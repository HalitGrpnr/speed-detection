import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, Play } from 'lucide-react'
import { api } from '@/lib/api'
import type { ModelSize } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { StatusBanner } from '@/components/common/StatusBanner'
import { DecimalField, StepGuide } from './parts'
import { useCrossRatio } from './store'

const MODELS: { id: ModelSize; label: string; note: string }[] = [
  { id: 'nano', label: 'Hızlı', note: 'düşük donanım, kısa süre' },
  { id: 'small', label: 'Dengeli', note: '' },
  { id: 'medium', label: 'Hassas', note: 'önerilen — küçük/uzak araçları daha iyi bulur' },
]

/** Adım 1 — Araçları bul ve kareler boyunca takip et (kalibrasyon gerekmez). */
export function TrackingStep() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const jobId = useCrossRatio((s) => s.jobId)
  const setJob = useCrossRatio((s) => s.setJob)
  const tracks = useCrossRatio((s) => s.tracks)
  const setTracks = useCrossRatio((s) => s.setTracks)
  const goTo = useCrossRatio((s) => s.goTo)

  const [model, setModel] = useState<ModelSize>('medium')
  const [fpsOn, setFpsOn] = useState(false)
  const [fps, setFps] = useState(videoMeta?.fps ?? 25)

  const start = useMutation({
    mutationFn: () => api.startTracking({
      video_id: videoMeta!.video_id, model_size: model, frame_step: 1,
      fps_override: fpsOn ? fps : null,
    }),
    onSuccess: (r) => setJob(r.job_id),
  })

  const status = useQuery({
    queryKey: ['xrJobStatus', jobId],
    queryFn: () => api.jobStatus(jobId!),
    enabled: !!jobId && tracks.length === 0,
    refetchInterval: (q) => (['done', 'error'].includes(q.state.data?.state ?? '') ? false : 1200),
    refetchIntervalInBackground: true,  // operatör başka pencereye geçse de uzun takip izlenir
  })
  const done = status.data?.state === 'done' || tracks.length > 0
  const failed = status.data?.state === 'error'

  const tracksQuery = useQuery({
    queryKey: ['xrTracks', jobId],
    queryFn: () => api.jobTracks(jobId!),
    enabled: !!jobId && done,
  })
  // Yalnızca izler ilk geldiğinde ilerle — operatör geri dönerse bu adımda kalabilsin.
  useEffect(() => {
    if (tracksQuery.data && tracks.length === 0) {
      setTracks(tracksQuery.data)
      if (tracksQuery.data.length > 0) goTo(2)
    }
  }, [tracksQuery.data, tracks.length, setTracks, goTo])

  if (!videoMeta) return <StatusBanner tone="warning">Önce bir video yükleyin.</StatusBanner>
  const running = !!jobId && !done && !failed

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <StepGuide
        title="1 · Araçları bul ve takip et"
        instruction={<>Sistem videodaki araçları bulur ve her birini kareler boyunca izler. Bu adımda
          <b> hiçbir ölçüm yapılmaz</b>; yalnızca bir sonraki adımda ölçülecek aracı seçebilmeniz için araç kutuları çıkarılır.</>}
        why={<>Hız, aracın <i>düz gittiği</i> kısa bir aralıkta ölçülür. O aralığı ve aracı seçmek için önce araçların
          hangi karelerde nerede olduğunu bilmek gerekir. Tespit tamamen bu bilgisayarda çalışır; video hiçbir yere gönderilmez.</>}
        checks={[
          { ok: jobId ? (done ? true : null) : null, text: 'Takip tamamlandı' },
          { ok: tracks.length > 0 ? true : done && tracksQuery.data ? tracksQuery.data.length > 0 : null, text: 'En az bir araç bulundu',
            hint: 'Araç bulunamadı — "Hassas" modeli deneyin; araç çok küçük/uzaksa bu video yöntem için uygun olmayabilir.' },
        ]}
      >
        {!jobId && (
          <div className="space-y-3">
            <div>
              <div className="mb-1.5 text-xs font-medium text-muted-foreground">Tespit hassasiyeti</div>
              <div className="grid grid-cols-3 gap-2">
                {MODELS.map((m) => (
                  <button key={m.id} type="button" onClick={() => setModel(m.id)}
                    className={`rounded-lg border p-2 text-left text-sm ${model === m.id ? 'border-primary bg-primary/5' : 'hover:bg-accent'}`}>
                    <div className="font-medium">{m.label}</div>
                    <div className="text-[11px] text-muted-foreground">{m.note}</div>
                  </button>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={fpsOn} onChange={(e) => setFpsOn(e.target.checked)} />
              Kare hızını elle gir (video başlığı: {videoMeta.fps.toFixed(3)} fps)
            </label>
            {fpsOn && (
              <div className="flex items-center gap-2">
                <DecimalField ariaLabel="Kare hızı (fps)" value={fps} min={0.001} onChange={setFps} className="w-32" />
                <span className="text-xs text-muted-foreground">
                  Hız doğrudan FPS ile orantılıdır. Yalnızca kaydedicinin gerçek kare hızını biliyorsanız değiştirin.
                </span>
              </div>
            )}
            <Button onClick={() => start.mutate()} disabled={start.isPending}>
              {start.isPending ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              Takibi başlat
            </Button>
            {start.isError && <StatusBanner tone="error">{(start.error as Error).message}</StatusBanner>}
          </div>
        )}
        {running && (
          <div className="space-y-1.5">
            <Progress value={status.data?.progress_pct ?? 0} />
            <p className="text-xs text-muted-foreground">Araçlar takip ediliyor… %{Math.round(status.data?.progress_pct ?? 0)}</p>
          </div>
        )}
        {failed && (
          <StatusBanner tone="error">
            Takip başarısız: {status.data?.error}
            <Button variant="secondary" size="sm" className="ml-2" onClick={() => setJob(null)}>Yeniden dene</Button>
          </StatusBanner>
        )}
        {tracks.length > 0 && (
          <div className="flex items-center justify-between rounded-md border bg-muted/40 px-3 py-2 text-sm">
            <span>{tracks.length} araç takip edildi.</span>
            <Button variant="secondary" size="sm" onClick={() => setJob(null)}>Takibi yeniden yap</Button>
          </div>
        )}
        {done && tracksQuery.data?.length === 0 && (
          <Button variant="secondary" onClick={() => setJob(null)}>Farklı ayarla yeniden dene</Button>
        )}
      </StepGuide>
    </div>
  )
}
