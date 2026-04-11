from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem
from app.sources.crypto import CryptoSource


class CoinGeckoCrawler(CrawlerPlugin):
    key = "coingecko"
    name = "CoinGecko"
    category = "crypto"
    enabled_key = "source_crypto_enabled"

    def __init__(self):
        self._source = CryptoSource()

    async def fetch(self) -> list[NewsItem]:
        return await self._source.fetch()
