import { useState, useEffect, useRef } from 'react'
import { useMutation, type UseMutationResult } from '@tanstack/react-query'
import { Activity, Bot, CheckCheck, FileText, Loader2, Target, Trash2, Video } from 'lucide-react'
import { api } from '@/lib/api'
import type { ControlPoint, ProfilePoint, WheelMarkSource, WheelSpeedProfileResponse, WheelSpeedResponse } from '@/lib/models'
import type { WheelOverlayRequest } from '@/lib/models'
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
  onWheelOverlayReady?: (trackId: number) => void
}

// ── Hız-zaman profil grafiği (saf SVG, bağımlılık yok) ─────────────────────

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

  // CI şerit polygon
  const upperPath = points.map((p) => `${tx(p.t_s).toFixed(1)},${ty(p.speed_kmh + p.ci_kmh).toFixed(1)}`).join(' ')
  const lowerPath = [...points].reverse().map((p) => `${tx(p.t_s).toFixed(1)},${ty(p.speed_kmh - p.ci_kmh).toFixed(1)}`).join(' ')
  const ciPoly = points.length > 1 ? `${upperPath} ${lowerPath}` : ''

  // Hız çizgisi
  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${tx(p.t_s).toFixed(1)} ${ty(p.speed_kmh).toFixed(1)}`)
    .join(' ')

  // Y ızgara
  const vStep = 10
  const vStart = Math.ceil(vMin / vStep) * vStep
  const gridLines: number[] = []
  for (let v = vStart; v <= vMax; v += vStep) gridLines.push(v)

  // X ekseni zaman etiketleri
  const nTicks = Math.min(5, points.length)
  const tTicks: number[] = Array.from({ length: nTicks }, (_, i) =>
    tMin + (i * (tMax - tMin)) / Math.max(nTicks - 1, 1)
  )

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width={W}
      height={H}
      className="rounded border bg-white"
      style={{ maxWidth: '100%' }}
    >
      {/* Y ızgara + etiketler */}
      {gridLines.map((v) => (
        <g key={v}>
          <line
            x1={ML} y1={ty(v).toFixed(1)}
            x2={ML + cw} y2={ty(v).toFixed(1)}
            stroke="#e5e7eb" strokeWidth={1}
          />
          <text
            x={ML - 4} y={(ty(v) + 4).toFixed(1)}
            fontSize={9} textAnchor="end" fill="#9ca3af"
          >{v}</text>
        </g>
      ))}

      {/* CI şerit */}
      {ciPoly && (
        <polygon points={ciPoly} fill="#bfdbfe" opacity={0.5} />
      )}

      {/* Hız çizgisi */}
      <path d={linePath} fill="none" stroke="#1a1a6e" strokeWidth={2} strokeLinejoin="round" />

      {/* Noktalar */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={tx(p.t_s).toFixed(1)}
          cy={ty(p.speed_kmh).toFixed(1)}
          r={3.5}
          fill="#1a1a6e"
          stroke="white"
          strokeWidth={1}
        />
      ))}

      {/* X ekseni etiketleri */}
      {tTicks.map((t) => (
        <text
          key={t}
          x={tx(t).toFixed(1)}
          y={H - 6}
          fontSize={9}
          textAnchor="middle"
          fill="#9ca3af"
        >{t.toFixed(1)}s</text>
      ))}

      {/* Eksenler */}
      <rect
        x={ML} y={MT} width={cw} height={ch}
        fill="none" stroke="#d1d5db" strokeWidth={1}
      />

      {/* Eksen başlıkları */}
      <text x={2} y={MT + 10} fontSize={8} fill="#6b7280">km/h</text>
    </svg>
  )
}

// ── Ana panel ────────────────────────────────────────────────────────────────

type Mode = 'speed' | 'profile'

interface MarkEntry {
  frame: number
  pixel: [number, number]
  source: WheelMarkSource
}

/**
 * T16 + T19 + T20 — Operatör-tekerlek hız ölçümü, fren/ivme profili ve otomatik temas tespiti.
 */
export function WheelSpeedPanel({
  jobId, videoId, trackId, frameCount, onClose, onReportRegenerated, onWheelSpeedResult, onWheelOverlayReady,
}: Props) {
  const [mode, setMode] = useState<Mode>('speed')
  const [marks, setMarks] = useState<Record<number, { pixel: [number, number]; source: WheelMarkSource }>>({})
  const [currentFrame, setCurrentFrame] = useState(0)
  const [frameInput, setFrameInput] = useState('')
  const [speedResult, setSpeedResult] = useState<WheelSpeedResponse | null>(null)
  const [profileResult, setProfileResult] = useState<WheelSpeedProfileResponse | null>(null)

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

  const handleAdd = (pixel: [number, number]) => {
    setMarks((prev) => ({ ...prev, [currentFrame]: { pixel, source: 'manual' } }))
  }

  // Operatör mevcut noktayı hareket ettirince → "operator-confirmed"
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

  // T20: Auto noktayı onayla (source → operator-confirmed)
  const confirmMark = (frame: number) => {
    setMarks((prev) => ({
      ...prev,
      [frame]: { ...prev[frame], source: 'operator-confirmed' },
    }))
  }

  // T20: Tüm auto noktaları onayla
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

  // T21: Panel açılır açılmaz auto markları yükle (operatör butona tıklamak zorunda kalmasın)
  const autoLoadFired = useRef(false)
  useEffect(() => {
    if (!autoLoadFired.current) {
      autoLoadFired.current = true
      autoMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const calcSpeedMutation = useMutation({
    mutationFn: () =>
      api.wheelSpeed(jobId, trackId, {
        marks: markEntries.map((m) => ({ frame: m.frame, pixel: m.pixel, source: m.source })),
      }),
    onSuccess: (data) => {
      setSpeedResult(data)
      onWheelSpeedResult?.(trackId, data)
    },
  })

  const calcProfileMutation = useMutation({
    mutationFn: () =>
      api.wheelSpeedProfile(jobId, trackId, {
        marks: markEntries.map((m) => ({ frame: m.frame, pixel: m.pixel, source: m.source })),
      }),
    onSuccess: (data) => {
      setProfileResult(data)
      // Profil özet değerlerini WheelSpeedResponse formatında ilet (T21)
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
  })

  const regenerateMutation = useMutation({
    mutationFn: () => api.regenerateReport(jobId),
    onSuccess: () => onReportRegenerated?.(),
  })

  const handleReset = () => {
    setMarks({})
    setSpeedResult(null)
    setProfileResult(null)
    calcSpeedMutation.reset()
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
          <Target className="size-4 text-muted-foreground" />
          Hızı Ölç — Takip #{trackId}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>Kapat</Button>
      </div>

      {/* T20/T21: Auto noktalar mount'ta otomatik yüklenir; bu buton yeniden yükleme içindir */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={autoMutation.isPending}
          onClick={() => autoMutation.mutate()}
          className="text-xs"
        >
          {autoMutation.isPending
            ? <Loader2 className="size-3 animate-spin" />
            : <Bot className="size-3" />}
          {autoMutation.isPending
            ? 'Yükleniyor…'
            : autoMutation.isSuccess
              ? 'Yeniden Yükle'
              : autoMutation.isError
                ? 'Tekrar Dene'
                : 'Yükleniyor…'}
        </Button>
        {autoMarkCount > 0 && (
          <>
            <span className="text-xs text-amber-700">
              {autoMarkCount} onaylanmamış auto nokta
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-amber-700 hover:text-amber-900"
              onClick={confirmAllAutoMarks}
            >
              <CheckCheck className="size-3 mr-1" />
              Tümünü Onayla
            </Button>
          </>
        )}
        {confirmedCount > 0 && (
          <span className="text-xs text-green-700">
            {confirmedCount} onaylı
          </span>
        )}
      </div>
      {autoMutation.isError && (
        <StatusBanner tone="error">
          {(autoMutation.error as Error).message}
        </StatusBanner>
      )}

      {/* Mod seçimi */}
      <div className="flex rounded-md border overflow-hidden text-xs font-medium">
        <button
          className={`flex-1 py-1.5 px-3 flex items-center justify-center gap-1.5 transition-colors
            ${mode === 'speed'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted text-muted-foreground'}`}
          onClick={() => setMode('speed')}
        >
          <Target className="size-3" />
          Tek Hız
        </button>
        <button
          className={`flex-1 py-1.5 px-3 flex items-center justify-center gap-1.5 transition-colors border-l
            ${mode === 'profile'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted text-muted-foreground'}`}
          onClick={() => setMode('profile')}
        >
          <Activity className="size-3" />
          Fren/İvme Profili
        </button>
      </div>

      {/* Yönlendirme */}
      <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5 text-sm text-blue-800 space-y-1">
        <p className="font-medium">
          {mode === 'speed' ? 'Nasıl yapılır? (3 adım)' : 'Profil modu — nasıl yapılır?'}
        </p>
        {mode === 'speed' ? (
          <ol className="list-decimal list-inside text-xs space-y-0.5 text-blue-700">
            <li>Videoda aracın bir tekerin yere değdiği yere tıkla.</li>
            <li>İleri/geri ile farklı bir kareye geç — AYNI tekeri tekrar tıkla. En az 2, tercihen 3-5 kare.</li>
            <li>"Hızı Hesapla" düğmesine bas.</li>
          </ol>
        ) : (
          <ol className="list-decimal list-inside text-xs space-y-0.5 text-blue-700">
            <li>Aynı tekeri fren/hareket boyunca en az {minMarksProfile}, tercihen 5-8 farklı karede işaretle.</li>
            <li>Yeterli işaret sonrası "Profil Hesapla" ile hız-zaman eğrisini ve ivmeyi gör.</li>
            <li>İsteğe bağlı: "Overlay Oluştur" ile kare-kare hız etiketi içeren video üret.</li>
          </ol>
        )}
      </div>

      {/* Kare navigasyonu */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>Kare: <span className="font-semibold tabular-nums text-foreground">{currentFrame}</span></span>
        <Button variant="outline" size="sm" className="h-7 px-2"
          onClick={() => goToFrame(currentFrame - 1)}>
          ← Önceki
        </Button>
        <Button variant="outline" size="sm" className="h-7 px-2"
          onClick={() => goToFrame(currentFrame + 1)}>
          Sonraki →
        </Button>
        <Input
          type="number"
          placeholder="kare no"
          value={frameInput}
          onChange={(e) => setFrameInput(e.target.value)}
          className="h-7 w-24"
        />
        <Button
          variant="secondary" size="sm" className="h-7 px-2"
          disabled={frameInput === ''}
          onClick={() => {
            const n = Number(frameInput)
            if (Number.isFinite(n)) goToFrame(n)
          }}
        >
          Git
        </Button>
        {marks[currentFrame] && (
          <span className="text-green-600 text-xs font-medium">✓ Bu kare işaretlendi</span>
        )}
      </div>

      {/* Video karesi + işaret canvas */}
      <CalibrationCanvas
        imageUrl={api.frameUrl(videoId, currentFrame)}
        points={canvasPoints}
        selectedId={null}
        onAdd={handleAdd}
        onMove={handleMove}
        onSelect={() => {}}
      />

      {/* İşaret listesi */}
      {markEntries.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">
            İşaretler ({markEntries.length}) — hepsinde AYNI teker olmalı:
            {mode === 'profile' && markEntries.length < minMarksProfile && (
              <span className="text-amber-600 ml-1">
                ({minMarksProfile - markEntries.length} işaret daha gerekli)
              </span>
            )}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {markEntries.map((m) => (
              <div
                key={m.frame}
                className={`flex items-center gap-1 rounded border px-2 py-0.5 text-xs cursor-pointer
                  ${m.frame === currentFrame
                    ? 'border-primary bg-primary/10'
                    : m.source === 'auto'
                      ? 'border-amber-400 bg-amber-50 text-amber-900'
                      : m.source === 'operator-confirmed'
                        ? 'border-green-400 bg-green-50 text-green-900'
                        : 'border-border bg-card'}`}
                onClick={() => setCurrentFrame(m.frame)}
              >
                <span className="tabular-nums">
                  {m.source === 'auto' && '⚠ '}
                  {m.source === 'operator-confirmed' && '✓ '}
                  Kare {m.frame}
                </span>
                {m.source === 'auto' && (
                  <button
                    className="text-amber-600 hover:text-green-700"
                    title="Onayla"
                    onClick={(e) => { e.stopPropagation(); confirmMark(m.frame) }}
                  >
                    <CheckCheck className="size-3" />
                  </button>
                )}
                <button
                  className="text-muted-foreground hover:text-destructive"
                  onClick={(e) => { e.stopPropagation(); removeMark(m.frame) }}
                >
                  <Trash2 className="size-3" />
                </button>
              </div>
            ))}
          </div>
          {autoMarkCount > 0 && (
            <p className="text-[0.65rem] text-amber-700">
              ⚠ Turuncu işaretler otomatik tespit (parallax uyarısı) — Canvas'ta düzelt veya "Onayla" düğmesine bas.
            </p>
          )}
        </div>
      )}

      {/* Aksiyon butonları */}
      <div className="flex flex-wrap items-center gap-2">
        {mode === 'speed' ? (
          <Button
            size="sm"
            disabled={markEntries.length < 2 || calcSpeedMutation.isPending}
            onClick={() => calcSpeedMutation.mutate()}
          >
            {calcSpeedMutation.isPending ? <Loader2 className="animate-spin" /> : <Target />}
            Hızı Hesapla
            {markEntries.length < 2 && ' (en az 2 işaret)'}
          </Button>
        ) : (
          <Button
            size="sm"
            disabled={!canCalcProfile || calcProfileMutation.isPending}
            onClick={() => calcProfileMutation.mutate()}
          >
            {calcProfileMutation.isPending ? <Loader2 className="animate-spin" /> : <Activity />}
            Profil Hesapla
            {!canCalcProfile && ` (en az ${minMarksProfile} işaret)`}
          </Button>
        )}
        {(markEntries.length > 0 || speedResult || profileResult) && (
          <Button variant="ghost" size="sm" onClick={handleReset}>
            Sıfırla
          </Button>
        )}
      </div>

      {calcSpeedMutation.isError && (
        <StatusBanner tone="error">{(calcSpeedMutation.error as Error).message}</StatusBanner>
      )}
      {calcProfileMutation.isError && (
        <StatusBanner tone="error">{(calcProfileMutation.error as Error).message}</StatusBanner>
      )}

      {/* Tek hız sonucu (mod: speed) */}
      {mode === 'speed' && speedResult && (
        <SpeedResult
          result={speedResult}
          jobId={jobId}
          trackId={trackId}
          regenerateMutation={regenerateMutation}
          onOverlayReady={onWheelOverlayReady ? () => onWheelOverlayReady(trackId) : undefined}
        />
      )}

      {/* Profil sonucu (mod: profile) */}
      {mode === 'profile' && profileResult && (
        <ProfileResult
          result={profileResult}
          jobId={jobId}
          trackId={trackId}
          overLayMutation={overLayMutation}
          regenerateMutation={regenerateMutation}
        />
      )}
    </div>
  )
}

