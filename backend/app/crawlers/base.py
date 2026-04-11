from abc import ABC, abstractmethod

from app.sources.base import NewsItem


class CrawlerPlugin(ABC):
    """Base class for all crawler plugins (replaces NewsSource)."""

    key: str = ""
    name: str = "unknown"
    category: str = "general"
    enabled_key: str = ""

    @abstractmethod
    async def fetch(self) -> list[NewsItem]:
        ...
