import { useEffect, useState, useRef } from 'react'
import { Bot, ExternalLink, Send, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { aliceApi } from '@/api'

interface AliceStatus {
  online: boolean
  enabled: boolean
  base_url?: string
  message?: string
}

interface ChatMessage {
  role: 'user' | 'alice'
  content: string
  timestamp: string
}

function StatusBadge({ status }: { status: AliceStatus | null }) {
  if (!status) {
    return (
      <div className="flex items-center gap-2 text-text-secondary text-sm">
        <RefreshCw size={14} className="animate-spin" /> 检测连接中...
      </div>
    )
  }

  if (!status.enabled) {
    return (
      <div className="flex items-center gap-2 text-text-secondary text-sm">
        <WifiOff size={14} />
        <span>未启用 — 请在「系统设置」中开启 OpenAlice</span>
      </div>
    )
  }

  if (!status.online) {
    return (
      <div className="flex items-center gap-2 text-amber-500 text-sm">
        <WifiOff size={14} />
        <span>{status.message || '未连接'}</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 text-success text-sm">
      <Wifi size={14} />
      <span>已连接</span>
      {status.base_url && (
        <a
          href={status.base_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-primary hover:underline ml-2"
        >
          打开完整界面 <ExternalLink size={12} />
        </a>
      )}
    </div>
  )
}

function ChatPanel({ enabled }: { enabled: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return

    const userMsg: ChatMessage = { role: 'user', content: text, timestamp: new Date().toLocaleTimeString('zh-CN') }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const resp = await aliceApi.ask(text)
      const data = resp.data
      const reply = data.error
        ? `[Error] ${data.error}`
        : (data.response || data.content || data.text || JSON.stringify(data))
      setMessages((prev) => [...prev, {
        role: 'alice',
        content: reply,
        timestamp: new Date().toLocaleTimeString('zh-CN'),
      }])
    } catch {
      setMessages((prev) => [...prev, {
        role: 'alice',
        content: '[Error] 请求失败，请检查 OpenAlice 是否在运行',
        timestamp: new Date().toLocaleTimeString('zh-CN'),
      }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-card rounded-xl border border-border flex flex-col" style={{ height: '400px' }}>
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <Bot size={16} className="text-primary" />
        <h3 className="text-sm font-semibold">AI 交易助手</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-text-secondary text-sm py-8">
            <Bot size={32} className="mx-auto mb-2 opacity-30" />
            <p>向 Alice 提问关于市场、交易策略、技术分析等问题</p>
            <p className="text-xs mt-1">例如：「BTC 当前的技术面怎么看？」</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-3.5 py-2.5 text-sm ${
              msg.role === 'user'
                ? 'bg-primary text-white'
                : 'bg-bg border border-border text-text'
            }`}>
              <p className="whitespace-pre-wrap break-words">{msg.content}</p>
              <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-white/60' : 'text-text-secondary'}`}>
                {msg.timestamp}
              </p>
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-bg border border-border rounded-xl px-3.5 py-2.5 text-sm text-text-secondary">
              <RefreshCw size={14} className="animate-spin inline mr-1.5" />
              Alice 正在思考...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-3 border-t border-border flex gap-2">
        <input
          className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary disabled:opacity-50"
          placeholder={enabled ? '输入消息...' : 'OpenAlice 未连接'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          disabled={!enabled || sending}
        />
        <button
          onClick={handleSend}
          disabled={!enabled || sending || !input.trim()}
          className="px-3 py-2 bg-primary text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}

export default function OpenAlice() {
  const [status, setStatus] = useState<AliceStatus | null>(null)
  const [checking, setChecking] = useState(true)

  const checkStatus = async () => {
    setChecking(true)
    try {
      const resp = await aliceApi.status()
      setStatus(resp.data)
    } catch {
      setStatus({ online: false, enabled: false, message: '无法连接后端' })
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => { checkStatus() }, [])

  const isConnected = status?.online && status?.enabled

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold">OpenAlice</h2>
          <StatusBadge status={status} />
        </div>
        <button
          onClick={checkStatus}
          disabled={checking}
          className="flex items-center gap-1.5 px-3 py-2 border border-border rounded-lg text-sm hover:bg-bg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={checking ? 'animate-spin' : ''} />
          刷新状态
        </button>
      </div>

      {!status?.enabled && !checking && (
        <div className="bg-card rounded-xl border border-border p-8 text-center mb-6">
          <Bot size={48} className="mx-auto mb-4 text-text-secondary opacity-30" />
          <h3 className="font-semibold mb-2">OpenAlice 未启用</h3>
          <p className="text-sm text-text-secondary mb-4 max-w-md mx-auto">
            OpenAlice 是一个独立的 AI 交易引擎，需要单独安装和启动。启用后可以通过 AI 助手进行交易分析、查看实时行情。
          </p>
          <div className="text-left bg-bg rounded-lg border border-border p-4 max-w-lg mx-auto text-xs font-mono space-y-1">
            <p className="text-text-secondary"># 1. 安装 OpenAlice</p>
            <p>git clone https://github.com/TraderAlice/OpenAlice.git</p>
            <p>cd OpenAlice && pnpm install && pnpm build</p>
            <p className="text-text-secondary mt-2"># 2. 启动</p>
            <p>pnpm dev</p>
            <p className="text-text-secondary mt-2"># 3. 在本站「系统设置」中启用 OpenAlice</p>
          </div>
        </div>
      )}

      {status?.enabled && !status?.online && !checking && (
        <div className="bg-card rounded-xl border border-amber-500/20 p-6 text-center mb-6">
          <WifiOff size={32} className="mx-auto mb-3 text-amber-500" />
          <h3 className="font-semibold mb-1">OpenAlice 未运行</h3>
          <p className="text-sm text-text-secondary">
            已启用但无法连接到 {status.base_url || 'http://localhost:3002'}，请确认 OpenAlice 已启动。
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
        <ChatPanel enabled={!!isConnected} />
      </div>
    </div>
  )
}
