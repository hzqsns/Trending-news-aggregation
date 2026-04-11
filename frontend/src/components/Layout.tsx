import { useState, useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Settings, LogOut, Moon, Sun, Monitor, Menu, X } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useAgentStore } from '@/stores/agent'
import { AGENTS } from '@/config/agents'
import AgentSwitcher from '@/components/AgentSwitcher'

const themeOptions = [
  { value: 'light' as const, icon: Sun, label: '浅色' },
  { value: 'dark' as const, icon: Moon, label: '深色' },
  { value: 'system' as const, icon: Monitor, label: '跟随系统' },
]

export default function Layout() {
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const { theme, setTheme } = useThemeStore()
  const currentAgentId = useAgentStore((s) => s.currentAgentId)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const currentAgent = AGENTS.find((a) => a.id === currentAgentId) ?? AGENTS[0]
  const currentThemeIcon = themeOptions.find((t) => t.value === theme)?.icon || Monitor

  useEffect(() => {
    document.documentElement.setAttribute('data-agent', currentAgentId)
  }, [currentAgentId])

  const cycleTheme = () => {
    const order: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system']
    const idx = order.indexOf(theme)
    setTheme(order[(idx + 1) % order.length])
  }

  const sidebar = (
    <>
      <div className="p-4 border-b border-white/10">
        <AgentSwitcher />
      </div>
      <nav className="flex-1 py-4 overflow-y-auto">
        {currentAgent.navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === currentAgent.pathPrefix}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-primary text-white'
                  : 'text-white/70 hover:bg-sidebar-hover hover:text-white'
              }`
            }
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        ))}
        {/* Settings is shared across agents */}
        <NavLink
          to="/settings"
          onClick={() => setSidebarOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
              isActive
                ? 'bg-primary text-white'
                : 'text-white/70 hover:bg-sidebar-hover hover:text-white'
            }`
          }
        >
          <Settings size={18} />
          系统设置
        </NavLink>
      </nav>
      <div className="p-4 border-t border-white/10 space-y-3">
        <button
          onClick={cycleTheme}
          className="flex items-center gap-2 text-white/50 hover:text-white text-sm w-full"
          title={`当前: ${themeOptions.find((t) => t.value === theme)?.label}`}
        >
          {(() => { const Icon = currentThemeIcon; return <Icon size={16} /> })()}
          {themeOptions.find((t) => t.value === theme)?.label}模式
        </button>
        {user && <p className="text-xs text-white/40">{user.username}</p>}
        <button
          onClick={() => { logout(); window.location.href = '/login' }}
          className="flex items-center gap-2 text-white/50 hover:text-white text-sm w-full"
        >
          <LogOut size={16} /> 退出登录
        </button>
      </div>
    </>
  )

  return (
    <div className="flex h-screen">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-60 bg-sidebar text-white flex-col shrink-0">
        {sidebar}
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <aside className="relative w-60 h-full bg-sidebar text-white flex flex-col z-50">
            <button onClick={() => setSidebarOpen(false)} className="absolute top-4 right-4 text-white/50 hover:text-white">
              <X size={20} />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-card border-b border-border">
          <button onClick={() => setSidebarOpen(true)} className="text-text-secondary hover:text-text">
            <Menu size={22} />
          </button>
          <h1 className="text-sm font-bold">{currentAgent.name}</h1>
        </header>

        <main className="flex-1 overflow-auto bg-bg">
          <div className="p-4 md:p-6 max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
