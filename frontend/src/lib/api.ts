/**
 * Tip-güvenli API istemcisi. Tüm istekler aynı-origin /api'ye gider (dev'de Vite
 * proxy uvicorn'a yönlendirir). Hiçbir harici servise çağrı yok (forensic, yerel).
 */
import type {
  AutoRefRequest,
  AxleCheckRequest,
  AxleCheckResponse,
  AxleSuggestFrameResponse,
  AxleStepRequest,
  AxleStepResponse,
  CalibrateRequest,
  CalibrateResponse,
  JobResult,
  JobStatus,
  PipelineRequest,
  PlanViewRequest,
  ProposedPoint,
  RecalibrateRequest,
  SpeedSeriesOut,
  VideoMeta,
} from '@/lib/models'

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* gövde JSON değil — statusText kullan */
    }
    throw new Error(detail || `İstek başarısız (${res.status})`)
  }
  return (await res.json()) as T
}

async function unwrapBlob(res: Response): Promise<Blob> {
  if (!res.ok) {
    let detail: string = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* gövde JSON değil — statusText kullan */
    }
    throw new Error(detail || `İstek başarısız (${res.status})`)
  }
  return await res.blob()
}

const jsonHeaders = { 'Content-Type': 'application/json' }

export const api = {
  /** Video yükler. onProgress 0–100 arası yükleme yüzdesini bildirir (büyük adli dosyalar için). */
  uploadVideo(file: File, onProgress?: (pct: number) => void): Promise<VideoMeta> {
    return new Promise<VideoMeta>((resolve, reject) => {
      const fd = new FormData()
      fd.append('file', file)
      const xhr = new XMLHttpRequest()
      xhr.open('POST', '/api/video/upload')
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as VideoMeta)
          } catch {
            reject(new Error('Sunucu yanıtı çözümlenemedi'))
          }
          return
        }
        let detail = `Yükleme başarısız (${xhr.status})`
        if (xhr.status === 413) {
          detail = 'Dosya çok büyük (maksimum 10 GB).'
        } else {
          try {
            const b = JSON.parse(xhr.responseText) as { detail?: unknown }
            if (typeof b.detail === 'string') detail = b.detail
          } catch {
            /* gövde JSON değil */
          }
        }
        reject(new Error(detail))
      }
      xhr.onerror = () => reject(new Error('Ağ hatası — yükleme tamamlanamadı'))
      xhr.send(fd)
    })
  },

  frameUrl: (videoId: string, frame: number) => `/api/video/${videoId}/frame/${frame}`,

  async calibrate(req: CalibrateRequest): Promise<CalibrateResponse> {
    return unwrap(
      await fetch('/api/calibrate', {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  async autoref(videoId: string, req: AutoRefRequest): Promise<ProposedPoint[]> {
    return unwrap(
      await fetch(`/api/video/${videoId}/autoref`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  async startPipeline(req: PipelineRequest): Promise<{ job_id: string }> {
    return unwrap(
      await fetch('/api/pipeline', {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  async jobStatus(jobId: string): Promise<JobStatus> {
    return unwrap(await fetch(`/api/job/${jobId}/status`))
  },

  async jobResults(jobId: string): Promise<JobResult> {
    return unwrap(await fetch(`/api/job/${jobId}/results`))
  },

  reportUrl: (jobId: string) => `/api/job/${jobId}/report`,
  overlayUrl: (jobId: string) => `/api/job/${jobId}/overlay`,
  overlayDownloadUrl: (jobId: string) => `/api/job/${jobId}/overlay/download`,

  async axleSuggestFrame(jobId: string, trackId: number): Promise<AxleSuggestFrameResponse> {
    return unwrap(await fetch(`/api/job/${jobId}/track/${trackId}/axle-suggest-frame`))
  },

  async axleCheck(jobId: string, trackId: number, req: AxleCheckRequest): Promise<AxleCheckResponse> {
    return unwrap(
      await fetch(`/api/job/${jobId}/track/${trackId}/axle-check`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** Kuş bakışı (kalibre edilmiş yol düzleminin projeksiyonu) — PNG blob döner. */
  async planView(videoId: string, req: PlanViewRequest): Promise<Blob> {
    return unwrapBlob(
      await fetch(`/api/video/${videoId}/plan-view`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  jobPlanViewUrl: (jobId: string) => `/api/job/${jobId}/plan-view`,

  /** Aks doğrulamasını kalibrasyona ekleyip yeni bir job olarak yeniden analiz başlatır. */
  async recalibrate(jobId: string, req: RecalibrateRequest): Promise<{ job_id: string }> {
    return unwrap(
      await fetch(`/api/job/${jobId}/recalibrate`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** Aks doğrulaması dahil güncellenmiş PDF raporu üretir. */
  async regenerateReport(jobId: string): Promise<{ status: string; axle_check_count: number }> {
    return unwrap(
      await fetch(`/api/job/${jobId}/report/regenerate`, { method: 'POST' }),
    )
  },

  /** Güncellenmiş raporu indirme URL'i. */
  reportV2Url: (jobId: string) => `/api/job/${jobId}/report/v2`,

  /** Dingil adımlama hız tahmini (T8). */
  async axleStep(jobId: string, trackId: number, req: AxleStepRequest): Promise<AxleStepResponse> {
    return unwrap(
      await fetch(`/api/job/${jobId}/track/${trackId}/axle-step`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** Track hız zaman serisi (T13 sparkline). result_data.json yoksa hata fırlatır. */
  async speedSeries(jobId: string, trackId: number): Promise<SpeedSeriesOut> {
    return unwrap(await fetch(`/api/job/${jobId}/track/${trackId}/speed-series`))
  },
}
