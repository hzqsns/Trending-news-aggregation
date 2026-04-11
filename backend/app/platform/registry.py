from __future__ import annotations

from app.platform.manifest import AgentManifest


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentManifest] = {}

    def register(self, manifest: AgentManifest) -> AgentManifest:
        existing = self._agents.get(manifest.key)
        if existing is not None:
            return existing
        self._agents[manifest.key] = manifest
        return manifest

    def get(self, agent_key: str) -> AgentManifest:
        manifest = self._agents.get(agent_key)
        if manifest is None:
            raise KeyError(f"Agent '{agent_key}' is not registered")
        return manifest

    def list_agents(self) -> list[AgentManifest]:
        return list(self._agents.values())


agent_registry = AgentRegistry()
