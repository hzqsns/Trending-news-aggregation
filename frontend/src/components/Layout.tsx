import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Newspaper,
  FileText,
  AlertTriangle,
  Cpu,
  Settings,
  LogOut,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/news', icon: Newspaper, label: '新闻流' },
  { to: '/reports', icon: FileText, label: 'AI 日报' },
  { to: '/alerts', icon: AlertTriangle, label: '预警中心' },
  { to: '/skills', icon: Cpu, label: 'Skills' },
  { to: '/settings', icon: Settings, label: '系统设置' },
]

export default function Layout() {
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)

  return (
    <div className="flex h-screen">
      <aside className="w-60 bg-sidebar text-white flex flex-col shrink-0">
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
        <div className="p-4 border-t border-white/10">
          {user && <p className="text-xs text-white/40 mb-2">👤 {user.username}</p>}
          <button
            onClick={() => { logout(); window.location.href = '/login' }}
            className="flex items-center gap-2 text-white/50 hover:text-white text-sm w-full"
          >
            <LogOut size={16} />
            退出登录
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto bg-bg">
        <div className="p-6 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
