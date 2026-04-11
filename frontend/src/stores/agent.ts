import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { DEFAULT_AGENT_ID } from '@/config/agents'

interface AgentState {
  currentAgentId: string
  setAgent: (id: string) => void
}

export const useAgentStore = create<AgentState>()(
  persist(
    (set) => ({
      currentAgentId: DEFAULT_AGENT_ID,
      setAgent: (id: string) => set({ currentAgentId: id }),
    }),
    { name: 'news-agent-current' },
  ),
)
