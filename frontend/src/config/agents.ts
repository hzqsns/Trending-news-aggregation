import {
  LayoutDashboard, Newspaper, Bookmark, FileText, AlertTriangle, Cpu,
  AtSign, CalendarDays, TrendingUp, History, Bot,
  Github, MessageSquare, Globe, Rss,
  Package, BarChart3, LayoutGrid, Sparkles, Star,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  to: string
  icon: LucideIcon
  label: string
}

export interface AgentManifest {
  id: string
  name: string
  shortName: string
  pathPrefix: string
  icon: LucideIcon
  description: string
  accentClass: string
  navItems: NavItem[]
}

export const AGENTS: AgentManifest[] = [
  {
    id: 'investment',
    name: '投研 Agent',
    shortName: '投研',
    pathPrefix: '/invest',
    icon: TrendingUp,
    description: 'AI 驱动的金融新闻聚合与投研系统',
    accentClass: 'bg-blue-600 hover:bg-blue-500',
    navItems: [
      { to: '/invest', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/invest/news', icon: Newspaper, label: '新闻流' },
      { to: '/invest/bookmarks', icon: Bookmark, label: '收藏夹' },
      { to: '/invest/reports', icon: FileText, label: 'AI 日报' },
      { to: '/invest/alerts', icon: AlertTriangle, label: '预警中心' },
      { to: '/invest/skills', icon: Cpu, label: 'Skills' },
      { to: '/invest/calendar', icon: CalendarDays, label: '金融日历' },
      { to: '/invest/macro', icon: TrendingUp, label: '宏观指标' },
      { to: '/invest/historical-events', icon: History, label: '历史事件库' },
      { to: '/invest/alice', icon: Bot, label: 'OpenAlice' },
      { to: '/invest/twitter', icon: AtSign, label: '推特追踪' },
    ],
  },
  {
    id: 'tech_info',
    name: '技术信息 Agent',
    shortName: '技术',
    pathPrefix: '/tech',
    icon: Globe,
    description: '技术趋势追踪与开发者资讯聚合',
    accentClass: 'bg-violet-600 hover:bg-violet-500',
    navItems: [
      { to: '/tech', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/tech/github', icon: Github, label: 'GitHub Trending' },
      { to: '/tech/hackernews', icon: Rss, label: 'Hacker News' },
      { to: '/tech/v2ex', icon: MessageSquare, label: 'V2EX' },
      { to: '/tech/linux-do', icon: Globe, label: 'Linux.do' },
      { to: '/tech/twitter', icon: AtSign, label: '技术推特' },
    ],
  },
  {
    id: 'cs2_market',
    name: 'CS2 饰品市场',
    shortName: 'CS2',
    pathPrefix: '/cs2',
    icon: Package,
    description: 'CS2 饰品行情 · 涨跌榜 · AI 预测',
    accentClass: 'bg-amber-600 hover:bg-amber-500',
    navItems: [
      { to: '/cs2', icon: LayoutDashboard, label: '市场总览' },
      { to: '/cs2/rankings', icon: BarChart3, label: '涨跌榜' },
      { to: '/cs2/categories', icon: LayoutGrid, label: '品类分析' },
      { to: '/cs2/predictions', icon: Sparkles, label: 'AI 预测' },
      { to: '/cs2/watchlist', icon: Star, label: '自选监控' },
    ],
  },
]

export const DEFAULT_AGENT_ID = 'investment'

export function getAgent(id: string): AgentManifest | undefined {
  return AGENTS.find((a) => a.id === id)
}
