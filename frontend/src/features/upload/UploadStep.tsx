import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Check, Copy, FileVideo, Loader2, UploadCloud } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { VideoMeta } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { StatusBanner } from '@/components/common/StatusBanner'
import { StepFooter } from '@/components/common/StepFooter'

const FPS_SOURCE_TR: Record<string, string> = {
  container: 'konteynerden',
  operator_override: 'operatör girişi',
}

function formatDuration(frames: number, fps: number): string {
  if (!fps) return '—'
  const total = Math.round(frames / fps)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function UploadStep() {
  const videoMeta = useWizard((s) => s.videoMeta)
  const setVideoMeta = useWizard((s) => s.setVideoMeta)
  const setControlPoints = useWizard((s) => s.setControlPoints)
  const setCalibration = useWizard((s) => s.setCalibration)
  const setJobId = useWizard((s) => s.setJobId)

  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (file: File) => {
      setProgress(0)
      return api.uploadVideo(file, setProgress)
    },
    onSuccess: (meta: VideoMeta) => {
      // Yeni video → eski kalibrasyon/iş durumunu temizle
      setControlPoints([])
      setCalibration(null)
      setJobId(null)
      setVideoMeta(meta)
    },
  })

  function handleFile(file: File | undefined | null) {
    if (!file) return
    setFileName(file.name)
    mutation.mutate(file)
  }

  const uploading = mutation.isPending

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adım 1 — Video Yükle</CardTitle>
        <CardDescription>
          Trafik kazası videosunu yükleyin. Bütünlük için SHA-256 hesaplanır; orijinal dosyaya
          asla yazılmaz, tüm işleme yereldir.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        {mutation.isError && (
          <StatusBanner tone="error">{(mutation.error as Error).message}</StatusBanner>
        )}

        {uploading ? (
          <div className="space-y-3 rounded-xl border bg-muted/30 p-6">
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span className="font-medium">Yükleniyor…</span>
              <span className="truncate text-muted-foreground">{fileName}</span>
              <span className="ml-auto tabular-nums text-muted-foreground">{progress}%</span>
            </div>
            <Progress value={progress} />
          </div>
        ) : videoMeta ? (
          <div className="space-y-4">
            <StatusBanner tone="success">
              Video yüklendi ve doğrulandı. Aşağıdaki bilgileri kontrol edip devam edin.
            </StatusBanner>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Meta label="Çözünürlük" value={`${videoMeta.width}×${videoMeta.height}`} />
              <Meta
                label="FPS"
                value={`${videoMeta.fps.toFixed(2)}`}
                hint={FPS_SOURCE_TR[videoMeta.fps_source] ?? videoMeta.fps_source}
              />
              <Meta label="Kare sayısı" value={videoMeta.frame_count.toLocaleString('tr-TR')} />
              <Meta label="Süre" value={formatDuration(videoMeta.frame_count, videoMeta.fps)} />
            </div>

            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                SHA-256 (orijinal dosya bütünlüğü — adli iz)
              </p>
              <ShaChip sha={videoMeta.sha256} />
            </div>

            <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
              <FileVideo /> Farklı video yükle
            </Button>
          </div>
        ) : (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              handleFile(e.dataTransfer.files?.[0])
            }}
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 text-center transition-colors',
              dragOver
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50 hover:bg-accent/40',
            )}
          >
            <UploadCloud className="size-10 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Tıklayın veya videoyu sürükleyip bırakın</p>
              <p className="mt-1 text-xs text-muted-foreground">MP4, AVI, MKV, MOV · maksimum 10 GB</p>
            </div>
          </div>
        )}

        <StepFooter />
      </CardContent>
    </Card>
  )
}

function Meta({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-[0.7rem] text-muted-foreground">{hint}</p>}
    </div>
  )
}

function ShaChip({ sha }: { sha: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(sha)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        } catch {
          /* pano erişimi yoksa sessiz geç */
        }
      }}
      className="flex w-full items-center gap-2 rounded-md bg-muted px-3 py-2 text-left font-mono text-xs text-muted-foreground transition-colors hover:bg-muted/70"
      title="Kopyalamak için tıklayın"
    >
      <span className="break-all">{sha}</span>
      {copied ? (
        <Check className="ml-auto size-4 shrink-0 text-emerald-600" />
      ) : (
        <Copy className="ml-auto size-4 shrink-0" />
      )}
    </button>
  )
}
