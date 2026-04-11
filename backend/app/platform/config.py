from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import SystemSetting


class ScopedConfigService:
    @staticmethod
    def namespaced_key(agent_key: str, key: str) -> str:
        return f"{agent_key}.{key}"

    async def get(
        self,
        session: AsyncSession,
        agent_key: str,
        key: str,
        default: str | None = None,
    ) -> str | None:
        namespaced = self.namespaced_key(agent_key, key)
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == namespaced)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else default

    async def list_namespace(
        self,
        session: AsyncSession,
        agent_key: str,
    ) -> list[SystemSetting]:
        prefix = f"{agent_key}.%"
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.like(prefix))
        )
        return list(result.scalars().all())
