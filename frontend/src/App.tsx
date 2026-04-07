import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { useAgentStore } from '@/stores/agent'
import Layout from '@/components/Layout'

// Shared pages
const Login = lazy(() => import('@/pages/Login'))
const Settings = lazy(() => import('@/pages/Settings'))

// Investment Agent pages
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const NewsFeed = lazy(() => import('@/pages/NewsFeed'))
const Reports = lazy(() => import('@/pages/Reports'))
const Alerts = lazy(() => import('@/pages/Alerts'))
const Skills = lazy(() => import('@/pages/Skills'))
const TwitterTracking = lazy(() => import('@/pages/TwitterTracking'))
const Bookmarks = lazy(() => import('@/pages/Bookmarks'))
const Calendar = lazy(() => import('@/pages/Calendar'))
const MacroIndicators = lazy(() => import('@/pages/MacroIndicators'))
const HistoricalEvents = lazy(() => import('@/pages/HistoricalEvents'))
const OpenAlicePage = lazy(() => import('@/pages/OpenAlice'))

// Tech Info Agent pages (placeholder until Phase 4)
const TechDashboard = lazy(() =>
  import('@/pages/Dashboard').then((m) => ({ default: m.default })),
)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function DefaultRedirect() {
  const agentId = useAgentStore((s) => s.currentAgentId)
  const prefix = agentId === 'tech_info' ? '/tech' : '/invest'
  return <Navigate to={prefix} replace />
}

const Fallback = () => (
  <div className="flex items-center justify-center h-64 text-text-secondary">加载中...</div>
)

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Fallback />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            {/* Root → redirect to last-used agent */}
            <Route index element={<DefaultRedirect />} />

            {/* Investment Agent routes */}
            <Route path="/invest" element={<Dashboard />} />
            <Route path="/invest/news" element={<NewsFeed />} />
            <Route path="/invest/reports" element={<Reports />} />
            <Route path="/invest/alerts" element={<Alerts />} />
            <Route path="/invest/skills" element={<Skills />} />
            <Route path="/invest/twitter" element={<TwitterTracking />} />
            <Route path="/invest/bookmarks" element={<Bookmarks />} />
            <Route path="/invest/calendar" element={<Calendar />} />
            <Route path="/invest/macro" element={<MacroIndicators />} />
            <Route path="/invest/historical-events" element={<HistoricalEvents />} />
            <Route path="/invest/alice" element={<OpenAlicePage />} />

            {/* Tech Info Agent routes (Phase 4 will add real pages) */}
            <Route path="/tech" element={<TechDashboard />} />
            <Route path="/tech/github" element={<TechDashboard />} />
            <Route path="/tech/hackernews" element={<TechDashboard />} />
            <Route path="/tech/v2ex" element={<TechDashboard />} />
            <Route path="/tech/linux-do" element={<TechDashboard />} />
            <Route path="/tech/twitter" element={<TechDashboard />} />

            {/* Shared routes */}
            <Route path="/settings" element={<Settings />} />

            {/* Legacy route redirects (backward compatibility) */}
            <Route path="/news" element={<Navigate to="/invest/news" replace />} />
            <Route path="/reports" element={<Navigate to="/invest/reports" replace />} />
            <Route path="/alerts" element={<Navigate to="/invest/alerts" replace />} />
            <Route path="/skills" element={<Navigate to="/invest/skills" replace />} />
            <Route path="/twitter" element={<Navigate to="/invest/twitter" replace />} />
            <Route path="/bookmarks" element={<Navigate to="/invest/bookmarks" replace />} />
            <Route path="/calendar" element={<Navigate to="/invest/calendar" replace />} />
            <Route path="/macro" element={<Navigate to="/invest/macro" replace />} />
            <Route path="/historical-events" element={<Navigate to="/invest/historical-events" replace />} />
            <Route path="/alice" element={<Navigate to="/invest/alice" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
