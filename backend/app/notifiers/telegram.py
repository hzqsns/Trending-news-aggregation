import logging

import httpx

from app.notifiers.base import Notifier

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    name = "Telegram"
    enabled_key = "telegram_enabled"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"

    async def send(self, title: str, content: str, url: str = "") -> bool:
        text = f"*{self._escape(title)}*\n\n{self._escape(content)}"
        if url:
            text += f"\n\n[阅读原文]({url})"
        return await self._send_message(text, parse_mode="MarkdownV2")

    async def send_markdown(self, title: str, markdown: str) -> bool:
        text = f"📊 *{title}*\n\n{markdown}"
        return await self._send_message(text, parse_mode="Markdown")

    async def _send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.api_base}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text[:4096],
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": False,
                    },
                )
                if resp.status_code == 200 and resp.json().get("ok"):
                    return True
                logger.error(f"Telegram send failed: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    @staticmethod
    def _escape(text: str) -> str:
        special = r"_*[]()~`>#+-=|{}.!"
        for char in special:
            text = text.replace(char, f"\\{char}")
        return text
