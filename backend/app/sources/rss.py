import logging
from datetime import datetime
from time import mktime

import feedparser
import httpx

from app.sources.base import NewsSource, NewsItem

logger = logging.getLogger(__name__)

DEFAULT_RSS_FEEDS = [
    # --- 中文财经 ---
    {
        "name": "新浪财经",
        "url": "https://finance.sina.com.cn/rss/economy.xml",
        "category": "a_stock",
    },
    {
        "name": "华尔街见闻",
        "url": "https://wallstreetcn.com/rss",
        "category": "global",
    },
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "category": "tech",
    },
    {
        "name": "金十数据",
        "url": "https://rsshub.app/jin10",
        "category": "global",
    },
    {
        "name": "东方财富",
        "url": "https://rsshub.app/eastmoney/report/stock",
        "category": "a_stock",
    },
    {
        "name": "FT中文网",
        "url": "https://rsshub.app/ft/chinese/hotstoryby7day",
        "category": "global",
    },
    # --- 国际财经 ---
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "category": "crypto",
    },
    {
        "name": "Reuters Business",
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance",
        "category": "global",
    },
    {
        "name": "CNBC",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "category": "global",
    },
    {
        "name": "Bloomberg",
        "url": "https://rsshub.app/bloomberg/markets",
        "category": "global",
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech",
    },
    {
        "name": "The Block",
        "url": "https://www.theblock.co/rss.xml",
        "category": "crypto",
    },
    {
        "name": "SEC Filings",
        "url": "https://rsshub.app/sec/latest",
        "category": "a_stock",
    },
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "tech",
    },
]


class RSSSource(NewsSource):
    name = "RSS"
    enabled_key = "source_rss_enabled"

    def __init__(self, feeds: list[dict] | None = None):
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    async def fetch(self) -> list[NewsItem]:
        items = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for feed_cfg in self.feeds:
                try:
                    resp = await client.get(
                        feed_cfg["url"],
                        headers={"User-Agent": "Mozilla/5.0 NewsAgent/2.0"},
                    )
                    if resp.status_code != 200:
                        logger.warning(f"RSS {feed_cfg['name']} returned {resp.status_code}")
                        continue

                    parsed = feedparser.parse(resp.text)
                    for entry in parsed.entries[:20]:
                        pub_date = None
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                            pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed))

                        summary = ""
                        if hasattr(entry, "summary"):
                            summary = entry.summary[:500]

                        image_url = None
                        if hasattr(entry, "media_content") and entry.media_content:
                            image_url = entry.media_content[0].get("url")
                        elif hasattr(entry, "enclosures") and entry.enclosures:
                            image_url = entry.enclosures[0].get("href")

                        items.append(NewsItem(
                            title=entry.get("title", "").strip(),
                            url=entry.get("link", ""),
                            source=feed_cfg["name"],
                            category=feed_cfg.get("category", "general"),
                            summary=summary,
                            image_url=image_url,
                            published_at=pub_date,
                        ))
                except Exception as e:
                    logger.error(f"Error fetching RSS {feed_cfg['name']}: {e}")
        return items
