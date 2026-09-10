import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, Milestone, TriangleAlert } from 'lucide-react'
import { api } from '@/lib/api'
import type { AxleStepResponse, ControlPoint } from '@/lib/models'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatusBanner } from '@/components/common/StatusBanner'
import { CalibrationCanvas } from '@/features/calibration/CalibrationCanvas'

interface Props {
  jobId: string
  videoId: string
  trackId: number
  onClose: () => void
}

const WHEELBASE_PRESETS: { label: string; value: number }[] = [
  { label: 'Otomobil (~2.65 m)', value: 2.65 },
  { label: 'Minibüs (~2.95 m)', value: 2.95 },
  { label: 'Minibüs büyük (~3.20 m)', value: 3.2 },
  { label: 'Kamyon (~3.80 m)', value: 3.8 },
  { label: 'Otobüs (~5.40 m)', value: 5.4 },
]

function ResultCard({
  data,
  wheelbase,
  isAuto,
}: {
  data: AxleStepResponse
  wheelbase: number
  isAuto: boolean
}) {
  const hWindowKmh = data.h_speed_window_kmh ?? null
  const diff =
    data.speed_kmh != null && hWindowKmh != null
      ? Math.abs(data.speed_kmh - hWindowKmh)
      : null

  return (
    <div className="rounded-lg border bg-card p-3 text-sm space-y-3">
      {data.interrupted && (
        <div className="flex items-start gap-2 text-xs text-amber-700">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          <span>
            <span className="font-medium">Track kesintisi:</span> {data.interrupt_reason}{' '}
            Hesaplama erken sonlandı.
          </span>
        </div>
      )}

      {data.speed_kmh == null ? (
        <StatusBanner tone="warning">
          Yetersiz adım ({data.step_count} adım) — hız hesaplanamadı. En az 2 adım gerekli.
          {isAuto
            ? ' Track çok kısa olabilir, manuel moda geçip farklı wheelbase deneyin.'
            : ' Dingil mesafesini veya başlangıç karesini değiştirip tekrar deneyin.'}
        </StatusBanner>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="rounded-md border p-2">
              <div className="text-xs text-muted-foreground">Dingil Adımlama</div>
              <div className="mt-0.5 text-lg font-bold tabular-nums">
                {data.speed_kmh.toFixed(1)}{' '}
                <span className="text-sm font-normal text-muted-foreground">km/h</span>
              </div>
              <div className="text-xs text-muted-foreground">
                ± {data.ci_kmh?.toFixed(1) ?? '—'} km/h · {data.step_count} adım
              </div>
            </div>
            <div className="rounded-md border p-2">
              <div className="text-xs text-muted-foreground">
                H-tabanlı {hWindowKmh != null ? '(aynı pencere)' : '(veri yok)'}
              </div>
              {hWindowKmh != null ? (
                <>
                  <div className="mt-0.5 text-lg font-bold tabular-nums">
                    {hWindowKmh.toFixed(1)}{' '}
                    <span className="text-sm font-normal text-muted-foreground">km/h</span>
                  </div>
                  {diff != null && (
                    <div
                      className={`text-xs ${diff < 3 ? 'text-green-600' : diff < 8 ? 'text-amber-600' : 'text-red-600'}`}
                    >
                      Fark: {diff.toFixed(1)} km/h
                      {diff < 3 ? ' ✓ tutarlı' : diff < 8 ? ' ⚠ orta sapma' : ' ✗ büyük sapma'}
                    </div>
                  )}
                </>
              ) : (
                <div className="mt-0.5 text-sm text-muted-foreground">Sonuç verisi mevcut değil</div>
              )}
            </div>
          </div>

          {!isAuto && data.initial_distance_m != null && (
            <div className="text-xs text-muted-foreground">
              Ölçülen başlangıç ön–arka mesafesi:{' '}
              <span className="tabular-nums font-medium text-foreground">
                {data.initial_distance_m.toFixed(2)} m
              </span>{' '}
              (girilen: {wheelbase.toFixed(2)} m
              {Math.abs(data.initial_distance_m - wheelbase) > 0.3 && (
                <span className="text-amber-600"> — büyük fark, teker işaretlerini kontrol edin</span>
              )}
              )
            </div>
          )}

          {isAuto && (
            <div className="text-xs text-muted-foreground">
              Yön vektörü track'in {data.step_count + 1}+ karesinden PCA ile tahmin edildi.
            </div>
          )}
        </>
      )}

      <p className="text-[0.7rem] text-muted-foreground">
        Bu sonuç yalnızca çapraz doğrulama amaçlıdır. Confidence seviyesi hesabına dahil
        edilmez; PDF raporuna otomatik eklenmez.
      </p>
    </div>
  )
}

