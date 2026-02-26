from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    category: str = "general"
    summary: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    importance: int = 0


class NewsSource(ABC):
    name: str = "unknown"
    category: str = "general"
    enabled_key: str = ""

    @abstractmethod
    async def fetch(self) -> list[NewsItem]:
        ...
