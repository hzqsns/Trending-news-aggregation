import { cn } from '@/lib/utils'
import { forwardRef } from 'react'

const variants = {
  primary: 'bg-primary text-white hover:bg-primary-dark disabled:opacity-50',
  secondary: 'border border-border text-text-secondary hover:bg-bg disabled:opacity-40',
  danger: 'bg-red-500 text-white hover:bg-red-600 disabled:opacity-50',
  ghost: 'text-text-secondary hover:text-text hover:bg-bg',
} as const

const sizes = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-3 py-1.5 text-sm',
  lg: 'px-4 py-2 text-sm',
} as const

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants
  size?: keyof typeof sizes
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-1.5 rounded font-medium transition-colors',
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      />
    )
  },
)

Button.displayName = 'Button'
