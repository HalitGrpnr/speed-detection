/**
 * Canlı doğrulama için istemci-tarafı geometri (T28).
 * Nihai sayı her zaman sunucudan gelir; burası yalnızca operatöre tıkladığı anda
 * "bu işaret iyi mi?" geri bildirimi verir. Formüller `src/speed/cross_ratio.py` ile aynıdır.
 */
export type Pt = [number, number]

export const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]]
export const dot = (a: Pt, b: Pt) => a[0] * b[0] + a[1] * b[1]
export const norm = (a: Pt) => Math.hypot(a[0], a[1])
export const unit = (a: Pt): Pt => {
  const n = norm(a) || 1
  return [a[0] / n, a[1] / n]
}

/** Ölçüm doğrusu: VP'den referans noktalarına (yoksa verilen noktalara) doğru. */
export interface MeasureLine {
  origin: Pt   // VP (sonlu) veya p1
  dir: Pt      // birim
  finiteVp: boolean
}

export function measureLine(vp: Pt | null, vpDir: Pt | null, refs: Pt[]): MeasureLine | null {
  if (refs.length === 0) return null
  const mean: Pt = [
    refs.reduce((s, p) => s + p[0], 0) / refs.length,
    refs.reduce((s, p) => s + p[1], 0) / refs.length,
  ]
  if (vp) return { origin: vp, dir: unit(sub(mean, vp)), finiteVp: true }
  if (vpDir) return { origin: refs[0], dir: unit(vpDir), finiteVp: false }
  return null
}

export function perpDistance(p: Pt, line: MeasureLine): number {
  const r = sub(p, line.origin)
  return Math.abs(r[0] * line.dir[1] - r[1] * line.dir[0])
}

/** 1 px işaret hatasının metre karşılığı (uzak kare = büyük). */
export function sensitivityMPerPx(line: MeasureLine, a: Pt, b: Pt, lengthM: number, p: Pt): number | null {
  const c1 = dot(sub(a, line.origin), line.dir)
  const c2 = dot(sub(b, line.origin), line.dir)
  if (Math.abs(c1 - c2) < 1e-6) return null
  if (!line.finiteVp) return Math.abs(lengthM / (c2 - c1))
  const c = dot(sub(p, line.origin), line.dir)
  if (c <= 0) return null
  return Math.abs((lengthM * c1 * c2) / ((c1 - c2) * c * c))
}

/** Noktalara toplam-EKK doğru uydur; dik RMS sapma (px). Düz-gidiş ipucu için. */
export function lineFitRms(points: Pt[]): number | null {
  const n = points.length
  if (n < 3) return null
  const mx = points.reduce((s, p) => s + p[0], 0) / n
  const my = points.reduce((s, p) => s + p[1], 0) / n
  let sxx = 0, syy = 0, sxy = 0
  for (const [x, y] of points) {
    sxx += (x - mx) ** 2
    syy += (y - my) ** 2
    sxy += (x - mx) * (y - my)
  }
  const theta = 0.5 * Math.atan2(2 * sxy, sxx - syy)
  const d: Pt = [Math.cos(theta), Math.sin(theta)]
  const ss = points.reduce((s, p) => {
    const r = sub(p, [mx, my])
    return s + (r[0] * d[1] - r[1] * d[0]) ** 2
  }, 0)
  return Math.sqrt(ss / (n - 2))
}

/** Görüntü dışındaki noktaya giden ışının görüntü kenarıyla kesişimi (ekran dışı VP oku). */
export function edgePointToward(target: Pt, w: number, h: number, margin = 18): Pt {
  const c: Pt = [w / 2, h / 2]
  const d = sub(target, c)
  const tx = d[0] === 0 ? Infinity : ((d[0] > 0 ? w - margin : margin) - c[0]) / d[0]
  const ty = d[1] === 0 ? Infinity : ((d[1] > 0 ? h - margin : margin) - c[1]) / d[1]
  const t = Math.min(Math.abs(tx), Math.abs(ty))
  return [c[0] + d[0] * t, c[1] + d[1] * t]
}

export const bboxBottomCenter = (b: readonly number[]): Pt => [(b[0] + b[2]) / 2, b[3]]

/** Zaman sırasına dizilmiş işaretlerin ölçüm doğrusu boyunca tek yönde ilerleyip ilerlemediği.
 * Döner: geri giden karelerin listesi (boşsa sorun yok). tolPx: işaretleme gürültüsü payı. */
export function nonMonotonicFrames(line: MeasureLine, marks: { f: number; p: Pt }[], tolPx = 2): number[] {
  const seq = [...marks].sort((a, b) => a.f - b.f).map((m) => ({ f: m.f, c: dot(sub(m.p, line.origin), line.dir) }))
  if (seq.length < 3) return []
  const total = seq[seq.length - 1].c - seq[0].c
  const dirSign = Math.sign(total) || 1
  const bad: number[] = []
  for (let i = 1; i < seq.length; i++) {
    if ((seq[i].c - seq[i - 1].c) * dirSign < -tolPx) bad.push(seq[i].f)
  }
  return bad
}
