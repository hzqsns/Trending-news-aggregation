import asyncio
import logging
from typing import TYPE_CHECKING

from app.crawlers.base import CrawlerPlugin
from app.crawlers.rss import RSSCrawler
from app.crawlers.coingecko import CoinGeckoCrawler
from app.crawlers.newsapi import NewsAPICrawler
from app.crawlers.twitter import TwitterCrawler
from app.crawlers.github import GitHubTrendingCrawler
from app.crawlers.hackernews import HackerNewsCrawler
from app.crawlers.v2ex import V2exCrawler
from app.crawlers.linux_do import LinuxDoCrawler
from app.crawlers.ai_blogs import AIBlogsCrawler
from app.sources.base import NewsItem

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

ALL_CRAWLERS: dict[str, CrawlerPlugin] = {
    "rss": RSSCrawler(),
    "coingecko": CoinGeckoCrawler(),
    "newsapi": NewsAPICrawler(),
    "twitter": TwitterCrawler(),
    "github": GitHubTrendingCrawler(),
    "hackernews": HackerNewsCrawler(),
    "v2ex": V2exCrawler(),
    "linux_do": LinuxDoCrawler(),
    "ai_blogs": AIBlogsCrawler(),
}


class CrawlerManager:
    """Assembles and runs a set of crawlers for a given agent."""

    def __init__(self, crawler_keys: list[str] | None = None):
        if crawler_keys is None:
            self._crawlers = list(ALL_CRAWLERS.values())
        else:
            self._crawlers = [
                ALL_CRAWLERS[k] for k in crawler_keys if k in ALL_CRAWLERS
            ]

    async def fetch_all(self) -> tuple[list[NewsItem], dict]:
        stats: dict = {"total_fetched": 0, "crawlers": {}}
        all_items: list[NewsItem] = []

        tasks = [c.fetch() for c in self._crawlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for crawler, result in zip(self._crawlers, results):
            if isinstance(result, Exception):
                logger.error(f"Crawler {crawler.name} failed: {result}")
                stats["crawlers"][crawler.key] = {"error": str(result)}
                continue

            stats["crawlers"][crawler.key] = {"fetched": len(result)}
            stats["total_fetched"] += len(result)
            all_items.extend(result)

        return all_items, stats
