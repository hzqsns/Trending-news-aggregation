import { useEffect, useState, useRef } from 'react'
import { FileText, Calendar, RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { reportsApi } from '@/api'

interface Report {
  id: number
  report_type: string
  report_date: string
  title: string | null
  content: string
  key_events: unknown[] | null
  created_at: string
}

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([])
  const [selected, setSelected] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [generatingType, setGeneratingType] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [generateResult, setGenerateResult] = useState<{ ok: boolean; message: string } | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const params: Record<string, unknown> = {}
        if (filter) params.report_type = filter
        const resp = await reportsApi.list(params)
        setReports(resp.data)
        if (resp.data.length > 0 && !selected) {
          setSelected(resp.data[0])
        }
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [filter])

  // cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const typeLabel = (t: string) => t === 'morning' ? '☀️ 早报' : '🌙 晚报'

  const handleGenerate = async (type: 'morning' | 'evening') => {
    setGeneratingType(type)
    setGenerateResult(null)
    setElapsed(0)

    // start elapsed timer
    const start = Date.now()
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)

    try {
      const resp = await reportsApi.generate(type)
      setGenerateResult({ ok: true, message: `${typeLabel(type)}生成成功` })
      setReports((prev) => [resp.data, ...prev])
      setSelected(resp.data)
    } catch (e: any) {
      const detail = e.response?.data?.detail || e.message
      setGenerateResult({ ok: false, message: detail })
    } finally {
      if (timerRef.current) clearInterval(timerRef.current)
      timerRef.current = null
      setGeneratingType(null)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">AI 日报</h2>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-border text-sm"
          >
            <option value="">全部</option>
            <option value="morning">早报</option>
            <option value="evening">晚报</option>
          </select>
          <button
            onClick={() => handleGenerate('morning')}
            disabled={generatingType !== null}
            className="flex items-center gap-1.5 px-3 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={generatingType === 'morning' ? 'animate-spin' : ''} />
            {generatingType === 'morning' ? `生成中 ${elapsed}s` : '生成早报'}
          </button>
          <button
            onClick={() => handleGenerate('evening')}
            disabled={generatingType !== null}
            className="flex items-center gap-1.5 px-3 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={generatingType === 'evening' ? 'animate-spin' : ''} />
            {generatingType === 'evening' ? `生成中 ${elapsed}s` : '生成晚报'}
          </button>
        </div>
      </div>

      {/* 生成进度/结果反馈 */}
      {generatingType && (
        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-700 dark:text-blue-400">
            <RefreshCw size={14} className="animate-spin" />
            <span>正在生成{typeLabel(generatingType)}... 已用时 {elapsed} 秒</span>
          </div>
          <div className="mt-2 w-full bg-blue-100 dark:bg-blue-900/40 rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-1000"
              style={{ width: `${Math.min((elapsed / 60) * 100, 95)}%` }}
            />
          </div>
          <p className="mt-1.5 text-xs text-blue-600/70 dark:text-blue-400/70">
            AI 正在分析今日新闻并撰写报告，通常需要 30~60 秒
          </p>
        </div>
      )}

      {generateResult && !generatingType && (
        <div className={`mb-4 p-4 rounded-lg border text-sm ${generateResult.ok
          ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-400'
          : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'}`}
        >
          <div className="flex items-start gap-2">
            {generateResult.ok
              ? <CheckCircle size={16} className="shrink-0 mt-0.5" />
              : <XCircle size={16} className="shrink-0 mt-0.5" />}
            <div>
              <p className="font-medium">{generateResult.ok ? '生成成功' : '生成失败'}</p>
              <p className="mt-1 whitespace-pre-wrap break-all">{generateResult.message}</p>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-text-secondary">加载中...</div>
      ) : reports.length === 0 && !generatingType ? (
        <div className="bg-card rounded-xl p-12 text-center border border-border">
          <FileText size={48} className="mx-auto text-text-secondary/30 mb-4" />
          <p className="text-text-secondary">暂无日报</p>
          <p className="text-xs text-text-secondary mt-1">点击上方「生成早报」或「生成晚报」按钮手动生成，或等待系统在 07:30/22:00 自动生成</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Report List */}
          <div className="lg:col-span-1 bg-card rounded-xl border border-border overflow-hidden">
            <div className="p-4 border-b border-border">
              <h3 className="font-semibold text-sm">报告列表</h3>
            </div>
            <div className="divide-y divide-border max-h-[70vh] overflow-auto">
              {reports.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className={`w-full text-left p-4 hover:bg-bg/50 transition-colors ${selected?.id === r.id ? 'bg-primary/5 border-l-2 border-l-primary' : ''}`}
                >
                  <p className="text-sm font-medium">{typeLabel(r.report_type)}</p>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-text-secondary">
                    <Calendar size={12} />
                    {r.report_date}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Report Content */}
          <div className="lg:col-span-2 bg-card rounded-xl border border-border overflow-hidden">
            {selected ? (
              <>
                <div className="p-5 border-b border-border">
                  <h3 className="font-semibold">{selected.title || `${typeLabel(selected.report_type)} ${selected.report_date}`}</h3>
                  <p className="text-xs text-text-secondary mt-1">
                    生成时间: {new Date(selected.created_at).toLocaleString('zh-CN')}
                  </p>
                </div>
                <div className="p-5 overflow-auto max-h-[65vh] markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {selected.content}
                  </ReactMarkdown>
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-text-secondary">选择一份报告查看</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
