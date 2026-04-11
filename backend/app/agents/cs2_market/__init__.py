from app.agents.cs2_market.defaults import BUILTIN_SKILLS
from app.agents.cs2_market.jobs import register_cs2_jobs
from app.agents.cs2_market.routes import router
from app.platform.manifest import AgentManifest
from app.platform.registry import AgentRegistry, agent_registry


def register_cs2_market_agent(
    registry: AgentRegistry | None = None,
) -> AgentManifest:
    target = registry or agent_registry
    manifest = AgentManifest(
        key="cs2_market",
        name="CS2 饰品市场",
        description="CS2 饰品行情 · 涨跌榜 · AI 预测",
        router=router,
        job_registrar=register_cs2_jobs,
        builtin_skills=BUILTIN_SKILLS,
    )
    return target.register(manifest)


__all__ = ["register_cs2_market_agent"]
