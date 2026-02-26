import logging
from datetime import datetime

import httpx

from app.sources.base import NewsSource, NewsItem

logger = logging.getLogger(__name__)


class CryptoSource(NewsSource):
    name = "CoinGecko"
    category = "crypto"
    enabled_key = "source_crypto_enabled"

    async def fetch(self) -> list[NewsItem]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/news",
                    headers={"User-Agent": "NewsAgent/2.0"},
                )
                if resp.status_code != 200:
                    logger.warning(f"CoinGecko news API returned {resp.status_code}")
                    return items

                data = resp.json()
                news_list = data.get("data", data) if isinstance(data, dict) else data

                if not isinstance(news_list, list):
                    return items

                for entry in news_list[:20]:
                    pub_date = None
                    if "updated_at" in entry:
                        try:
                            pub_date = datetime.fromisoformat(
                                entry["updated_at"].replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    items.append(NewsItem(
                        title=entry.get("title", ""),
                        url=entry.get("url", ""),
                        source="CoinGecko",
                        category="crypto",
                        summary=entry.get("description", "")[:500] if entry.get("description") else None,
                        image_url=entry.get("thumb_2x") or entry.get("large_img"),
                        published_at=pub_date,
                    ))
        except Exception as e:
            logger.error(f"Error fetching CoinGecko news: {e}")
        return items