// ── Tek hız sonuç kartı ──────────────────────────────────────────────────────

function SpeedResult({
  result,
  jobId,
  trackId,
  regenerateMutation,
  onOverlayReady,
}: {
  result: WheelSpeedResponse
  jobId: string
  trackId: number
  regenerateMutation: UseMutationResult<unknown, Error, void>
  onOverlayReady?: () => void
}) {
  const overlayMutation = useMutation({
    mutationFn: () => api.generateWheelOverlay(jobId, trackId, {
      value_kmh: result.value_kmh,
      ci_kmh: result.ci_kmh,
      confidence_level: result.confidence_level,
    } satisfies WheelOverlayRequest),
    onSuccess: () => onOverlayReady?.(),
  })

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">Operatör-Tekerlek Hızı</div>
          <div className="text-3xl font-bold tabular-nums leading-none">
            {result.value_kmh.toFixed(1)}
            <span className="text-base font-normal text-muted-foreground ml-1">km/h</span>
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">Güven Aralığı</div>
          <div className="text-lg font-semibold tabular-nums">
            ± {result.ci_kmh.toFixed(1)} km/h
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">Güven</div>
          <ConfidenceBadge level={result.confidence_level} />
        </div>
        <div>
          <div className="text-xs text-muted-foreground mb-0.5">İşaret</div>
          <div className="text-sm tabular-nums">{result.mark_count} kare</div>
        </div>
      </div>

      {result.warnings.length > 0 && (
        <StatusBanner tone="warning">{result.warnings.join(' ')}</StatusBanner>
      )}

      <div className="text-[0.7rem] text-muted-foreground">
        Residual: {result.residual_kmh.toFixed(1)} km/h — ardışık çift hız std'si.
      </div>

      {/* T25 — Tekerlek hızı overlay */}
      <div className="border-t pt-3 flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={overlayMutation.isPending || overlayMutation.isSuccess}
          onClick={() => overlayMutation.mutate()}
        >
          {overlayMutation.isPending ? <Loader2 className="animate-spin" /> : <Video />}
          {overlayMutation.isSuccess ? 'Overlay hazır ✓' : 'Bu Hızla Overlay Oluştur'}
        </Button>
        {overlayMutation.isError && (
          <StatusBanner tone="error">{(overlayMutation.error as Error).message}</StatusBanner>
        )}
        {overlayMutation.isSuccess && (
          <p className="w-full text-[0.7rem] text-muted-foreground">
            Overlay oluşturuldu. Sonuç ekranındaki video seçicide "Tekerlek #{trackId}" seçeneği aktif oldu.
          </p>
        )}
      </div>

      <ReportButton regenerateMutation={regenerateMutation} />
    </div>
  )
}

