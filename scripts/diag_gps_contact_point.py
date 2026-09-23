"""GPS testi geriye-doğru teşhis: videoyu gerçek tracker'dan geçir,
Track'lerin bbox'larını H ile dünyaya çevir, plato bölgesindeki hız
davranışını farklı temas-noktası seçenekleriyle karşılaştır."""
import json
import numpy as np
import cv2
from src.detection.tracker import VehicleTracker

# --- GPS-test kalibrasyon noktaları (session f11938f5) ---
PX = np.array([[308.5,351.6],[370.6,388.4],[463.4,444.1],[583.1,519.7],[748.4,623.7],
               [362.9,260.0],[432.3,283.9],[534.6,323.4],[665.9,380.4],[840.9,467.6]], np.float64)
WORLD = np.array([[0,0],[0,2.65],[0,5.3],[0,7.95],[0,10.6],
                  [3.5,0],[3.5,2.65],[3.5,5.3],[3.5,7.95],[3.5,10.6]], np.float64)
H, _ = cv2.findHomography(PX, WORLD, method=0)  # tüm noktalar (LS)
FPS = 25.0

def p2w(x, y):
    v = H @ np.array([x, y, 1.0])
    return v[0]/v[2], v[1]/v[2]

print("Video işleniyor (yolo11m)...")
tr = VehicleTracker(model_name="yolo11m.pt")
tracks, meta = tr.process_video("docs/82_kmh.mp4", frame_step=1, progress=False)
print(f"  {len(tracks)} track, {meta.width}x{meta.height} @ {meta.fps} fps, {meta.frame_count} kare\n")

# Kalibrasyon bbox'ı (piksel) — plato bölgesi bu aralık
cal_py_min, cal_py_max = PX[:,1].min(), PX[:,1].max()  # 260..624
print(f"Kalibrasyon piksel-Y aralığı: {cal_py_min:.0f}..{cal_py_max:.0f}\n")

def speed_series(track, frac):
    """frac: temas noktası = y1 + (y2-y1)*frac (1.0 = bbox bottom)."""
    pts = []
    for p in track.points:
        x1,y1,x2,y2 = p.bbox
        cx = (x1+x2)/2
        cy = y1 + (y2-y1)*frac
        wx, wy = p2w(cx, cy)
        pts.append((p.frame, cx, cy, wx, wy))
    sp = []
    for i in range(1, len(pts)):
        f0,_,_,x0,y0 = pts[i-1]
        f1,cx,cy,x1w,y1w = pts[i]
        dt = (f1-f0)/FPS
        d = np.hypot(x1w-x0, y1w-y0)
        sp.append((f1, cx, cy, x1w, y1w, d/dt*3.6))
    return pts, sp

# En hızlı / en çok kare gören track'i bul (hedef araç)
cand = [t for t in tracks if len(t.points) >= 10]
print(f"{len(cand)} aday track (>=10 kare)")
for t in sorted(cand, key=lambda x: x.track_id):
    _, sp = speed_series(t, 1.0)
    v = np.array([s[5] for s in sp])
    pyrange = (min(p.bbox[3] for p in t.points), max(p.bbox[3] for p in t.points))
    print(f"  Track {t.track_id}: {len(t.points)} kare, hız med={np.median(v):.1f} max={v.max():.1f} "
          f"bbox-y2 {pyrange[0]:.0f}..{pyrange[1]:.0f}")

# Hedef: max hız en yüksek olan
target = max(cand, key=lambda t: np.max([s[5] for s in speed_series(t,1.0)[1]]))
print(f"\n=== HEDEF Track {target.track_id} ({target.vehicle_class}) ===")

for frac, label in [(1.0,"bbox_bottom(y2)"), (0.90,"y1+0.90*(y2-y1)"), (0.95,"0.95")]:
    pts, sp = speed_series(target, frac)
    # plato = temas piksel-Y kalibrasyon aralığında olan kareler
    inzone = [s for s in sp if cal_py_min <= s[2] <= cal_py_max]
    v_all = np.array([s[5] for s in sp])
    v_in = np.array([s[5] for s in inzone])
    print(f"\n-- temas={label} --")
    print(f"   tüm kareler: med={np.median(v_all):.1f}  max={v_all.max():.1f}")
    if len(v_in):
        print(f"   KALİBRASYON İÇİ ({len(v_in)} kare): med={np.median(v_in):.1f} "
              f"ort={v_in.mean():.1f} min={v_in.min():.1f} max={v_in.max():.1f}")

# Detay: hedef track'in bbox yüksekliği ve dünya yolu (frac=1.0)
print("\n=== HEDEF track kare-kare (bbox_bottom) ===")
pts, sp = speed_series(target, 1.0)
print("frame  cx    y2   bbox_h  worldX worldY  v_kmh  in_zone")
for s in sp:
    f,cx,cy,wx,wy,v = s
    bp = next(p for p in target.points if p.frame==f)
    bh = bp.bbox[3]-bp.bbox[1]
    inz = "*" if cal_py_min<=cy<=cal_py_max else ""
    print(f"{f:4d} {cx:6.0f} {cy:5.0f} {bh:6.0f} {wx:6.2f} {wy:6.2f} {v:6.1f}  {inz}")
