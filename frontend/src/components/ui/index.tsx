import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

type PanelProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode
}

export function Panel({ className, children, ...props }: PanelProps) {
  return (
    <section className={cn('research-panel', className)} {...props}>
      {children}
    </section>
  )
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
}

const buttonVariants: Record<ButtonVariant, string> = {
  primary: 'border-blue-700 bg-blue-700 text-white hover:border-blue-800 hover:bg-blue-800',
  secondary: 'border-[#BFD2D7] bg-white text-[#28323C] hover:border-blue-600 hover:bg-blue-50',
  ghost: 'border-transparent bg-transparent text-[#3E5662] hover:bg-slate-100 hover:text-[#28323C]',
  danger: 'border-red-200 bg-white text-red-700 hover:bg-red-50',
}

export function Button({ className, variant = 'primary', type = 'button', ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50',
        buttonVariants[variant],
        className,
      )}
      type={type}
      {...props}
    />
  )
}

type StatusTone = 'blue' | 'amber' | 'slate' | 'red' | 'demo'

const statusTones: Record<StatusTone, string> = {
  blue: 'border-blue-200 bg-blue-50 text-blue-800',
  amber: 'border-amber-200 bg-amber-50 text-amber-800',
  slate: 'border-slate-200 bg-slate-50 text-slate-700',
  red: 'border-red-200 bg-red-50 text-red-700',
  demo: 'border-violet-200 bg-violet-50 text-violet-800',
}

export function StatusPill({ children, tone = 'slate' }: { children: ReactNode; tone?: StatusTone }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-semibold tracking-wide', statusTones[tone])}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-75" aria-hidden="true" />
      {children}
    </span>
  )
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-4 border-b border-[#D9E0E7] pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="research-eyebrow">{eyebrow}</p>
        <h1 className="mt-1.5 text-2xl font-semibold tracking-[-0.02em] text-[#28323C] sm:text-[1.75rem]">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-[#5E747F]">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-[#C9D9DE] bg-[#F8FAFC] px-5 py-8 text-center">
      <p className="text-sm font-semibold text-[#394957]">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#657B85]">{detail}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}

export function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="rounded-lg border border-[#D9E0E7] bg-white p-4">
      <p className="text-xs font-medium text-[#6B818B]">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[#28323C]">{value}</p>
      <p className="mt-1 text-xs leading-5 text-[#718791]">{detail}</p>
    </article>
  )
}
