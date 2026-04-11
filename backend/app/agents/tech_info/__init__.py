from app.agents.tech_info.defaults import BUILTIN_SKILLS
from app.agents.tech_info.jobs import register_tech_jobs
from app.agents.tech_info.routes import router
from app.platform.manifest import AgentManifest
from app.platform.registry import AgentRegistry, agent_registry


def register_tech_info_agent(
    registry: AgentRegistry | None = None,
) -> AgentManifest:
    target = registry or agent_registry
    manifest = AgentManifest(
        key="tech_info",
        name="技术信息 Agent",
        description="技术趋势追踪与开发者资讯聚合",
        router=router,
        job_registrar=register_tech_jobs,
        builtin_skills=BUILTIN_SKILLS,
    )
    return target.register(manifest)


__all__ = ["register_tech_info_agent"]
