from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem
from app.sources.rss import RSSSource


class RSSCrawler(CrawlerPlugin):
    key = "rss"
    name = "RSS"
    category = "general"
    enabled_key = "source_rss_enabled"

    def __init__(self):
        self._source = RSSSource()

    async def fetch(self) -> list[NewsItem]:
        return await self._source.fetch()
