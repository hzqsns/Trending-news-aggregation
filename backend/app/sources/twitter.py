import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.database import async_session
from app.models.setting import SystemSetting
from app.sources.base import NewsSource, NewsItem

logger = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).parent.parent.parent / "data" / "twitter_cookies.json"

_client = None  # global twikit client, reused across calls


async def _get_twitter_config() -> dict:
    async with async_session() as session:
        keys = [
            "twitter_enabled", "twitter_auth_username", "twitter_auth_email",
            "twitter_auth_password", "twitter_handles",
        ]
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.in_(keys))
        )
        settings = {s.key: s.value for s in result.scalars().all()}

    handles = []
    try:
        handles = json.loads(settings.get("twitter_handles", "[]"))
    except json.JSONDecodeError:
        pass

    return {
        "enabled": settings.get("twitter_enabled", "false") == "true",
        "username": settings.get("twitter_auth_username", ""),
        "email": settings.get("twitter_auth_email", ""),
        "password": settings.get("twitter_auth_password", ""),
        "handles": handles,
    }


async def _get_client(config: dict):
    global _client

    try:
        from twikit import Client as TwikitClient
    except ImportError:
        logger.error("twikit not installed. Run: pip install twikit")
        return None

    # Reuse existing client
    if _client is not None:
        return _client

    client = TwikitClient("en-US")

    # Try restoring session from cookies
    if COOKIES_FILE.exists():
        try:
            client.load_cookies(str(COOKIES_FILE))
            _client = client
            logger.info("Twitter: restored session from cookies")
            return _client
        except Exception as e:
            logger.warning(f"Twitter: failed to load cookies ({e}), will re-login")
            COOKIES_FILE.unlink(missing_ok=True)

    # Fresh login
    username = config["username"]
    email = config["email"]
    password = config["password"]
    if not username or not password:
        logger.error("Twitter: auth credentials not configured")
        return None

    try:
        COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
        client.save_cookies(str(COOKIES_FILE))
        _client = client
        logger.info("Twitter: logged in successfully, cookies saved")
        return _client
    except Exception as e:
        logger.error(f"Twitter: login failed: {e}")
        COOKIES_FILE.unlink(missing_ok=True)
        _client = None
        return None


async def _fetch_user_tweets(client, handle: str, hours: int = 24) -> list[dict]:
    """Fetch recent tweets for a handle within the last `hours` hours."""
    try:
        user = await client.get_user_by_screen_name(handle)
        tweets = await client.get_user_tweets(user.id, "Tweets", count=20)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results = []
        for tweet in tweets:
            try:
                created_at = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
            except Exception:
                continue
            if created_at < cutoff:
                continue
            results.append({
                "text": tweet.text,
                "created_at": created_at,
                "url": f"https://x.com/{handle}/status/{tweet.id}",
                "handle": handle,
            })
        return results
    except Exception as e:
        logger.warning(f"Twitter: failed to fetch tweets for @{handle}: {e}")
        return []


class TwitterSource(NewsSource):
    name = "Twitter"
    category = "twitter"
    enabled_key = "twitter_enabled"

    async def fetch(self) -> list[NewsItem]:
        config = await _get_twitter_config()

        if not config["enabled"]:
            return []
        if not config["handles"]:
            logger.info("Twitter tracking enabled but no handles configured")
            return []

        client = await _get_client(config)
        if client is None:
            return []

        all_items = []
        for handle in config["handles"]:
            tweets = await _fetch_user_tweets(client, handle)
            if not tweets:
                logger.info(f"Twitter: no recent tweets for @{handle}")
                continue

            for t in tweets:
                # 标题取推文前 80 字符
                title_text = t["text"].replace("\n", " ")
                title = f"@{handle}: {title_text[:80]}{'…' if len(title_text) > 80 else ''}"

                all_items.append(NewsItem(
                    title=title,
                    url=t["url"],          # https://x.com/{handle}/status/{id}，天然去重
                    source="Twitter",
                    category="twitter",
                    summary=t["text"][:300],
                    content=t["text"],
                    published_at=t["created_at"],
                    importance=2,
                ))

        logger.info(f"Twitter source fetched {len(all_items)} tweets for {len(config['handles'])} handles")
        return all_items
