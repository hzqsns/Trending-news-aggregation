import { useState, useEffect, useCallback } from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ToastContext, type ToastContextValue } from './toastContext'

type ToastType = 'success' | 'error' | 'info'

interface ToastData {
  id: number
  type: ToastType
  message: string
}

let _nextId = 0

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([])

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++_nextId
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const value: ToastContextValue = {
    toast: addToast,
    success: (msg) => addToast('success', msg),
    error: (msg) => addToast('error', msg),
    info: (msg) => addToast('info', msg),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[999] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={() => remove(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

const icons = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
}

const styles = {
  success: 'border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400',
  error: 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400',
  info: 'border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400',
}

function ToastItem({ toast, onClose }: { toast: ToastData; onClose: () => void }) {
  const [visible, setVisible] = useState(false)
  const Icon = icons[toast.type]

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true))
  }, [])

  return (
    <div
      className={cn(
        'pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-sm',
        'transition-all duration-300 ease-out max-w-sm',
        visible ? 'translate-x-0 opacity-100' : 'translate-x-8 opacity-0',
        styles[toast.type],
      )}
    >
      <Icon size={16} className="shrink-0" />
      <span className="text-sm flex-1">{toast.message}</span>
      <button onClick={onClose} className="shrink-0 opacity-50 hover:opacity-100">
        <X size={14} />
      </button>
    </div>
  )
}
