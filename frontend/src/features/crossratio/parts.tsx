import { useEffect, useState, type ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, CircleHelp, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { QualityGate } from '@/lib/models'

// ── Adım yönergesi: ne yapmalı + neden + canlı kontroller ──────────────────────

export interface Check {
  ok: boolean | null        // null = henüz değerlendirilemez
  text: string
  hint?: string             // ok=false iken ne yapılmalı
}

export function StepGuide({
  title, instruction, why, checks, children,
}: {
  title: string
  instruction: ReactNode
  why?: ReactNode
  checks?: Check[]
  children?: ReactNode
}) {
  const [showWhy, setShowWhy] = useState(false)
  return (
    <div className="space-y-3 rounded-xl border bg-card p-4 shadow-card">
      <div>
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        <div className="mt-1 text-sm leading-relaxed text-foreground/90">{instruction}</div>
      </div>
      {why && (
        <div>
          <button type="button" onClick={() => setShowWhy((v) => !v)}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
            <CircleHelp className="size-3.5" /> {showWhy ? 'Gizle' : 'Neden bu adım?'}
          </button>
          {showWhy && <div className="mt-1.5 rounded-md bg-muted/60 p-2.5 text-xs leading-relaxed text-muted-foreground">{why}</div>}
        </div>
      )}
      {children}
      {checks && checks.length > 0 && (
        <ul className="space-y-1.5 border-t pt-3">
          {checks.map((c, i) => (
            <li key={i} className="flex items-start gap-2 text-xs">
              {c.ok === null ? <span className="mt-0.5 size-3.5 shrink-0 rounded-full border-2 border-muted-foreground/30" />
                : c.ok ? <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-success" />
                  : <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-warning" />}
              <span>
                <span className={cn(c.ok === false && 'font-medium text-amber-800')}>{c.text}</span>
                {c.ok === false && c.hint && <span className="block text-muted-foreground">{c.hint}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Kare kaydırıcısı ──────────────────────────────────────────────────────────

export function FrameScrubber({
  value, min, max, onChange, marked, highlight,
}: {
  value: number
  min: number
  max: number
  onChange: (n: number) => void
  marked?: Set<number>
  highlight?: [number, number] | null
}) {
  const [draft, setDraft] = useState(String(value))
  useEffect(() => setDraft(String(value)), [value])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === 'INPUT') return
      if (e.key === 'ArrowRight') onChange(Math.min(max, value + (e.shiftKey ? 10 : 1)))
      if (e.key === 'ArrowLeft') onChange(Math.max(min, value - (e.shiftKey ? 10 : 1)))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [value, min, max, onChange])

  const span = Math.max(1, max - min)
  const pct = (n: number) => `${((n - min) / span) * 100}%`
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <button type="button" onClick={() => onChange(Math.max(min, value - 1))}
          className="flex size-8 items-center justify-center rounded-md border hover:bg-accent" title="Önceki kare (←)">
          <ChevronLeft className="size-4" />
        </button>
        <div className="relative flex-1">
          {highlight && (
            <div className="pointer-events-none absolute top-1/2 h-2 -translate-y-1/2 rounded bg-primary/25"
              style={{ left: pct(highlight[0]), width: `calc(${pct(highlight[1])} - ${pct(highlight[0])})` }} />
          )}
          {marked && [...marked].map((n) => (
            <span key={n} className="pointer-events-none absolute top-0 h-1.5 w-0.5 bg-emerald-500" style={{ left: pct(n) }} />
          ))}
          <input type="range" min={min} max={max} value={value}
            onChange={(e) => onChange(Number(e.target.value))} className="relative w-full" />
        </div>
        <button type="button" onClick={() => onChange(Math.min(max, value + 1))}
          className="flex size-8 items-center justify-center rounded-md border hover:bg-accent" title="Sonraki kare (→)">
          <ChevronRight className="size-4" />
        </button>
        <input value={draft} onChange={(e) => setDraft(e.target.value)}
          onBlur={() => { const n = Number(draft); if (Number.isFinite(n)) onChange(Math.round(Math.min(max, Math.max(min, n)))) }}
          onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
          className="h-8 w-20 rounded-md border px-2 text-center text-sm tabular-nums" aria-label="Kare numarası" />
      </div>
      <p className="text-[11px] text-muted-foreground">← / → bir kare, Shift ile on kare. Fare tekerleğiyle yakınlaşın.</p>
    </div>
  )
}

// ── "Temas noktası nedir / ne değildir" mini şeması ─────────────────────────────

export function ContactPointDiagram() {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-2.5">
      <svg viewBox="0 0 200 92" className="h-20 w-44 shrink-0" aria-label="Temas noktası şeması">
        <rect x="18" y="14" width="164" height="58" rx="6" fill="none" stroke="#94a3b8" strokeDasharray="4 3" />
        <path d="M30 56 L48 32 L150 30 L172 52 L172 60 L30 60 Z" fill="#cbd5e1" stroke="#64748b" />
        <circle cx="60" cy="64" r="11" fill="#1e293b" /><circle cx="60" cy="64" r="4" fill="#94a3b8" />
        <circle cx="146" cy="64" r="11" fill="#1e293b" /><circle cx="146" cy="64" r="4" fill="#94a3b8" />
        <line x1="4" y1="75" x2="196" y2="75" stroke="#64748b" strokeWidth="1.5" />
        {/* ✗ kutu alt-ortası */}
        <g transform="translate(100 72)"><line x1="-5" y1="-5" x2="5" y2="5" stroke="#ef4444" strokeWidth="2.5" /><line x1="-5" y1="5" x2="5" y2="-5" stroke="#ef4444" strokeWidth="2.5" /></g>
        {/* ✓ tekerlek-zemin teması */}
        <circle cx="146" cy="75" r="4" fill="#22c55e" stroke="#fff" strokeWidth="1.5" />
        <text x="100" y="89" textAnchor="middle" fontSize="9" fill="#ef4444">kutu altı ✗</text>
        <text x="146" y="89" textAnchor="middle" fontSize="9" fill="#16a34a">teker–zemin ✓</text>
      </svg>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Tıklayacağınız nokta, <b className="text-foreground">lastiğin yola değdiği</b> yerdir — araç kutusunun
        alt kenarı <b className="text-foreground">değil</b>. Kutu alt kenarı tampon/gölgeye denk gelir ve hızı
        sistematik olarak düşük gösterir.
      </p>
    </div>
  )
}

// ── Kalite kapıları ───────────────────────────────────────────────────────────

const SEV = {
  error: { Icon: XCircle, cls: 'border-red-200 bg-red-50 text-red-800' },
  warn: { Icon: AlertTriangle, cls: 'border-amber-200 bg-amber-50 text-amber-900' },
  info: { Icon: Info, cls: 'border-slate-200 bg-slate-50 text-slate-700' },
} as const

export function GateList({ gates }: { gates: QualityGate[] }) {
  const order = { error: 0, warn: 1, info: 2 } as const
  const sorted = [...gates].sort((a, b) => order[a.severity] - order[b.severity])
  if (sorted.length === 0)
    return <p className="text-sm text-success">Kalite kontrollerinin tümü geçti.</p>
  return (
    <ul className="space-y-2">
      {sorted.map((g, i) => {
        const { Icon, cls } = SEV[g.severity]
        return (
          <li key={i} className={cn('flex items-start gap-2 rounded-md border px-3 py-2 text-sm', cls)}>
            <Icon className="mt-0.5 size-4 shrink-0" />
            <div>
              <div>{g.message}</div>
              {g.action && <div className="mt-0.5 text-xs opacity-80">→ {g.action}</div>}
            </div>
          </li>
        )
      })}
    </ul>
  )
}

// ── Konum–zaman grafiği (eğim = hız) ─────────────────────────────────────────

export function PositionTimeChart({ times, positions, speedKmh }: { times: number[]; positions: number[]; speedKmh: number }) {
  const W = 420, H = 190, ML = 44, MR = 12, MT = 12, MB = 30
  if (times.length < 2) return null
  const t0 = Math.min(...times), t1 = Math.max(...times)
  const xs = positions
  const x0 = Math.min(...xs, 0), x1 = Math.max(...xs)
  const tx = (t: number) => ML + ((t - t0) / (t1 - t0 || 1)) * (W - ML - MR)
  const ty = (x: number) => MT + (1 - (x - x0) / (x1 - x0 || 1)) * (H - MT - MB)
  // En küçük kareler doğrusu (görsel — sayı sunucudan)
  const n = times.length
  const mt = times.reduce((a, b) => a + b, 0) / n
  const mx = xs.reduce((a, b) => a + b, 0) / n
  const slope = times.reduce((s, t, i) => s + (t - mt) * (xs[i] - mx), 0) / (times.reduce((s, t) => s + (t - mt) ** 2, 0) || 1)
  const fit = (t: number) => mx + slope * (t - mt)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-md rounded-md border bg-white">
      <rect x={ML} y={MT} width={W - ML - MR} height={H - MT - MB} fill="none" stroke="#e2e8f0" />
      <line x1={tx(t0)} y1={ty(fit(t0))} x2={tx(t1)} y2={ty(fit(t1))} stroke="#2563eb" strokeWidth={2} />
      {times.map((t, i) => (
        <circle key={i} cx={tx(t)} cy={ty(xs[i])} r={4} fill="#0f172a" stroke="#fff" strokeWidth={1.5} />
      ))}
      <text x={ML - 6} y={ty(x1) + 4} fontSize={10} textAnchor="end" fill="#64748b">{x1.toFixed(1)} m</text>
      <text x={ML - 6} y={ty(x0) + 4} fontSize={10} textAnchor="end" fill="#64748b">{x0.toFixed(1)} m</text>
      <text x={tx(t0)} y={H - 10} fontSize={10} textAnchor="middle" fill="#64748b">{t0.toFixed(2)} s</text>
      <text x={tx(t1)} y={H - 10} fontSize={10} textAnchor="middle" fill="#64748b">{t1.toFixed(2)} s</text>
      <text x={W - MR} y={MT + 14} fontSize={11} textAnchor="end" fill="#2563eb">eğim = {speedKmh.toFixed(1)} km/h</text>
    </svg>
  )
}

// ── Ondalık sayı alanı ────────────────────────────────────────────────────────

/** Yazarken ham metni tutar; virgül veya nokta kabul eder (tr-TR). Yalnızca geçerli, sonlu ve
 * `min` üstü değerler kaydedilir — "2," gibi ara girişler değeri bozmaz. */
export function DecimalField({
  value, onChange, min = 0, className, ariaLabel,
}: {
  value: number
  onChange: (n: number) => void
  min?: number
  className?: string
  ariaLabel?: string
}) {
  const fmt = (n: number) => String(n).replace('.', ',')
  const [draft, setDraft] = useState(fmt(value))
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setDraft(fmt(value)) }, [value, focused])
  const parsed = Number(draft.trim().replace(',', '.'))
  const valid = draft.trim() !== '' && Number.isFinite(parsed) && parsed >= min
  return (
    <input
      type="text" inputMode="decimal" aria-label={ariaLabel} value={draft}
      onFocus={() => setFocused(true)}
      onBlur={() => { setFocused(false); setDraft(fmt(value)) }}
      onChange={(e) => {
        setDraft(e.target.value)
        const n = Number(e.target.value.trim().replace(',', '.'))
        if (e.target.value.trim() !== '' && Number.isFinite(n) && n >= min) onChange(n)
      }}
      className={cn('flex h-9 w-full rounded-md border bg-background px-3 py-1 text-sm tabular-nums shadow-sm',
        !valid && 'border-red-400 bg-red-50', className)}
    />
  )
}
