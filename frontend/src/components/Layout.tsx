import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Newspaper, FileText, AlertTriangle, Cpu,
  Settings, LogOut, Moon, Sun, Monitor, Menu, X,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/news', icon: Newspaper, label: '新闻流' },
  { to: '/reports', icon: FileText, label: 'AI 日报' },
  { to: '/alerts', icon: AlertTriangle, label: '预警中心' },
  { to: '/skills', icon: Cpu, label: 'Skills' },
  { to: '/settings', icon: Settings, label: '系统设置' },
]

const themeOptions = [
  { value: 'light' as const, icon: Sun, label: '浅色' },
  { value: 'dark' as const, icon: Moon, label: '深色' },
  { value: 'system' as const, icon: Monitor, label: '跟随系统' },
]

export default function Layout() {
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const { theme, setTheme } = useThemeStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const currentThemeIcon = themeOptions.find((t) => t.value === theme)?.icon || Monitor

  const cycleTheme = () => {
    const order: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system']
    const idx = order.indexOf(theme)
    setTheme(order[(idx + 1) % order.length])
  }

  const sidebar = (
    <>
      <div className="p-5 border-b border-white/10">
        <h1 className="text-lg font-bold tracking-tight">📊 投研 Agent</h1>
        <p className="text-xs text-white/50 mt-1">News Intelligence System</p>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
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
        {user && <p className="text-xs text-white/40">👤 {user.username}</p>}
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
          <h1 className="text-sm font-bold">📊 投研 Agent</h1>
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
