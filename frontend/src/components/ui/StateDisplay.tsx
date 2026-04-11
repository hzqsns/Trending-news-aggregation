import { cn } from '@/lib/utils'

interface StateDisplayProps {
  className?: string
}

export function Loading({ className }: StateDisplayProps) {
  return (
    <div className={cn('flex items-center justify-center h-64 text-text-secondary', className)}>
      加载中...
    </div>
  )
}

export function Empty({ className, children }: StateDisplayProps & { children?: React.ReactNode }) {
  return (
    <div className={cn('p-8 text-center text-text-secondary', className)}>
      {children || '暂无数据'}
    </div>
  )
}
