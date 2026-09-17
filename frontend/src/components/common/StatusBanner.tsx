import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

type Tone = 'info' | 'success' | 'warning' | 'error'

const TONES: Record<Tone, { cls: string; Icon: typeof Info }> = {
  info: { cls: 'border-blue-200 bg-blue-50 text-blue-700', Icon: Info },
  success: { cls: 'border-success/30 bg-success/10 text-success', Icon: CheckCircle2 },
  warning: { cls: 'border-amber-200 bg-amber-50 text-amber-800', Icon: AlertTriangle },
  error: { cls: 'border-red-200 bg-red-50 text-red-700', Icon: XCircle },
}

export function StatusBanner({
  tone = 'info',
  children,
  className,
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  const { cls, Icon } = TONES[tone]
  return (
    <div className={cn('flex items-start gap-2 rounded-md border px-3 py-2 text-sm', cls, className)}>
      <Icon className="mt-0.5 size-4 shrink-0" />
      <div>{children}</div>
    </div>
  )
}
