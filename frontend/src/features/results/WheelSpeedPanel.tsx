import { useState, useEffect, useRef } from 'react'
import { useMutation, type UseMutationResult } from '@tanstack/react-query'
import { Activity, Bot, CheckCheck, FileText, Loader2, Trash2, Video } from 'lucide-react'
import { api } from '@/lib/api'
import type { ControlPoint, ProfilePoint, WheelMarkSource, WheelSpeedProfileResponse, WheelSpeedResponse } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBanner } from '@/components/common/StatusBanner'
import { ConfidenceBadge } from '@/components/common/ConfidenceBadge'
import { CalibrationCanvas } from '@/features/calibration/CalibrationCanvas'

interface Props {
  jobId: string
  videoId: string
  trackId: number
  frameCount: number
  onClose: () => void
  onReportRegenerated?: () => void
  onWheelSpeedResult?: (trackId: number, result: WheelSpeedResponse) => void
  onProfileOverlayReady?: (trackId: number) => void
  onSeekToFrame?: (frame: number) => void
}

// ── Hız-zaman profil grafiği ─────────────────────────────────────────────────

function SpeedProfileChart({ points }: { points: ProfilePoint[] }) {
  if (points.length === 0) return null

  const W = 480, H = 160, ML = 42, MR = 12, MT = 12, MB = 30
  const cw = W - ML - MR
  const ch = H - MT - MB

  const times = points.map((p) => p.t_s)
  const speeds = points.map((p) => p.speed_kmh)
  const cis = points.map((p) => p.ci_kmh)

  const tMin = Math.min(...times)
  const tMax = Math.max(...times)
  const vMin = Math.max(0, Math.min(...speeds) - Math.max(10, Math.max(...cis) * 1.5))
  const vMax = Math.max(...speeds) + Math.max(10, Math.max(...cis) * 1.5)

  const tx = (t: number) => ML + (cw * (t - tMin)) / Math.max(tMax - tMin, 0.001)
  const ty = (v: number) => MT + ch - (ch * (v - vMin)) / Math.max(vMax - vMin, 0.001)

  const upperPath = points.map((p) => `${tx(p.t_s).toFixed(1)},${ty(p.speed_kmh + p.ci_kmh).toFixed(1)}`).join(' ')
  const lowerPath = [...points].reverse().map((p) => `${tx(p.t_s).toFixed(1)},${ty(p.speed_kmh - p.ci_kmh).toFixed(1)}`).join(' ')
  const ciPoly = points.length > 1 ? `${upperPath} ${lowerPath}` : ''
  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${tx(p.t_s).toFixed(1)} ${ty(p.speed_kmh).toFixed(1)}`)
    .join(' ')

  const vStep = 10
  const vStart = Math.ceil(vMin / vStep) * vStep
  const gridLines: number[] = []
  for (let v = vStart; v <= vMax; v += vStep) gridLines.push(v)

  const nTicks = Math.min(5, points.length)
  const tTicks: number[] = Array.from({ length: nTicks }, (_, i) =>
    tMin + (i * (tMax - tMin)) / Math.max(nTicks - 1, 1)
  )

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H}
      className="rounded border bg-white" style={{ maxWidth: '100%' }}>
      {gridLines.map((v) => (
        <g key={v}>
          <line x1={ML} y1={ty(v).toFixed(1)} x2={ML + cw} y2={ty(v).toFixed(1)} stroke="#e5e7eb" strokeWidth={1} />
          <text x={ML - 4} y={(ty(v) + 4).toFixed(1)} fontSize={9} textAnchor="end" fill="#9ca3af">{v}</text>
        </g>
      ))}
      {ciPoly && <polygon points={ciPoly} fill="#bfdbfe" opacity={0.5} />}
      <path d={linePath} fill="none" stroke="#1a1a6e" strokeWidth={2} strokeLinejoin="round" />
      {points.map((p, i) => (
        <circle key={i} cx={tx(p.t_s).toFixed(1)} cy={ty(p.speed_kmh).toFixed(1)}
          r={3.5} fill="#1a1a6e" stroke="white" strokeWidth={1} />
      ))}
      {tTicks.map((t) => (
        <text key={t} x={tx(t).toFixed(1)} y={H - 6} fontSize={9} textAnchor="middle" fill="#9ca3af">
          {t.toFixed(1)}s
        </text>
      ))}
      <rect x={ML} y={MT} width={cw} height={ch} fill="none" stroke="#d1d5db" strokeWidth={1} />
      <text x={2} y={MT + 10} fontSize={8} fill="#6b7280">km/h</text>
    </svg>
  )
}

// ── Ana panel ────────────────────────────────────────────────────────────────

interface MarkEntry {
  frame: number
  pixel: [number, number]
  source: WheelMarkSource
}

export function WheelSpeedPanel({
  jobId, videoId, trackId, frameCount, onClose, onReportRegenerated, onWheelSpeedResult, onProfileOverlayReady, onSeekToFrame,
}: Props) {
  const fps = useWizard((s) => s.videoMeta?.fps ?? 25)

  const [marks, setMarks] = useState<Record<number, { pixel: [number, number]; source: WheelMarkSource }>>({})
  const [currentFrame, setCurrentFrame] = useState(0)
  const [frameInput, setFrameInput] = useState('')
  const [profileResult, setProfileResult] = useState<WheelSpeedProfileResponse | null>(null)

  const canvasAreaRef = useRef<HTMLDivElement>(null)

  const markEntries: MarkEntry[] = Object.entries(marks)
    .map(([f, m]) => ({ frame: Number(f), pixel: m.pixel, source: m.source }))
    .sort((a, b) => a.frame - b.frame)

  const currentMark = marks[currentFrame]
  const currentPixel = currentMark?.pixel
  const canvasPoints: ControlPoint[] = currentPixel
    ? [{ id: 'wheel_mark', pixel: currentPixel, world_m: [0, 0], source: 'operator', held_out: false }]
    : []

  const goToFrame = (n: number) => {
    const clamped = Math.max(0, Math.min(frameCount - 1, n))
    setCurrentFrame(clamped)
  }

  // Profil tablosundan: profil varsa video seek, yoksa canvas'a git
  const handleGoToFrame = (n: number) => {
    if (onSeekToFrame) {
      onSeekToFrame(n)
    } else {
      goToFrame(n)
      canvasAreaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }

  const handleAdd = (pixel: [number, number]) => {
    setMarks((prev) => ({ ...prev, [currentFrame]: { pixel, source: 'manual' } }))
  }

  const handleMove = (_id: string, pixel: [number, number]) => {
    setMarks((prev) => ({
      ...prev,
      [currentFrame]: {
        pixel,
        source: prev[currentFrame]?.source === 'auto' ? 'operator-confirmed' : (prev[currentFrame]?.source ?? 'manual'),
      },
    }))
  }

  const removeMark = (frame: number) => {
    setMarks((prev) => {
      const next = { ...prev }
      delete next[frame]
      return next
    })
  }

  const confirmMark = (frame: number) => {
    setMarks((prev) => ({ ...prev, [frame]: { ...prev[frame], source: 'operator-confirmed' } }))
  }

  const confirmAllAutoMarks = () => {
    setMarks((prev) => {
      const next = { ...prev }
      for (const f of Object.keys(next)) {
        if (next[Number(f)].source === 'auto') {
          next[Number(f)] = { ...next[Number(f)], source: 'operator-confirmed' }
        }
      }
      return next
    })
  }

  const autoMutation = useMutation({
    mutationFn: () => api.autoContactPoints(jobId, trackId, 8),
    onSuccess: (data: import('@/lib/models').AutoContactPointsResponse) => {
      setMarks((prev) => {
        const next = { ...prev }
        for (const m of data.marks) {
          if (!(m.frame in next)) {
            next[m.frame] = { pixel: m.pixel as [number, number], source: 'auto' }
          }
        }
        return next
      })
    },
  })

  const autoLoadFired = useRef(false)
  useEffect(() => {
    if (!autoLoadFired.current) {
      autoLoadFired.current = true
      autoMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const calcProfileMutation = useMutation({
    mutationFn: () =>
      api.wheelSpeedProfile(jobId, trackId, {
        marks: markEntries.map((m) => ({ frame: m.frame, pixel: m.pixel, source: m.source })),
      }),
    onSuccess: (data) => {
      setProfileResult(data)
      onWheelSpeedResult?.(trackId, {
        value_kmh: data.summary_value_kmh,
        ci_kmh: data.summary_ci_kmh,
        confidence_level: data.summary_confidence_level,
        mark_count: data.summary_mark_count,
        residual_kmh: data.summary_residual_kmh,
        warnings: data.warnings,
      })
    },
  })

  const overLayMutation = useMutation({
    mutationFn: () =>
      api.generateProfileOverlay(jobId, trackId, {
        marks: markEntries.map((m) => ({ frame: m.frame, pixel: m.pixel, source: m.source })),
      }),
    onSuccess: () => onProfileOverlayReady?.(trackId),
  })

  const regenerateMutation = useMutation({
    mutationFn: (speedLimitKmh?: number) => api.regenerateReport(jobId, speedLimitKmh),
    onSuccess: () => onReportRegenerated?.(),
  })

  const handleReset = () => {
    setMarks({})
    setProfileResult(null)
    calcProfileMutation.reset()
    overLayMutation.reset()
    regenerateMutation.reset()
    autoMutation.reset()
  }

  const autoMarkCount = markEntries.filter((m) => m.source === 'auto').length
  const confirmedCount = markEntries.filter((m) => m.source === 'operator-confirmed').length
  const minMarksProfile = 3
  const canCalcProfile = markEntries.length >= minMarksProfile

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      {/* Başlık */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Activity className="size-4 text-muted-foreground" />
          Fren/İvme Profili — Takip #{trackId}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>Kapat</Button>
      </div>

      {/* Auto nokta durumu */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline" size="sm"
          disabled={autoMutation.isPending}
          onClick={() => autoMutation.mutate()}
          className="text-xs"
        >
          {autoMutation.isPending ? <Loader2 className="size-3 animate-spin" /> : <Bot className="size-3" />}
          {autoMutation.isPending ? 'Yükleniyor…' : autoMutation.isSuccess ? 'Yeniden Yükle' : autoMutation.isError ? 'Tekrar Dene' : 'Yükleniyor…'}
        </Button>
        {autoMarkCount > 0 && (
          <>
            <span className="text-xs text-amber-700">{autoMarkCount} onaylanmamış auto nokta</span>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-amber-700 hover:text-amber-900"
              onClick={confirmAllAutoMarks}>
              <CheckCheck className="size-3 mr-1" /> Tümünü Onayla
            </Button>
          </>
        )}
        {confirmedCount > 0 && (
          <span className="text-xs text-green-700">{confirmedCount} onaylı</span>
        )}
      </div>
      {autoMutation.isError && (
        <StatusBanner tone="error">{(autoMutation.error as Error).message}</StatusBanner>
      )}

      {/* İşaret & canvas — profil hesaplandıktan sonra gizlenir */}
      {!profileResult ? (
        <>
          <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm text-blue-800 space-y-1">
            <p className="font-medium">Nasıl yapılır? (3 adım)</p>
            <ol className="list-decimal list-inside text-xs space-y-0.5 text-blue-700">
              <li>Aynı tekeri fren/hareket boyunca en az {minMarksProfile}, tercihen 5-8 farklı karede işaretle.</li>
              <li>"Profil Hesapla" ile hız-zaman eğrisini ve ivmeyi gör.</li>
              <li>"Fren Overlay Oluştur" ile video üret — ana videoda görünür.</li>
            </ol>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Kare: <span className="font-semibold tabular-nums text-foreground">{currentFrame}</span></span>
            <Button variant="outline" size="sm" className="h-7 px-2" onClick={() => goToFrame(currentFrame - 1)}>← Önceki</Button>
            <Button variant="outline" size="sm" className="h-7 px-2" onClick={() => goToFrame(currentFrame + 1)}>Sonraki →</Button>
            <Input type="number" placeholder="kare no" value={frameInput}
              onChange={(e) => setFrameInput(e.target.value)} className="h-7 w-24" />
            <Button variant="secondary" size="sm" className="h-7 px-2" disabled={frameInput === ''}
              onClick={() => { const n = Number(frameInput); if (Number.isFinite(n)) goToFrame(n) }}>
              Git
            </Button>
            {marks[currentFrame] && (
              <span className="text-green-600 text-xs font-medium">✓ Bu kare işaretlendi</span>
            )}
          </div>

          <div ref={canvasAreaRef}>
            <CalibrationCanvas
              imageUrl={api.frameUrl(videoId, currentFrame)}
              points={canvasPoints}
              selectedId={null}
              onAdd={handleAdd}
              onMove={handleMove}
              onSelect={() => {}}
            />
          </div>

          {markEntries.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">
                İşaretler ({markEntries.length}) — hepsinde AYNI teker olmalı:
                {markEntries.length < minMarksProfile && (
                  <span className="text-amber-600 ml-1">({minMarksProfile - markEntries.length} daha gerekli)</span>
                )}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {markEntries.map((m) => (
                  <div
                    key={m.frame}
                    className={`flex items-center gap-1 rounded border px-2 py-0.5 text-xs cursor-pointer
                      ${m.frame === currentFrame ? 'border-primary bg-primary/10'
                        : m.source === 'auto' ? 'border-amber-400 bg-amber-50 text-amber-900'
                        : m.source === 'operator-confirmed' ? 'border-green-400 bg-green-50 text-green-900'
                        : 'border-border bg-card'}`}
                    onClick={() => setCurrentFrame(m.frame)}
                  >
                    <span className="tabular-nums">
                      {m.source === 'auto' && '⚠ '}
                      {m.source === 'operator-confirmed' && '✓ '}
                      K{m.frame}
                    </span>
                    {m.source === 'auto' && (
                      <button className="text-amber-600 hover:text-green-700" title="Onayla"
                        onClick={(e) => { e.stopPropagation(); confirmMark(m.frame) }}>
                        <CheckCheck className="size-3" />
                      </button>
                    )}
                    <button className="text-muted-foreground hover:text-destructive"
                      onClick={(e) => { e.stopPropagation(); removeMark(m.frame) }}>
                      <Trash2 className="size-3" />
                    </button>
                  </div>
                ))}
              </div>
              {autoMarkCount > 0 && (
                <p className="text-[0.65rem] text-amber-700">
                  ⚠ Turuncu = otomatik tespit — canvas'ta düzelt veya onayla.
                </p>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm"
              disabled={!canCalcProfile || calcProfileMutation.isPending}
              onClick={() => calcProfileMutation.mutate()}>
              {calcProfileMutation.isPending ? <Loader2 className="animate-spin" /> : <Activity />}
              Profil Hesapla{!canCalcProfile && ` (en az ${minMarksProfile})`}
            </Button>
            {markEntries.length > 0 && (
              <Button variant="ghost" size="sm" onClick={handleReset}>Sıfırla</Button>
            )}
          </div>
        </>
      ) : (
        /* Profil hesaplandı — işaret özetini kompakt göster, "Yeniden Düzenle" butonu */
        <div className="flex items-center gap-3 rounded-md border border-success/30 bg-success/5 px-3 py-2 text-xs text-success">
          <Activity className="size-3.5 shrink-0" />
          <span>{markEntries.length} kare işareti ile profil hesaplandı.</span>
          <Button variant="ghost" size="sm" className="ml-auto h-6 px-2 text-muted-foreground text-xs"
            onClick={handleReset}>
            Yeniden Düzenle
          </Button>
        </div>
      )}

      {calcProfileMutation.isError && (
        <StatusBanner tone="error">{(calcProfileMutation.error as Error).message}</StatusBanner>
      )}

      {profileResult && (
        <ProfileResult
          result={profileResult}
          fps={fps}
          onGoToFrame={handleGoToFrame}
          overLayMutation={overLayMutation}
          regenerateMutation={regenerateMutation}
          trackId={trackId}
        />
      )}
    </div>
  )
}

// ── Profil sonuç kartı ───────────────────────────────────────────────────────

function ProfileResult({
  result,
  fps,
  trackId,
  onGoToFrame,
  overLayMutation,
  regenerateMutation,
}: {
  result: WheelSpeedProfileResponse
  fps: number
  trackId: number
  onGoToFrame: (frame: number) => void
  overLayMutation: UseMutationResult<{ overlay_path: string; download_url: string }, Error, void>
  regenerateMutation: UseMutationResult<unknown, Error, number | undefined>
}) {
  const firstSpeed = result.points[0]?.speed_kmh ?? 0
  const lastSpeed = result.points[result.points.length - 1]?.speed_kmh ?? 0
  const maxDecel = result.points
    .filter((p) => p.accel_ms2 !== null)
    .reduce<number | null>((min, p) => {
      const a = p.accel_ms2!
      return min === null || a < min ? a : min
    }, null)

  return (
    <div className="rounded-lg border bg-card p-4 space-y-4">
      {/* Özet */}
      <div className="flex items-center gap-3 flex-wrap">
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">Ortalama Hız</div>
          <div className="text-3xl font-bold tabular-nums leading-none">
            {result.summary_value_kmh.toFixed(1)}
            <span className="text-base font-normal text-muted-foreground ml-1">km/h</span>
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">CI</div>
          <div className="text-lg font-semibold tabular-nums">± {result.summary_ci_kmh.toFixed(1)} km/h</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">Güven</div>
          <ConfidenceBadge level={result.summary_confidence_level} />
        </div>
      </div>

      {/* İstatistikler */}
      <div className="grid grid-cols-3 gap-3 text-center text-sm">
        <div className="rounded border bg-muted/40 py-2">
          <div className="text-xs text-muted-foreground">Başlangıç hızı</div>
          <div className="font-semibold tabular-nums">{firstSpeed.toFixed(1)} km/h</div>
        </div>
        <div className="rounded border bg-muted/40 py-2">
          <div className="text-xs text-muted-foreground">Bitiş hızı</div>
          <div className="font-semibold tabular-nums">{lastSpeed.toFixed(1)} km/h</div>
        </div>
        <div className="rounded border bg-muted/40 py-2">
          <div className="text-xs text-muted-foreground">Maks. yavaşlama</div>
          <div className="font-semibold tabular-nums text-orange-600">
            {maxDecel !== null ? `${maxDecel.toFixed(2)} m/s²` : '—'}
          </div>
        </div>
      </div>

      {/* Grafik */}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-1.5">
          Hız-Zaman Profili
          <span className="text-[0.65rem] ml-2 font-normal">(mavi şerit = ±CI)</span>
        </div>
        <SpeedProfileChart points={result.points} />
      </div>

      {/* Profil nokta tablosu */}
      {result.points.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1">
            Profil Noktaları
            <span className="text-[0.65rem] ml-1 font-normal text-muted-foreground/60">
              — satıra tıkla → o kareye git (canvas yukarıda güncellenir)
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-muted/60">
                  <th className="border border-border px-2 py-1 text-left">t (s)</th>
                  <th className="border border-border px-2 py-1 text-right">Hız (km/h)</th>
                  <th className="border border-border px-2 py-1 text-right">CI (km/h)</th>
                  <th className="border border-border px-2 py-1 text-right">İvme (m/s²)</th>
                </tr>
              </thead>
              <tbody>
                {result.points.map((p, i) => {
                  const targetFrame = Math.round(p.t_s * fps)
                  return (
                    <tr
                      key={i}
                      className={`cursor-pointer hover:bg-primary/10 transition-colors ${i % 2 === 0 ? '' : 'bg-muted/20'}`}
                      title={`Kare ${targetFrame}'e git`}
                      onClick={() => onGoToFrame(targetFrame)}
                    >
                      <td className="border border-border px-2 py-0.5 tabular-nums text-primary underline-offset-2 hover:underline">
                        {p.t_s.toFixed(2)}
                      </td>
                      <td className="border border-border px-2 py-0.5 tabular-nums text-right">{p.speed_kmh.toFixed(1)}</td>
                      <td className="border border-border px-2 py-0.5 tabular-nums text-right">± {p.ci_kmh.toFixed(1)}</td>
                      <td className={`border border-border px-2 py-0.5 tabular-nums text-right
                        ${p.accel_ms2 !== null && p.accel_ms2 < -2 ? 'text-orange-600 font-medium' : ''}`}>
                        {p.accel_ms2 !== null ? p.accel_ms2.toFixed(2) : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="text-[0.65rem] text-muted-foreground mt-1">
            Ham çift hızlar (audit): [{result.raw_pairwise_kmh.map((v) => v.toFixed(1)).join(', ')}] km/h
            · Pencere: {result.smoothing_window}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <StatusBanner tone="warning">{result.warnings.join(' ')}</StatusBanner>
      )}

      {/* Overlay + Rapor */}
      <div className="border-t pt-3 space-y-3">
        {!overLayMutation.isSuccess ? (
          <Button variant="outline" size="sm" disabled={overLayMutation.isPending} onClick={() => overLayMutation.mutate()}>
            {overLayMutation.isPending ? <Loader2 className="animate-spin" /> : <Video />}
            {overLayMutation.isPending ? 'Oluşturuluyor…' : 'Fren Overlay Oluştur'}
          </Button>
        ) : (
          <div className="flex items-center gap-2 rounded-md border border-success/40 bg-success/5 px-3 py-2 text-xs text-success">
            <Video className="size-3.5 shrink-0" />
            Fren overlay hazır — yukarıdaki videoda <strong className="mx-1">"Fren #{trackId}"</strong> sekmesini seç.
          </div>
        )}
        {overLayMutation.isError && (
          <StatusBanner tone="error">{(overLayMutation.error as Error).message}</StatusBanner>
        )}
        <ReportButton regenerateMutation={regenerateMutation} />
      </div>
    </div>
  )
}

