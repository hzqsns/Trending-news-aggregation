from abc import ABC, abstractmethod


class Notifier(ABC):
    name: str = "unknown"
    enabled_key: str = ""

    @abstractmethod
    async def send(self, title: str, content: str, url: str = "") -> bool:
        ...

    @abstractmethod
    async def send_markdown(self, title: str, markdown: str) -> bool:
        ...
