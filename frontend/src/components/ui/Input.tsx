import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

const baseStyles = 'rounded-lg border border-border text-sm bg-white dark:bg-card focus:outline-none focus:ring-2 focus:ring-primary/30'

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(baseStyles, 'px-3 py-2', className)} {...props} />
  ),
)
Input.displayName = 'Input'

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select ref={ref} className={cn(baseStyles, 'px-3 py-2', className)} {...props} />
  ),
)
Select.displayName = 'Select'

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea ref={ref} className={cn(baseStyles, 'px-2 py-1.5 resize-none', className)} {...props} />
  ),
)
Textarea.displayName = 'Textarea'
