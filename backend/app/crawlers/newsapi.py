from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem
from app.sources.newsapi import NewsAPISource


class NewsAPICrawler(CrawlerPlugin):
    key = "newsapi"
    name = "NewsAPI"
    category = "global"
    enabled_key = "source_newsapi_enabled"

    def __init__(self):
        self._source = NewsAPISource()

    async def fetch(self) -> list[NewsItem]:
        return await self._source.fetch()
