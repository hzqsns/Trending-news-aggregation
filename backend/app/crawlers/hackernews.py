import logging
from datetime import datetime, timezone

import httpx

from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem

logger = logging.getLogger(__name__)

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


class HackerNewsCrawler(CrawlerPlugin):
    key = "hackernews"
    name = "Hacker News"
    category = "tech"
    enabled_key = "source_hackernews_enabled"

    async def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(HN_TOP_URL)
                if resp.status_code != 200:
                    logger.warning(f"HN top stories returned {resp.status_code}")
                    return items

                story_ids = resp.json()[:30]

                for sid in story_ids:
                    try:
                        detail = await client.get(HN_ITEM_URL.format(sid))
                        if detail.status_code != 200:
                            continue
                        story = detail.json()
                        if not story or story.get("type") != "story":
                            continue

                        pub_date = None
                        if story.get("time"):
                            pub_date = datetime.fromtimestamp(story["time"], tz=timezone.utc)

                        url = story.get("url") or f"https://news.ycombinator.com/item?id={sid}"
                        score = story.get("score", 0)
                        items.append(NewsItem(
                            title=f"{story.get('title', '')} ({score} pts)",
                            url=url,
                            source="Hacker News",
                            category="tech",
                            summary=None,
                            published_at=pub_date,
                        ))
                    except Exception as e:
                        logger.debug(f"HN item {sid} error: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error fetching Hacker News: {e}")
        return items
