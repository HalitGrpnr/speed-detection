import { useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { measureLine, perpDistance, sub, norm, type Pt } from './geometry'
import { bboxAt, extendLine, frameUrl, useChosenVp, useSelectedTrack, useVideoId, windowPoints } from './hooks'
import { MeasureCanvas, type Shape } from './MeasureCanvas'
import { ContactPointDiagram, DecimalField, FrameScrubber, StepGuide, type Check } from './parts'
import { MODEL_WHEELBASE_SIGMA, SCENE_SIGMA, TYPE_WHEELBASE, useCrossRatio } from './store'

const A_COLOR = '#f472b6'
const B_COLOR = '#22d3ee'
const LINE_COLOR = '#a78bfa'
const OFF_LINE_PX = 4

/** Adım 4 — Bilinen uzunluk: dingil mesafesi (her zaman) veya olay yeri ölçüsü. */
export function KnownLengthStep() {
  const videoId = useVideoId()
  const frameStart = useCrossRatio((s) => s.frameStart)
  const frameEnd = useCrossRatio((s) => s.frameEnd)
  const frame = useCrossRatio((s) => s.currentFrame)
  const setFrame = useCrossRatio((s) => s.setCurrentFrame)
  const L = useCrossRatio((s) => s.length)
  const setL = useCrossRatio((s) => s.setLength)
  const track = useSelectedTrack()
  const { vp, dir, sigma } = useChosenVp()
  const wheelbase = L.kind === 'wheelbase'
  const nameA = wheelbase ? 'Arka teker teması' : '1. işaret'
  const nameB = wheelbase ? 'Ön teker teması' : '2. işaret'

  // Aracın en büyük göründüğü (kameraya en yakın) kare — işaretleme için en hassas yer
  const nearest = useMemo(() => {
    const pts = windowPoints(track, frameStart, frameEnd)
    return pts.reduce<null | { frame: number; h: number }>((best, p) => {
      const h = p.bbox[3] - p.bbox[1]
      return !best || h > best.h ? { frame: p.frame, h } : best
    }, null)?.frame ?? null
  }, [track, frameStart, frameEnd])

  const onClick = (p: Pt) => {
    if (!L.pointA) setL({ pointA: p, frame })
    else if (!L.pointB) setL({ pointB: p })
  }
  const onDrag = (id: string, p: Pt) => setL(id === 'A' ? { pointA: p } : { pointB: p })

  const line = measureLine(vp, dir, [L.pointA, L.pointB].filter(Boolean) as Pt[])
  const shapes: Shape[] = []
  const b = bboxAt(track, frame)
  if (b) shapes.push({ kind: 'box', bbox: b, color: '#22c55e', dash: [5, 4] })
  if (line && L.pointA) {
    const [a, e] = extendLine(line, L.pointA)
    shapes.push({ kind: 'line', a, b: e, color: LINE_COLOR, width: 1.5, dash: [7, 5] })
  }
  if (L.pointA && L.pointB)
    shapes.push({ kind: 'line', a: L.pointA, b: L.pointB, color: '#fff', width: 3, label: `${L.lengthM.toLocaleString('tr-TR', { maximumFractionDigits: 3 })} m` })
  if (L.pointA) shapes.push({ kind: 'point', p: L.pointA, color: A_COLOR, id: 'A', label: nameA })
  if (L.pointB) shapes.push({ kind: 'point', p: L.pointB, color: B_COLOR, id: 'B', label: nameB })
  if (vp) shapes.push({ kind: 'vp', p: vp, color: '#f472b6', label: 'Perspektif referansı', sigmaPx: sigma })

  // Canlı kontrol: iki işaret perspektif referansından geçen aynı doğruda mı?
  const refLine = L.pointA ? measureLine(vp, dir, [L.pointA]) : null
  const offLine = refLine && L.pointB ? perpDistance(L.pointB, refLine) : null
  const sepPx = L.pointA && L.pointB ? norm(sub(L.pointA, L.pointB)) : null
  const checks: Check[] = [
    { ok: L.lengthM > 0 && L.sigmaM >= 0 ? true : false, text: `Uzunluk: ${L.lengthM.toLocaleString('tr-TR', { maximumFractionDigits: 3 })} m ± ${(L.sigmaM * 100).toLocaleString('tr-TR', { maximumFractionDigits: 1 })} cm`,
      hint: 'Pozitif bir uzunluk girin.' },
    { ok: L.pointA && L.pointB ? true : null, text: `${nameA} ve ${nameB} işaretlendi` },
    {
      ok: offLine == null ? null : offLine <= OFF_LINE_PX,
      text: offLine == null ? 'İki işaret aynı perspektif doğrusunda'
        : `İki işaret aynı perspektif doğrusunda (sapma ${offLine.toFixed(1)} px)`,
      hint: wheelbase
        ? 'Ön ve arka tekeri aracın AYNI tarafında, lastiğin yere değdiği noktada işaretleyin.'
        : 'Mesafenin iki ucu aracın tekerleklerinin geçtiği çizgi üzerinde olmalı.',
    },
    {
      ok: sepPx == null ? null : sepPx >= 40,
      text: sepPx == null ? 'İşaretler arası yeterli piksel mesafesi' : `İşaretler arası ${sepPx.toFixed(0)} px`,
      hint: 'İşaretler çok yakın — aracın daha büyük göründüğü (yakın) bir kareye gidin; ölçek hatası büyür.',
    },
  ]
  if (wheelbase && L.wheelbasePreset === 'type')
    checks.push({ ok: false, text: 'Tip varsayılanı kullanılıyor (±15 cm)',
      hint: 'Araç modeli biliniyorsa gerçek dingil mesafesini girin — güven aralığı belirgin daralır.' })

  if (!videoId) return null
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-3">
        <MeasureCanvas imageUrl={frameUrl(videoId, frame)} shapes={shapes} onClick={onClick} onDrag={onDrag} />
        <FrameScrubber value={frame} min={frameStart ?? 0} max={frameEnd ?? 0} onChange={setFrame} />
      </div>
      <div className="space-y-3">
        <StepGuide
          title="4 · Bilinen bir uzunluk verin"
          instruction={wheelbase
            ? <>Aracın <b>dingil mesafesini</b> (ön ve arka teker merkezleri arası) girin. Sonra aracın iyi göründüğü bir
              karede, <b>aynı taraftaki</b> arka ve ön tekerin <b>yere değdiği</b> noktalara sırayla tıklayın.</>
            : <>Yolda gerçek mesafesini bildiğiniz iki noktayı (ör. kesik şerit çizgisi başları, olay yeri ölçüsü)
              işaretleyin ve mesafeyi metre olarak girin. Noktalar <b>aracın tekerlerinin geçtiği çizgi üzerinde</b> olmalı.</>}
          why={<>Perspektif referansı yalnızca oranları verir; ölçeği (kaç piksel = kaç metre) bilinen bir uzunluk sağlar.
            Uzunluğun belirsizliği doğrudan hıza yansır — %1 hata ≈ %1 hız hatası. Bu yüzden belirsizlik (±) de girilir
            ve sonuçtaki güven aralığına katılır.</>}
          checks={checks}
        >
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-muted p-1 text-sm">
            {(['wheelbase', 'scene'] as const).map((k) => (
              <button key={k} type="button"
                onClick={() => setL(k === 'wheelbase'
                  ? { kind: k, wheelbasePreset: 'type', lengthM: TYPE_WHEELBASE.lengthM, sigmaM: TYPE_WHEELBASE.sigmaM, pointA: null, pointB: null }
                  : { kind: k, lengthM: 10, sigmaM: SCENE_SIGMA, pointA: null, pointB: null })}
                className={cn('rounded-md px-2 py-1.5', L.kind === k ? 'bg-card font-medium shadow-card' : 'text-muted-foreground')}>
                {k === 'wheelbase' ? 'Dingil mesafesi' : 'Olay yeri mesafesi'}
              </button>
            ))}
          </div>

          {wheelbase && (
            <div className="space-y-1.5 text-sm">
              <label className="flex items-start gap-2">
                <input type="radio" className="mt-1" checked={L.wheelbasePreset === 'model'}
                  onChange={() => setL({ wheelbasePreset: 'model', sigmaM: MODEL_WHEELBASE_SIGMA })} />
                <span>Araç modeli biliniyor <span className="text-muted-foreground">(teknik belgeden, ±1 cm)</span></span>
              </label>
              <label className="flex items-start gap-2">
                <input type="radio" className="mt-1" checked={L.wheelbasePreset === 'type'}
                  onChange={() => setL({ wheelbasePreset: 'type', ...TYPE_WHEELBASE })} />
                <span>Model bilinmiyor — binek araç tip değeri <span className="text-muted-foreground">(2,65 m ±15 cm)</span></span>
              </label>
            </div>
          )}
          <div className="flex items-end gap-2">
            <label className="flex-1 text-xs text-muted-foreground">Uzunluk (m)
              <DecimalField ariaLabel="Uzunluk (m)" value={L.lengthM} min={0.01}
                onChange={(n) => setL({ lengthM: n, ...(wheelbase && L.wheelbasePreset === 'type' ? { wheelbasePreset: 'model', sigmaM: MODEL_WHEELBASE_SIGMA } : {}) })} />
            </label>
            <label className="w-28 text-xs text-muted-foreground">Belirsizlik ± (m)
              <DecimalField ariaLabel="Belirsizlik (m)" value={L.sigmaM} onChange={(n) => setL({ sigmaM: n })} />
            </label>
          </div>

          {wheelbase && <ContactPointDiagram />}

          <div className="flex flex-wrap gap-2">
            {nearest != null && nearest !== frame && (
              <Button size="sm" variant="secondary" onClick={() => setFrame(nearest)}>Aracın en yakın olduğu kareye git</Button>
            )}
            {(L.pointA || L.pointB) && (
              <Button size="sm" variant="ghost" onClick={() => setL({ pointA: null, pointB: null, frame: null })}>İşaretleri temizle</Button>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {!L.pointA ? `Sıradaki tıklama: ${nameA}` : !L.pointB ? `Sıradaki tıklama: ${nameB}` : 'İnce ayar için noktaları sürükleyin.'}
          </p>
        </StepGuide>
      </div>
    </div>
  )
}
