import logging

import httpx

from app.notifiers.base import Notifier

logger = logging.getLogger(__name__)


class QQNotifier(Notifier):
    """通过 Qmsg 酱推送到 QQ"""

    name = "QQ"
    enabled_key = "qq_enabled"

    def __init__(self, key: str):
        self.key = key

    async def send(self, title: str, content: str, url: str = "") -> bool:
        msg = f"【{title}】\n{content}"
        if url:
            msg += f"\n{url}"
        return await self._push(msg)

    async def send_markdown(self, title: str, markdown: str) -> bool:
        return await self._push(f"【{title}】\n{markdown}")

    async def _push(self, msg: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://qmsg.zendee.cn/send/{self.key}",
                    data={"msg": msg[:1500]},
                )
                data = resp.json()
                if data.get("success"):
                    return True
                logger.error(f"Qmsg error: {data}")
                return False
        except Exception as e:
            logger.error(f"Qmsg error: {e}")
            return False
