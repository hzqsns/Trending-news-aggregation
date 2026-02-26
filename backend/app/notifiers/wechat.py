import logging

import httpx

from app.notifiers.base import Notifier

logger = logging.getLogger(__name__)


class WeChatNotifier(Notifier):
    """通过 PushPlus 推送到微信"""

    name = "WeChat"
    enabled_key = "wechat_enabled"

    def __init__(self, token: str):
        self.token = token

    async def send(self, title: str, content: str, url: str = "") -> bool:
        body = content
        if url:
            body += f'\n\n<a href="{url}">阅读原文</a>'
        return await self._push(title, body, template="txt")

    async def send_markdown(self, title: str, markdown: str) -> bool:
        return await self._push(title, markdown, template="markdown")

    async def _push(self, title: str, content: str, template: str = "txt") -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://www.pushplus.plus/send",
                    json={
                        "token": self.token,
                        "title": title[:100],
                        "content": content,
                        "template": template,
                    },
                )
                data = resp.json()
                if data.get("code") == 200:
                    return True
                logger.error(f"PushPlus error: {data}")
                return False
        except Exception as e:
            logger.error(f"PushPlus error: {e}")
            return False
