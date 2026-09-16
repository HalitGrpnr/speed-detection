/**
 * Tip-güvenli API istemcisi. Tüm istekler aynı-origin /api'ye gider (dev'de Vite
 * proxy uvicorn'a yönlendirir). Hiçbir harici servise çağrı yok (forensic, yerel).
 */
import type {
  AutoCalibrateRequest,
  AutoCalibrateResponse,
  AutoContactPointsResponse,
  AxleCheckRequest,
  AxleCheckResponse,
  AxleSuggestFrameResponse,
  CalibrateRequest,
  CalibrateResponse,
  InterpolatePointRequest,
  InterpolatePointResponse,
  JobResult,
  JobStatus,
  PipelineRequest,
  PlanViewRequest,
  RecalibrateRequest,
  VideoMeta,
  WheelSpeedRequest,
  WheelSpeedResponse,
  WheelSpeedProfileRequest,
  WheelSpeedProfileResponse,
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

  /** Oturum logu — her adım, parametre ve sonuç. */
  async sessionLog(jobId: string): Promise<Record<string, unknown>[]> {
    return unwrap(await fetch(`/api/job/${jobId}/session-log`))
  },

  /** T16 — Operatör-tekerlek hız ölçümü: işaretlerden birincil hızı hesapla. */
  async wheelSpeed(jobId: string, trackId: number, req: WheelSpeedRequest): Promise<WheelSpeedResponse> {
    return unwrap(
      await fetch(`/api/job/${jobId}/track/${trackId}/wheel-speed`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** T19 — Çok-işaretli hız profili (fren/ivme analizi). */
  async wheelSpeedProfile(jobId: string, trackId: number, req: WheelSpeedProfileRequest): Promise<WheelSpeedProfileResponse> {
    return unwrap(
      await fetch(`/api/job/${jobId}/track/${trackId}/wheel-speed-profile`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** T19 — Profil overlay videosu oluştur (uzun sürebilir). */
  async generateProfileOverlay(jobId: string, trackId: number, req: WheelSpeedProfileRequest): Promise<{ overlay_path: string; download_url: string }> {
    return unwrap(
      await fetch(`/api/job/${jobId}/track/${trackId}/wheel-speed-profile-overlay`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** T19 — Profil hız-zaman grafiği (PNG URL). */
  profileChartUrl: (jobId: string, trackId: number) =>
    `/api/job/${jobId}/track/${trackId}/wheel-profile-chart` as const,

  /** T19 — Profil overlay videosu indirme URL'i. */
  profileOverlayUrl: (jobId: string, trackId: number) =>
    `/api/job/${jobId}/track/${trackId}/wheel-profile-overlay` as const,

  /** T14 — Alt-kare enterpolasyon: bracketing iki karedeki teker konumundan ara nokta hesaplar. */
  async interpolatePoint(videoId: string, req: InterpolatePointRequest): Promise<InterpolatePointResponse> {
    return unwrap(
      await fetch(`/api/video/${videoId}/interpolate-point`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** T22 — Vanishing-point tabanlı otomatik kalibrasyon önerisi. */
  async autoCalibrate(videoId: string, req: AutoCalibrateRequest): Promise<AutoCalibrateResponse> {
    return unwrap(
      await fetch(`/api/video/${videoId}/auto-calibrate`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(req),
      }),
    )
  },

  /** T20 — Otomatik temas noktası tahminleri (klasik CV + bbox yedek). */
  async autoContactPoints(
    jobId: string,
    trackId: number,
    maxMarks: number = 8,
  ): Promise<AutoContactPointsResponse> {
    return unwrap(
      await fetch(
        `/api/job/${jobId}/track/${trackId}/auto-contact-points?max_marks=${maxMarks}`,
      ),
    )
  },
}
