import { useMemo } from 'react'
import type { TrackSummary } from '@/lib/models'
import { useWizard } from '@/store/wizard'
import { measureLine, type MeasureLine, type Pt } from './geometry'
import { usableVp, useCrossRatio } from './store'

export const frameUrl = (videoId: string, n: number) => `/api/video/${videoId}/frame/${n}`

export function useVideoId(): string | null {
  return useWizard((s) => s.videoMeta?.video_id ?? null)
}

export function useSelectedTrack(): TrackSummary | null {
  const tracks = useCrossRatio((s) => s.tracks)
  const id = useCrossRatio((s) => s.trackId)
  return useMemo(() => tracks.find((t) => t.track_id === id) ?? null, [tracks, id])
}

/** Karedeki bbox (tam eşleşme yoksa ±3 kare içindeki en yakın). */
export function bboxAt(track: TrackSummary | null, frame: number): readonly number[] | null {
  if (!track) return null
  let best: TrackSummary['points'][number] | null = null
  for (const p of track.points) {
    if (!best || Math.abs(p.frame - frame) < Math.abs(best.frame - frame)) best = p
  }
  return best && Math.abs(best.frame - frame) <= 3 ? best.bbox : null
}

export function windowPoints(track: TrackSummary | null, start: number | null, end: number | null) {
  if (!track || start == null || end == null) return []
  return track.points.filter((p) => p.frame >= start && p.frame <= end)
}

/** Seçilen perspektif referansı: (nokta | null, sonsuz yön | null, kaynak). */
export function useChosenVp(): { vp: Pt | null; dir: Pt | null; source: string | null; sigma: number | null } {
  const preview = useCrossRatio((s) => s.vpPreview)
  const primary = useCrossRatio((s) => s.vpPrimary)
  return useMemo(() => {
    const v = usableVp(preview, primary)
    if (!v) return { vp: null, dir: null, source: null, sigma: null }
    return {
      vp: (v.point as Pt | null) ?? null,
      dir: (v.direction as Pt | null) ?? null,
      source: v.source,
      sigma: v.sigma_major_px ?? null,
    }
  }, [preview, primary])
}

/** Referans işaretlerinden (yoksa temas işaretlerinden) ölçüm doğrusu. */
export function useMeasureLine(): MeasureLine | null {
  const { vp, dir } = useChosenVp()
  const length = useCrossRatio((s) => s.length)
  const marks = useCrossRatio((s) => s.marks)
  return useMemo(() => {
    const refs = [length.pointA, length.pointB].filter(Boolean) as Pt[]
    const pts = refs.length ? refs : Object.values(marks).map((m) => m.pixel)
    return measureLine(vp, dir, pts)
  }, [vp, dir, length.pointA, length.pointB, marks])
}

/** Ölçüm doğrusunu görüntüyü kesecek kadar uzatılmış iki uç olarak döndür. */
export function extendLine(line: MeasureLine, through: Pt, span = 4000): [Pt, Pt] {
  const a: Pt = [through[0] - line.dir[0] * span, through[1] - line.dir[1] * span]
  const b: Pt = [through[0] + line.dir[0] * span, through[1] + line.dir[1] * span]
  return line.finiteVp ? [line.origin, b] : [a, b]
}

export const CLASS_TR: Record<string, string> = {
  car: 'Otomobil', truck: 'Kamyon', bus: 'Otobüs', motorcycle: 'Motosiklet',
}
