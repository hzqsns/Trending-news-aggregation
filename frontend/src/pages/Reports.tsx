import { useEffect, useState } from 'react'
import { FileText, Calendar } from 'lucide-react'
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

  const typeLabel = (t: string) => t === 'morning' ? '☀️ 早报' : '🌙 晚报'

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">AI 日报</h2>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border text-sm"
        >
          <option value="">全部</option>
          <option value="morning">早报</option>
          <option value="evening">晚报</option>
        </select>
      </div>

      {loading ? (
        <div className="p-8 text-center text-text-secondary">加载中...</div>
      ) : reports.length === 0 ? (
        <div className="bg-card rounded-xl p-12 text-center border border-border">
          <FileText size={48} className="mx-auto text-text-secondary/30 mb-4" />
          <p className="text-text-secondary">暂无日报</p>
          <p className="text-xs text-text-secondary mt-1">系统会在每日 07:30 和 22:00 自动生成市场日报（需配置 AI API Key）</p>
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
