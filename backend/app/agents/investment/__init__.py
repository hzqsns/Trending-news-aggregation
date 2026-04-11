from app.agents.investment.defaults import BUILTIN_SKILLS
from app.agents.investment.jobs import register_investment_jobs
from app.agents.investment.routes import router
from app.platform.manifest import AgentManifest
from app.platform.registry import AgentRegistry, agent_registry


def build_investment_manifest() -> AgentManifest:
    return AgentManifest(
        key="investment",
        name="投研 Agent",
        description="AI 驱动的金融新闻聚合与投研系统",
        router=router,
        job_registrar=register_investment_jobs,
        builtin_skills=BUILTIN_SKILLS,
    )


def register_investment_agent(
    registry: AgentRegistry | None = None,
) -> AgentManifest:
    target_registry = registry or agent_registry
    manifest = build_investment_manifest()
    return target_registry.register(manifest)


__all__ = ["build_investment_manifest", "register_investment_agent"]