// ── Profil sonuç kartı ───────────────────────────────────────────────────────

function ProfileResult({
  result,
  jobId,
  trackId,
  overLayMutation,
  regenerateMutation,
}: {
  result: WheelSpeedProfileResponse
  jobId: string
  trackId: number
  overLayMutation: UseMutationResult<{ overlay_path: string; download_url: string }, Error, void>
  regenerateMutation: UseMutationResult<unknown, Error, void>
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
      <div>
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Özet (birincil, T16 yöntemi)
        </div>
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
            <div className="text-lg font-semibold tabular-nums">
              ± {result.summary_ci_kmh.toFixed(1)} km/h
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-0.5">Güven</div>
            <ConfidenceBadge level={result.summary_confidence_level} />
          </div>
        </div>
      </div>

      {/* Profil istatistikleri */}
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

      {/* Hız-zaman grafiği */}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-1.5">
          Hız-Zaman Profili
          <span className="text-[0.65rem] ml-2 font-normal">
            (mavi şerit = ±CI; noktalar = segment orta noktaları)
          </span>
        </div>
        <SpeedProfileChart points={result.points} />
      </div>

      {/* Profil nokta tablosu */}
      {result.points.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1">Profil Noktaları</div>
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
                {result.points.map((p, i) => (
                  <tr key={i} className={i % 2 === 0 ? '' : 'bg-muted/20'}>
                    <td className="border border-border px-2 py-0.5 tabular-nums">{p.t_s.toFixed(2)}</td>
                    <td className="border border-border px-2 py-0.5 tabular-nums text-right">{p.speed_kmh.toFixed(1)}</td>
                    <td className="border border-border px-2 py-0.5 tabular-nums text-right">± {p.ci_kmh.toFixed(1)}</td>
                    <td className={`border border-border px-2 py-0.5 tabular-nums text-right
                      ${p.accel_ms2 !== null && p.accel_ms2 < -2 ? 'text-orange-600 font-medium' : ''}`}>
                      {p.accel_ms2 !== null ? p.accel_ms2.toFixed(2) : '—'}
                    </td>
                  </tr>
                ))}
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

      {/* Overlay ve rapor butonları */}
      <div className="border-t pt-3 space-y-2">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={overLayMutation.isPending || overLayMutation.isSuccess}
            onClick={() => overLayMutation.mutate()}
          >
            {overLayMutation.isPending ? <Loader2 className="animate-spin" /> : <Video />}
            {overLayMutation.isSuccess ? 'Overlay hazır ✓' : 'Fren Overlay Oluştur'}
          </Button>

          {overLayMutation.isSuccess && (
            <a
              href={api.profileOverlayUrl(jobId, trackId)}
              download={`fren_analizi_track${trackId}.mp4`}
            >
              <Button variant="secondary" size="sm">
                <Video /> İndir
              </Button>
            </a>
          )}
        </div>

        {overLayMutation.isError && (
          <StatusBanner tone="error">
            {(overLayMutation.error as Error).message}
          </StatusBanner>
        )}

        {overLayMutation.isSuccess && (
          <p className="text-[0.7rem] text-muted-foreground">
            Overlay videoda işaretli karelerde yeşil dolu etiket, ara karelerde sarı kenarlı etiket gösterilir.
          </p>
        )}

        <ReportButton regenerateMutation={regenerateMutation} />
      </div>
    </div>
  )
}

// ── Rapor güncelleme butonu (ortak) ──────────────────────────────────────────

function ReportButton({
  regenerateMutation,
}: {
  regenerateMutation: UseMutationResult<unknown, Error, void>
}) {
  return (
    <div className="space-y-2">
      <Button
        variant="outline"
        size="sm"
        disabled={regenerateMutation.isPending || regenerateMutation.isSuccess}
        onClick={() => regenerateMutation.mutate()}
      >
        {regenerateMutation.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
        {regenerateMutation.isSuccess ? 'Rapor güncellendi ✓' : 'Sonucu PDF Raporuna Ekle'}
      </Button>
      {!regenerateMutation.isSuccess && (
        <p className="text-[0.7rem] text-amber-700">
          ⚠ Sonuç otomatik rapora eklenmez. Yukarıdaki düğme ile orijinal rapor
          korunarak tekerlek hızı/profil dahil yeni bir rapor (rapor_v2.pdf) oluşturulur.
        </p>
      )}
      {regenerateMutation.isError && (
        <StatusBanner tone="error">
          {(regenerateMutation.error as Error).message}
        </StatusBanner>
      )}
    </div>
  )
}