// ── Rapor güncelleme butonu ──────────────────────────────────────────────────

function ReportButton({ regenerateMutation }: {
  regenerateMutation: UseMutationResult<unknown, Error, number | undefined>
}) {
  const [speedLimit, setSpeedLimit] = useState<string>('')

  const handleGenerate = () => {
    const val = speedLimit.trim() === '' ? undefined : parseFloat(speedLimit)
    regenerateMutation.mutate(val && !isNaN(val) && val > 0 ? val : undefined)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <label className="text-xs text-muted-foreground whitespace-nowrap">
          Mahaldeki hız limiti (km/h):
        </label>
        <input
          type="number" min="0" max="300" placeholder="örn. 50"
          value={speedLimit}
          onChange={(e) => {
            setSpeedLimit(e.target.value)
            if (regenerateMutation.isSuccess) regenerateMutation.reset()
          }}
          className="w-20 rounded border border-input bg-background px-2 py-1 text-xs"
        />
        <span className="text-xs text-muted-foreground">(boş bırakılırsa eklenmez)</span>
      </div>
      <Button
        variant="outline" size="sm"
        disabled={regenerateMutation.isPending || regenerateMutation.isSuccess}
        onClick={handleGenerate}
      >
        {regenerateMutation.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
        {regenerateMutation.isSuccess ? 'Rapor güncellendi ✓' : 'Sonucu PDF Raporuna Ekle'}
      </Button>
      {!regenerateMutation.isSuccess && (
        <p className="text-[0.7rem] text-amber-700">
          ⚠ Sonuç otomatik rapora eklenmez. Yukarıdaki düğme yeni bir rapor (rapor_v2.pdf) oluşturur.
        </p>
      )}
      {regenerateMutation.isError && (
        <StatusBanner tone="error">{(regenerateMutation.error as Error).message}</StatusBanner>
      )}
    </div>
  )
}
