import { useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api'
import type { QualityGate } from '@/lib/models'
import { Button } from '@/components/ui/button'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { StatusBanner } from '@/components/common/StatusBanner'
import { GateList, PositionTimeChart } from './parts'
import { useCrossRatio, XR_STEPS, type XrStepId } from './store'

/** Kalite kapısı → düzeltileceği adım. */
const GATE_STEP: Record<string, XrStepId> = {
  vp_disagreement_in_ci: 3,
  too_few_marks: 5, auto_marks_unconfirmed: 5, not_straight: 5, far_marks: 5,
  ref_off_line: 4, length_sigma_default: 4,
  vp_note: 3, vp_infinite: 3, vp_unreliable: 3, vp_uncertain: 3, vp_disagree: 3, trajectory_vp_failed: 3,
  fps_suspicious: 1,
}

const SRC_TR: Record<string, string> = {
  lane_manual: 'Şerit çizgileri (operatör)', lane_auto: 'Şerit çizgileri (otomatik)', trajectory: 'Araç izi (otomatik)',
}

/** Adım 6 — Hız ± güven aralığı, kullanılan girdiler ve kalite kontrolleri. */
export function ResultStep() {
  const st = useCrossRatio()
  const { jobId, trackId, result, setResult, goTo } = st

  const run = useMutation({
    mutationFn: () => api.crossRatioSpeed(jobId!, trackId!, {
      lane_lines: st.laneLines.length >= 2 ? st.laneLines : [],
      use_trajectory: st.useTrajectory,
      frame_start: st.frameStart,
      frame_end: st.frameEnd,
      vp_primary: st.vpPrimary,
      known_length: {
        kind: st.length.kind, length_m: st.length.lengthM, sigma_m: st.length.sigmaM,
        point_a: st.length.pointA!, point_b: st.length.pointB!, frame: st.length.frame,
      },
      marks: Object.entries(st.marks).map(([f, m]) => ({ frame: Number(f), pixel: m.pixel, source: m.source })),
      pixel_sigma: 1.0,
    }),
    onSuccess: setResult,
  })

  // Adıma girildiğinde (veya girdiler değişip sonuç temizlendiğinde) otomatik hesapla
  useEffect(() => {
    if (!result && !run.isPending && !run.isError) run.mutate()
  }, [result]) // eslint-disable-line react-hooks/exhaustive-deps

  if (run.isPending && !result)
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Hız hesaplanıyor — perspektif referansı belirsizliği örnekleniyor…
      </div>
    )
  if (run.isError)
    return (
      <div className="mx-auto max-w-2xl space-y-3">
        <StatusBanner tone="error">{(run.error as Error).message}</StatusBanner>
        <Button variant="secondary" onClick={() => run.mutate()}><RefreshCw className="size-4" /> Tekrar dene</Button>
      </div>
    )
  if (!result) return null

  const r = result
  const comp = r.ci_components_kmh
  const COMP_TR: Record<string, string> = {
    fit: 'İşaretleme / düzlük', vp: 'Perspektif referansı', length: 'Bilinen uzunluk',
    vp_disagreement: 'Referanslar arası fark',
  }
  const compRows: [string, string, number][] = Object.entries(comp).map(([k, v]) => [k, COMP_TR[k] ?? k, v ?? 0])
  const compTotal = Math.max(1e-9, compRows.reduce((s, [, , v]) => s + v ** 2, 0))
  const gatesWithStep = r.gates.map((g: QualityGate) => ({ g, step: GATE_STEP[g.code] }))
  const lengthLabel = st.length.kind === 'wheelbase' ? 'Dingil mesafesi' : 'Olay yeri mesafesi'

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-4">
        <div className="rounded-xl border bg-card p-5 shadow-card">
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Ölçülen hız</div>
          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <span className="text-5xl font-bold tabular-nums tracking-tight">{r.speed_kmh.toFixed(1)}</span>
            <span className="text-2xl font-semibold tabular-nums text-muted-foreground">± {r.ci_kmh.toFixed(1)} km/h</span>
            <ConfidenceBadge level={r.confidence_level} />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            ~%95 güven aralığı: <b className="tabular-nums text-foreground">{(r.speed_kmh - r.ci_kmh).toFixed(1)} – {(r.speed_kmh + r.ci_kmh).toFixed(1)} km/h</b>.
            Takip #{trackId}, kare {st.frameStart}–{st.frameEnd}.
          </p>

          <div className="mt-4 space-y-1.5">
            <div className="text-xs font-medium text-muted-foreground">Belirsizlik nereden geliyor?</div>
            {compRows.map(([k, name, v]) => (
              <div key={k} className="flex items-center gap-2 text-xs">
                <span className="w-44 shrink-0">{name}</span>
                <div className="h-2 flex-1 rounded bg-muted">
                  <div className="h-2 rounded bg-primary/70" style={{ width: `${(v ** 2 / compTotal) * 100}%` }} />
                </div>
                <span className="w-16 text-right tabular-nums">± {v.toFixed(2)}</span>
              </div>
            ))}
            <p className="text-[11px] text-muted-foreground">Toplam = bileşenlerin karelerinin toplamının karekökü. Çubuk, varyansa katkı payıdır.</p>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-5 shadow-card">
          <div className="mb-2 text-sm font-semibold">Konum – zaman</div>
          <PositionTimeChart times={r.times_s} positions={r.positions_m} speedKmh={r.speed_kmh} />
          <p className="mt-2 text-xs text-muted-foreground">
            Her nokta bir işaretli karedeki teker temasının yol boyunca konumudur. Doğrunun eğimi hızdır; noktalar doğrudan
            ne kadar az saparsa ölçüm o kadar tutarlıdır (artık RMS {(r.residual_rms_m * 100).toFixed(1)} cm).
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="rounded-xl border bg-card p-4 shadow-card">
          <div className="mb-2 text-sm font-semibold">Kalite kontrolleri</div>
          <GateList gates={r.gates} />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[...new Set(gatesWithStep.filter((x) => x.step && x.g.severity !== 'info').map((x) => x.step!))].map((s) => (
              <Button key={s} size="sm" variant="secondary" onClick={() => goTo(s)}>
                Düzelt: {XR_STEPS[s - 1].label}
              </Button>
            ))}
          </div>
        </div>

        <div className="rounded-xl border bg-card p-4 shadow-card">
          <div className="mb-2 text-sm font-semibold">Kullanılan girdiler</div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-xs">
            <dt className="text-muted-foreground">Yöntem</dt><dd>Cross-ratio (kaçış noktası + bilinen uzunluk, tek doğru)</dd>
            <dt className="text-muted-foreground">Perspektif ref.</dt>
            <dd>{SRC_TR[r.vp_used.source] ?? r.vp_used.source}
              {r.vp_used.point ? ` · (${r.vp_used.point[0].toFixed(0)}, ${r.vp_used.point[1].toFixed(0)}) px` : ' · sonsuzda'}
              {r.vp_used.sigma_major_px != null && ` · ±${r.vp_used.sigma_major_px.toFixed(1)} px`}</dd>
            {r.agreement && (<><dt className="text-muted-foreground">Çapraz kontrol</dt><dd>{r.agreement.message}</dd></>)}
            {r.speed_alternative_kmh != null && (<><dt className="text-muted-foreground">Diğer ref. ile hız</dt>
              <dd className="tabular-nums">{r.speed_alternative_kmh.toFixed(1)} km/h</dd></>)}
            <dt className="text-muted-foreground">{lengthLabel}</dt>
            <dd className="tabular-nums">{st.length.lengthM.toFixed(2)} m ± {(r.length_sigma_m * 100).toFixed(0)} cm</dd>
            <dt className="text-muted-foreground">İşaretler</dt><dd className="tabular-nums">{r.mark_count} kare, en büyük çizgi sapması {r.max_offset_px.toFixed(1)} px</dd>
            <dt className="text-muted-foreground">Kare hızı</dt><dd className="tabular-nums">{r.fps.toFixed(3)} fps ({r.fps_source === 'operator_override' ? 'operatör girdi' : 'video başlığı'})</dd>
            <dt className="text-muted-foreground">Belirsizlik örn.</dt><dd className="tabular-nums">{r.vp_mc_samples} örnek (sabit tohum — tekrarlanabilir)</dd>
          </dl>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Tüm girdiler ve sonuç bu analizin oturum kaydına yazıldı; aynı girdiler aynı sonucu verir.
          </p>
        </div>

        <Button variant="secondary" className="w-full" onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />} Yeniden hesapla
        </Button>
      </div>
    </div>
  )
}
