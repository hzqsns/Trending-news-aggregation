import { useEffect, useState } from 'react'
import { Plus, Trash2, RefreshCw, ExternalLink, AtSign, CheckCircle, XCircle, Loader, FileText, Zap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { twitterApi, settingsApi, reportsApi } from '@/api'

interface DigestReport {
  id: number
  title: string
  content: string
  report_date: string
  created_at: string
}

export default function TwitterTracking() {
  const [activeTab, setActiveTab] = useState<'handles' | 'digest'>('handles')
  const [handles, setHandles] = useState<string[]>([])
  const [newHandle, setNewHandle] = useState('')
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [fetchResult, setFetchResult] = useState<string | null>(null)
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [savingSettings, setSavingSettings] = useState(false)
  const [cookieJson, setCookieJson] = useState('')
  const [importingCookies, setImportingCookies] = useState(false)
  const [cookieStatus, setCookieStatus] = useState<{ ok: boolean; message: string } | null>(null)
  // 观点日报 tab
  const [digests, setDigests] = useState<DigestReport[]>([])
  const [digestLoading, setDigestLoading] = useState(false)
  const [generatingDigest, setGeneratingDigest] = useState(false)
  const [digestResult, setDigestResult] = useState<string | null>(null)
  const [expandedDigest, setExpandedDigest] = useState<number | null>(null)

  const loadHandles = async () => {
    try {
      const resp = await twitterApi.listHandles()
      setHandles(resp.data.handles)
    } catch (e) {
      console.error(e)
    }
  }

  const loadSettings = async () => {
    try {
      const resp = await settingsApi.list('twitter')
      const items = resp.data.twitter || []
      const s: Record<string, string> = {}
      for (const item of items) {
        if (item.key !== 'twitter_handles') {
          s[item.key] = item.value ?? ''
        }
      }
      setSettings(s)
    } catch (e) {
      console.error(e)
    }
  }

  const loadDigests = async () => {
    setDigestLoading(true)
    try {
      const resp = await reportsApi.listByType('twitter_digest', 7)
      setDigests(resp.data)
    } catch (e) {
      console.error(e)
    } finally {
      setDigestLoading(false)
    }
  }

  useEffect(() => {
    Promise.all([loadHandles(), loadSettings()]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (activeTab === 'digest' && digests.length === 0) {
      loadDigests()
    }
  }, [activeTab])

  const addHandle = async () => {
    const h = newHandle.trim().replace(/^@/, '')
    if (!h) return
    setAdding(true)
    try {
      const resp = await twitterApi.addHandle(h)
      setHandles(resp.data.handles)
      setNewHandle('')
    } catch (e: any) {
      alert(e.response?.data?.detail || '添加失败')
    } finally {
      setAdding(false)
    }
  }

  const removeHandle = async (handle: string) => {
    try {
      const resp = await twitterApi.removeHandle(handle)
      setHandles(resp.data.handles)
    } catch (e) {
      console.error(e)
    }
  }

  const manualFetch = async () => {
    setFetching(true)
    setFetchResult(null)
    try {
      const resp = await twitterApi.manualFetch()
      setFetchResult(`采集完成：获取 ${resp.data.fetched} 条，新增 ${resp.data.saved} 条`)
    } catch (e: any) {
      setFetchResult(`采集失败：${e.response?.data?.detail || e.message}`)
    } finally {
      setFetching(false)
    }
  }

  const saveSettings = async () => {
    setSavingSettings(true)
    try {
      await settingsApi.batchUpdate(settings)
    } catch (e) {
      console.error(e)
    } finally {
      setSavingSettings(false)
    }
  }

  const generateDigest = async () => {
    setGeneratingDigest(true)
    setDigestResult(null)
    try {
      await reportsApi.generateTwitterDigest()
      setDigestResult('生成成功！')
      await loadDigests()
    } catch (e: any) {
      setDigestResult(`生成失败：${e.response?.data?.detail || e.message}`)
    } finally {
      setGeneratingDigest(false)
    }
  }

  const importCookies = async () => {
    if (!cookieJson.trim()) return
    setImportingCookies(true)
    setCookieStatus(null)
    try {
      const resp = await twitterApi.importCookies(cookieJson.trim())
      setCookieStatus({ ok: true, message: resp.data.message })
      setCookieJson('')
    } catch (e: any) {
      setCookieStatus({ ok: false, message: e.response?.data?.detail || e.message })
    } finally {
      setImportingCookies(false)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-text-secondary">加载中...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">推特博主追踪</h2>
        {activeTab === 'handles' ? (
          <button
            onClick={manualFetch}
            disabled={fetching || handles.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={fetching ? 'animate-spin' : ''} />
            {fetching ? '采集中...' : '立即采集'}
          </button>
        ) : (
          <button
            onClick={generateDigest}
            disabled={generatingDigest}
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <Zap size={16} className={generatingDigest ? 'animate-pulse' : ''} />
            {generatingDigest ? '生成中...' : '立即生成日报'}
          </button>
        )}
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-1 mb-6 bg-card rounded-xl p-1 border border-border w-fit">
        <button
          onClick={() => setActiveTab('handles')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-colors ${activeTab === 'handles' ? 'bg-primary text-white' : 'text-text-secondary hover:text-text'}`}
        >
          <AtSign size={15} />
          博主管理
        </button>
        <button
          onClick={() => setActiveTab('digest')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-colors ${activeTab === 'digest' ? 'bg-primary text-white' : 'text-text-secondary hover:text-text'}`}
        >
          <FileText size={15} />
          观点日报
        </button>
      </div>

      {fetchResult && activeTab === 'handles' && (
        <div className="mb-4 p-3 bg-card border border-border rounded-lg text-sm">
          {fetchResult}
        </div>
      )}

      {digestResult && activeTab === 'digest' && (
        <div className={`mb-4 p-3 border rounded-lg text-sm ${digestResult.startsWith('生成成功') ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-400' : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'}`}>
          {digestResult}
        </div>
      )}

      {/* 观点日报 Tab */}
      {activeTab === 'digest' && (
        <div className="space-y-4">
          {digestLoading ? (
            <div className="p-8 text-center text-text-secondary">加载中...</div>
          ) : digests.length === 0 ? (
            <div className="bg-card rounded-xl border border-border p-12 text-center">
              <FileText size={40} className="mx-auto mb-3 text-text-secondary opacity-40" />
              <p className="text-text-secondary text-sm">暂无观点日报</p>
              <p className="text-text-secondary text-xs mt-1">点击右上角"立即生成日报"，或等待每天09:00自动生成</p>
            </div>
          ) : (
            digests.map((report) => (
              <div key={report.id} className="bg-card rounded-xl border border-border overflow-hidden">
                <button
                  onClick={() => setExpandedDigest(expandedDigest === report.id ? null : report.id)}
                  className="w-full p-5 flex items-center justify-between hover:bg-bg transition-colors text-left"
                >
                  <div>
                    <div className="font-semibold text-sm">{report.title}</div>
                    <div className="text-xs text-text-secondary mt-0.5">
                      {new Date(report.created_at).toLocaleString('zh-CN')}
                    </div>
                  </div>
                  <span className="text-text-secondary text-xs ml-4">{expandedDigest === report.id ? '收起 ▲' : '展开 ▼'}</span>
                </button>
                {expandedDigest === report.id && (
                  <div className="px-5 pb-5 border-t border-border">
                    <div className="prose prose-sm max-w-none dark:prose-invert pt-4 text-sm">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.content}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* 博主管理 Tab */}
      {activeTab === 'handles' && <>
      {/* 博主列表 */}
      <div className="bg-card rounded-xl border border-border mb-6">
        <div className="p-5 border-b border-border">
          <h3 className="font-semibold">追踪的博主</h3>
          <p className="text-xs text-text-secondary mt-1">添加推特博主的用户名（不含 @），系统会定时采集他们的投资相关推文</p>
        </div>

        {/* 添加输入框 */}
        <div className="p-4 border-b border-border">
          <div className="flex gap-2">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary text-sm">@</span>
              <input
                type="text"
                value={newHandle}
                onChange={(e) => setNewHandle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addHandle()}
                placeholder="输入推特用户名，如 elonmusk"
                className="w-full pl-8 pr-3 py-2 rounded-lg border border-border text-sm"
              />
            </div>
            <button
              onClick={addHandle}
              disabled={adding || !newHandle.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
            >
              <Plus size={16} />
              添加
            </button>
          </div>
        </div>

        {/* 博主列表 */}
        <div className="divide-y divide-border">
          {handles.map((handle) => (
            <div key={handle} className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                  <AtSign size={16} className="text-blue-500" />
                </div>
                <div>
                  <span className="text-sm font-medium">@{handle}</span>
                  <a
                    href={`https://x.com/${handle}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-text-secondary hover:text-primary"
                  >
                    <ExternalLink size={12} className="inline" />
                  </a>
                </div>
              </div>
              <button
                onClick={() => removeHandle(handle)}
                className="p-1.5 text-text-secondary hover:text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {handles.length === 0 && (
            <div className="p-8 text-center text-text-secondary text-sm">
              暂未添加任何博主，请在上方输入框添加
            </div>
          )}
        </div>
      </div>

      {/* X 账号认证 */}
      <div className="bg-card rounded-xl border border-border">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="font-semibold">X 账号认证</h3>
            <p className="text-xs text-text-secondary mt-1">导入浏览器 Cookie 完成认证，避免 Cloudflare 拦截</p>
          </div>
          <button
            onClick={saveSettings}
            disabled={savingSettings}
            className="px-3 py-1.5 bg-primary hover:bg-primary-dark text-white rounded-lg text-xs transition-colors disabled:opacity-50"
          >
            {savingSettings ? '保存中...' : '保存配置'}
          </button>
        </div>
        <div className="divide-y divide-border">
          <SettingRow
            label="启用推特追踪"
            description="开启后系统会定时采集配置的博主推文"
            value={settings.twitter_enabled ?? 'false'}
            type="boolean"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_enabled: v }))}
          />
          <SettingRow
            label="采集间隔（分钟）"
            description="建议 >= 30 以节省频率限制"
            value={settings.twitter_fetch_interval ?? '30'}
            type="number"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_fetch_interval: v }))}
          />
        </div>

        {/* Cookie 导入区域 */}
        <div className="p-5 border-t border-border">
          <div className="mb-3">
            <h4 className="text-sm font-medium">导入浏览器 Cookie</h4>
            <p className="text-xs text-text-secondary mt-1">
              在浏览器中登录 <a href="https://x.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">x.com</a>，安装
              <a href="https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline mx-1">Cookie-Editor</a>
              插件，Export → Export as JSON，将结果粘贴到下方
            </p>
          </div>
          <textarea
            value={cookieJson}
            onChange={(e) => setCookieJson(e.target.value)}
            placeholder='粘贴 Cookie JSON，如：[{"name":"auth_token","value":"..."},...]'
            rows={4}
            className="w-full px-3 py-2 rounded-lg border border-border text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-primary"
          />
          {cookieStatus && (
            <div className={`mt-2 flex items-start gap-2 p-3 rounded-lg text-sm ${cookieStatus.ok ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'}`}>
              {cookieStatus.ok
                ? <CheckCircle size={16} className="shrink-0 mt-0.5" />
                : <XCircle size={16} className="shrink-0 mt-0.5" />}
              <span>{cookieStatus.message}</span>
            </div>
          )}
          <button
            onClick={importCookies}
            disabled={importingCookies || !cookieJson.trim()}
            className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {importingCookies
              ? <><Loader size={14} className="animate-spin" />导入验证中...</>
              : <><CheckCircle size={14} />导入并验证</>}
          </button>
        </div>
      </div>
      </>}
    </div>
  )
}

function SettingRow({
  label,
  description,
  value,
  type,
  onChange,
}: {
  label: string
  description: string
  value: string
  type: 'text' | 'password' | 'number' | 'boolean'
  onChange: (v: string) => void
}) {
  const [showPwd, setShowPwd] = useState(false)

  return (
    <div className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="sm:w-1/3">
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-text-secondary">{description}</div>
      </div>
      <div className="sm:w-2/3">
        {type === 'boolean' ? (
          <button
            type="button"
            onClick={() => onChange(value === 'true' ? 'false' : 'true')}
            className={`relative w-12 h-6 rounded-full transition-colors ${value === 'true' ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${value === 'true' ? 'left-6' : 'left-0.5'}`} />
          </button>
        ) : type === 'password' ? (
          <div className="relative max-w-md">
            <input
              type={showPwd ? 'text' : 'password'}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-3 py-2 pr-10 rounded-lg border border-border text-sm"
            />
            <button
              type="button"
              onClick={() => setShowPwd(!showPwd)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary text-sm"
            >
              {showPwd ? '隐藏' : '显示'}
            </button>
          </div>
        ) : (
          <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full max-w-md px-3 py-2 rounded-lg border border-border text-sm"
          />
        )}
      </div>
    </div>
  )
}
