from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem
from app.sources.twitter import TwitterSource


class TwitterCrawler(CrawlerPlugin):
    key = "twitter"
    name = "Twitter/X"
    category = "social"
    enabled_key = "twitter_enabled"

    def __init__(self):
        self._source = TwitterSource()

    async def fetch(self) -> list[NewsItem]:
        return await self._source.fetch()
