import { useNavigate } from 'react-router-dom'
import { AGENTS } from '@/config/agents'
import { useAgentStore } from '@/stores/agent'

export default function AgentSwitcher() {
  const { currentAgentId, setAgent } = useAgentStore()
  const navigate = useNavigate()

  const current = AGENTS.find((a) => a.id === currentAgentId) ?? AGENTS[0]
  const gridCols = AGENTS.length === 3 ? 'grid-cols-3' : 'grid-cols-2'

  const switchTo = (agent: typeof AGENTS[number]) => {
    if (agent.id === currentAgentId) return
    setAgent(agent.id)
    navigate(agent.pathPrefix)
  }

  return (
    <div>
      <div className="text-[10px] font-medium uppercase tracking-wider text-white/40 mb-2 px-1">
        当前 Agent
      </div>

      <div className={`grid ${gridCols} gap-1.5`}>
        {AGENTS.map((agent) => {
          const Icon = agent.icon
          const isActive = agent.id === currentAgentId
          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => switchTo(agent)}
              title={`${agent.name} — ${agent.description}`}
              aria-label={`切换到 ${agent.name}`}
              aria-pressed={isActive}
              className={`
                group relative flex flex-col items-center justify-center
                gap-1 py-2.5 max-md:py-3.5 px-1 rounded-lg
                transition-all duration-200 ease-out
                focus:outline-none focus:ring-2 focus:ring-white/30
                ${isActive
                  ? `${agent.accentClass} text-white shadow-lg scale-[1.03]`
                  : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white/90'}
              `}
            >
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-white rounded-full" />
              )}
              <Icon
                size={20}
                strokeWidth={isActive ? 2.5 : 2}
                className={isActive ? 'scale-110' : 'group-hover:scale-110 transition-transform'}
              />
              <span className="text-[11px] font-medium leading-none truncate max-w-full">
                {agent.shortName}
              </span>
            </button>
          )
        })}
      </div>

      <p className="mt-2 px-1 text-[10px] text-white/50 leading-snug min-h-[14px]">
        {current.description}
      </p>
    </div>
  )
}