export function AxleSteppingPanel({ jobId, videoId, trackId, onClose }: Props) {
  const [mode, setMode] = useState<'auto' | 'manual'>('auto')
  const [points, setPoints] = useState<ControlPoint[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [wheelbase, setWheelbase] = useState(2.65)
  const [manualFrame, setManualFrame] = useState<number | null>(null)
  const [frameInput, setFrameInput] = useState('')

  const frameQuery = useQuery({
    queryKey: ['axleSuggestFrame', jobId, trackId],
    queryFn: () => api.axleSuggestFrame(jobId, trackId),
    enabled: mode === 'manual',
  })

  const autoMutation = useMutation({
    mutationFn: () => api.axleStepAuto(jobId, trackId, { wheelbase_m: wheelbase }),
  })

  const manualMutation = useMutation({
    mutationFn: () => {
      const front = points.find((p) => p.id === 'axle_front')
      const rear = points.find((p) => p.id === 'axle_rear')
      if (!front || !rear) throw new Error('Ön ve arka teker işaretleyin.')
      return api.axleStep(jobId, trackId, {
        frame_n: frameN!,
        front_pixel: front.pixel,
        rear_pixel: rear.pixel,
        wheelbase_m: wheelbase,
      })
    },
  })

  const activeMutation = mode === 'auto' ? autoMutation : manualMutation

  const handleAdd = (pixel: [number, number]) => {
    setPoints((prev) => {
      if (prev.length === 0) {
        return [{ id: 'axle_front', pixel, world_m: [0, 0], source: 'auto', held_out: false }]
      }
      if (prev.length === 1 && !prev.find((p) => p.id === 'axle_rear')) {
        return [...prev, { id: 'axle_rear', pixel, world_m: [0, 0], source: 'site_measurement', held_out: false }]
      }
      return prev
    })
  }

  const handleMove = (id: string, pixel: [number, number]) => {
    setPoints((prev) => prev.map((p) => (p.id === id ? { ...p, pixel } : p)))
  }

  const handleReset = () => {
    setPoints([])
    setSelectedId(null)
    manualMutation.reset()
  }

  const switchMode = (next: 'auto' | 'manual') => {
    setMode(next)
    autoMutation.reset()
    manualMutation.reset()
    handleReset()
  }

  const goToFrame = (n: number) => {
    if (n < 0) return
    setManualFrame(n)
    handleReset()
  }

  const frameN = manualFrame ?? frameQuery.data?.frame_n

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      {/* Başlık */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Milestone className="size-4 text-muted-foreground" /> Dingil Adımlama — Takip #{trackId}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Kapat
        </Button>
      </div>

      {/* Mod seçici */}
      <div className="flex gap-1 rounded-md border p-0.5 w-fit bg-background">
        <button
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            mode === 'auto'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => switchMode('auto')}
        >
          Otomatik
        </button>
        <button
          className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
            mode === 'manual'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => switchMode('manual')}
        >
          Manuel
        </button>
      </div>

      {/* ── OTOMATİK MOD ── */}
      {mode === 'auto' && (
        <>
          <p className="text-xs text-muted-foreground">
            Yön vektörü track'in tüm noktalarından otomatik tahmin edilir. Yalnızca dingil
            mesafesini seçip hesaplat.
          </p>

          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted-foreground">
              Dingil mesafesi (m)
              <div className="mt-1 flex gap-1.5">
                <Input
                  type="number"
                  step="0.01"
                  value={wheelbase}
                  onChange={(e) => setWheelbase(Number(e.target.value))}
                  className="h-8 w-28"
                />
                <select
                  className="h-8 rounded-md border bg-background px-2 text-xs"
                  value=""
                  onChange={(e) => {
                    const v = Number(e.target.value)
                    if (v) setWheelbase(v)
                  }}
                >
                  <option value="">Hazır seç…</option>
                  {WHEELBASE_PRESETS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
            </label>

            <Button
              size="sm"
              disabled={autoMutation.isPending}
              onClick={() => autoMutation.mutate()}
            >
              {autoMutation.isPending ? <Loader2 className="animate-spin" /> : <Milestone />}
              Hesapla
            </Button>
          </div>
        </>
      )}

      {/* ── MANUEL MOD ── */}
      {mode === 'manual' && (
        <>
          <p className="text-xs text-muted-foreground">
            Aracın <span className="font-semibold text-blue-600">ön</span> (1. tıklama) ve{' '}
            <span className="font-semibold text-green-600">arka</span> (2. tıklama) teker temas
            noktasını işaretleyin, dingil mesafesini girin.
          </p>

          {frameQuery.isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Aday kare belirleniyor…
            </div>
          )}

          {frameN != null && (
            <>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>
                  Kare:{' '}
                  <span className="font-semibold tabular-nums text-foreground">{frameN}</span>
                  {manualFrame == null && ' (öneri)'}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => goToFrame(Math.max(0, frameN - 1))}
                >
                  ← Önceki
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => goToFrame(frameN + 1)}
                >
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
                  variant="secondary"
                  size="sm"
                  className="h-7 px-2"
                  disabled={frameInput === ''}
                  onClick={() => {
                    const n = Number(frameInput)
                    if (Number.isFinite(n)) goToFrame(n)
                  }}
                >
                  Git
                </Button>
                {manualFrame != null && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2"
                    onClick={() => goToFrame(frameQuery.data?.frame_n ?? 0)}
                  >
                    Öneriye dön
                  </Button>
                )}
              </div>

              <div className="flex gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <span className="inline-block size-2.5 rounded-full bg-blue-400" />
                  Ön teker (1. tıklama)
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block size-2.5 rounded-full bg-emerald-400" />
                  Arka teker (2. tıklama)
                </span>
                {points.length < 2 && (
                  <span className="text-amber-600">
                    {points.length === 0 ? 'Ön tekeri tıklayın' : 'Arka tekeri tıklayın'}
                  </span>
                )}
              </div>

              <CalibrationCanvas
                imageUrl={api.frameUrl(videoId, frameN)}
                points={points}
                selectedId={selectedId}
                onAdd={handleAdd}
                onMove={handleMove}
                onSelect={setSelectedId}
              />
            </>
          )}

          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted-foreground">
              Dingil mesafesi (m)
              <div className="mt-1 flex gap-1.5">
                <Input
                  type="number"
                  step="0.01"
                  value={wheelbase}
                  onChange={(e) => setWheelbase(Number(e.target.value))}
                  className="h-8 w-28"
                />
                <select
                  className="h-8 rounded-md border bg-background px-2 text-xs"
                  value=""
                  onChange={(e) => {
                    const v = Number(e.target.value)
                    if (v) setWheelbase(v)
                  }}
                >
                  <option value="">Hazır seç…</option>
                  {WHEELBASE_PRESETS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
            </label>

            <Button
              size="sm"
              disabled={points.length < 2 || manualMutation.isPending}
              onClick={() => manualMutation.mutate()}
            >
              {manualMutation.isPending ? <Loader2 className="animate-spin" /> : <Milestone />}
              Hesapla
            </Button>
            <Button variant="secondary" size="sm" onClick={handleReset}>
              Noktaları Sıfırla
            </Button>
          </div>
        </>
      )}

      {/* Hata */}
      {activeMutation.isError && (
        <StatusBanner tone="error">{(activeMutation.error as Error).message}</StatusBanner>
      )}

      {/* Sonuç */}
      {activeMutation.isSuccess && activeMutation.data && (
        <ResultCard
          data={activeMutation.data}
          wheelbase={wheelbase}
          isAuto={mode === 'auto'}
        />
      )}
    </div>
  )
}
