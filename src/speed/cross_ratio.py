"""T28 — Cross-ratio hız yöntemi (H-bağımsız, tek doğru boyunca 1B projektif ölçüm).

Yöntem:
  Araç yol düzleminde düz bir doğru boyunca gider. Bu doğrunun görüntüsü kaçış noktasından (VP)
  geçer. Doğru üzerindeki bir görüntü noktasının VP'ye piksel uzaklığı r ise, gerçek konum X
  ile 1/r arasındaki ilişki affine'dir (cross-ratio'nun kapalı hali):

      X(r) = L · r2 · (r1 − r) / ((r1 − r2) · r)

  p1, p2: gerçek arası L metre olan iki referans noktası (ör. aynı taraftaki ön/arka tekerlek
  teması → dingil mesafesi). X(p1)=0, X(p2)=L. Her karedeki tekerlek temas noktası bu haritadan
  geçirilir; konum–zaman doğrusuna (ağırlıklı) fit edilir → eğim = hız.

  VP sonsuza giderken (doğru görüntü düzlemine paralel) r1, r2, r → ∞ ve formül düz orana iner:
      X(s) = L · (s − s1) / (s2 − s1)
  Bu durum `vp=None` ile açıkça da seçilebilir.

Kapsam notu: tüm noktalar AYNI görüntü doğrusu üzerinde varsayılır. Doğru dışındaki noktalar
doğruya dik (görüntüde) izdüşürülür ve sapmaları `offsets_px` olarak raporlanır — kalite kapısı.

Saf NumPy/SciPy; homografi veya eski hız modüllerine bağımlılığı yoktur.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Sequence

import numpy as np
from scipy import stats

Point = Sequence[float]

# Kalite eşikleri (T10 GPS doğrulama setine kadar geçici)
_MAX_OFFSET_PX = 4.0          # doğrudan dik sapma — "düz gitmiyor / doğru dışında" uyarısı
_HIGH_REL_CI = 0.05           # CI/hız ≤ %5 → yüksek
_MEDIUM_REL_CI = 0.15         # CI/hız ≤ %15 → orta


def _as_points(points: Sequence[Point] | np.ndarray) -> np.ndarray:
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("Noktalar (N, 2) biçiminde olmalıdır.")
    return arr


def fit_line_direction(points: Sequence[Point] | np.ndarray, vp: Point | None) -> np.ndarray:
    """Ölçüm doğrusunun birim yön vektörü.

    vp verilirse doğru VP'den geçmeye zorlanır (merkezlemesiz SVD) ve yön VP'den noktalara
    doğru bakar. vp=None ise noktaların ana ekseni (PCA) kullanılır.
    """
    pts = _as_points(points)
    if vp is None:
        if len(pts) < 2:
            raise ValueError("VP yokken yön için en az 2 nokta gerekir.")
        centered = pts - pts.mean(axis=0)
    else:
        if len(pts) < 1:
            raise ValueError("Yön için en az 1 nokta gerekir.")
        centered = pts - np.asarray(vp, dtype=np.float64)
    _, sing, vt = np.linalg.svd(centered, full_matrices=False)
    if sing[0] < 1e-9:
        raise ValueError("Noktalar çakışık — doğru yönü belirlenemiyor.")
    d = vt[0]
    if vp is not None and float(np.mean(centered @ d)) < 0:
        d = -d
    return d / np.linalg.norm(d)


@dataclass(frozen=True)
class LineScale:
    """Tek görüntü doğrusu için piksel → metre (doğru boyunca konum) haritası."""

    vp: tuple[float, float] | None
    origin: tuple[float, float]        # vp varsa vp; yoksa p1'in izdüşümü
    direction: tuple[float, float]     # birim yön
    c1: float                          # p1'in doğru koordinatı (r1 veya s1)
    c2: float                          # p2'nin doğru koordinatı (r2 veya s2)
    length_m: float
    ref_offsets_px: tuple[float, float]

    def _coords(self, points: np.ndarray) -> np.ndarray:
        return (points - np.asarray(self.origin)) @ np.asarray(self.direction)

    def offsets_px(self, points: Sequence[Point] | np.ndarray) -> np.ndarray:
        """Noktaların ölçüm doğrusuna görüntüde dik uzaklığı (px)."""
        pts = _as_points(points)
        d = np.asarray(self.direction)
        rel = pts - np.asarray(self.origin)
        return np.abs(rel[:, 0] * d[1] - rel[:, 1] * d[0])

    def position_m(self, points: Sequence[Point] | np.ndarray) -> np.ndarray:
        """Doğru boyunca gerçek konum (m); p1'de 0, p2 yönünde pozitif."""
        c = self._coords(_as_points(points))
        L, c1, c2 = self.length_m, self.c1, self.c2
        if self.vp is None:
            return L * (c - c1) / (c2 - c1)
        return L * c2 * (c1 - c) / ((c1 - c2) * c)

    def position_sensitivity_m_per_px(self, points: Sequence[Point] | np.ndarray) -> np.ndarray:
        """|dX/dpx| — 1 px işaretleme hatasının metre karşılığı (uzak = büyük)."""
        c = self._coords(_as_points(points))
        L, c1, c2 = self.length_m, self.c1, self.c2
        if self.vp is None:
            return np.full_like(c, abs(L / (c2 - c1)))
        return np.abs(L * c1 * c2 / ((c1 - c2) * c * c))


def line_scale_from_vp(
    vp: Point | None,
    ref_a: Point,
    ref_b: Point,
    length_m: float,
    line_points: Sequence[Point] | np.ndarray | None = None,
) -> LineScale:
    """VP + bilinen uzunluktan 1B ölçek haritası kur.

    vp: kaçış noktası (px) — None ise doğru görüntü düzlemine paralel kabul edilir.
    ref_a, ref_b: gerçek arası `length_m` olan iki nokta (p1, p2).
    line_points: doğrunun yönünü belirlemek için ek noktalar (ör. tekerlek izi). Verilmezse
        yön yalnızca referans noktalarından (ve vp'den) çıkarılır.
    """
    if not (length_m > 0):
        raise ValueError("Bilinen uzunluk pozitif olmalıdır.")
    refs = _as_points([ref_a, ref_b])
    dir_pts = refs if line_points is None else np.vstack([refs, _as_points(line_points)])
    d = fit_line_direction(dir_pts, vp)

    if vp is None:
        origin = refs[0]
    else:
        origin = np.asarray(vp, dtype=np.float64)
    coords = (refs - origin) @ d
    c1, c2 = float(coords[0]), float(coords[1])

    if abs(c1 - c2) < 1e-6:
        raise ValueError("Referans noktaları doğru üzerinde çakışıyor — uzunluk ölçeklenemez.")
    if vp is not None and (c1 <= 0 or c2 <= 0):
        raise ValueError("Referans noktası kaçış noktasının ötesinde — VP veya noktalar hatalı.")

    scale = LineScale(
        vp=None if vp is None else (float(vp[0]), float(vp[1])),
        origin=(float(origin[0]), float(origin[1])),
        direction=(float(d[0]), float(d[1])),
        c1=c1,
        c2=c2,
        length_m=float(length_m),
        ref_offsets_px=(0.0, 0.0),
    )
    offs = scale.offsets_px(refs)
    return replace(scale, ref_offsets_px=(float(offs[0]), float(offs[1])))


@dataclass
class CrossRatioSpeedResult:
    speed_kmh: float
    ci_kmh: float                      # ~%95 güven aralığı yarı-genişliği
    confidence_level: str              # "high" | "medium" | "low"
    n_points: int
    direction: str                     # "toward_ref_b" | "toward_ref_a" (p1→p2 yönüne göre)
    positions_m: list[float]           # audit izi
    times_s: list[float]
    residual_rms_m: float
    max_offset_px: float
    method: str = "cross_ratio"
    warnings: list[str] = field(default_factory=list)


def cross_ratio_speed(
    scale: LineScale,
    frames: Sequence[float],
    points: Sequence[Point] | np.ndarray,
    fps: float,
    pixel_sigma: float = 1.0,
    length_sigma_m: float = 0.0,
) -> CrossRatioSpeedResult:
    """Karelerdeki temas noktalarından doğru boyunca hız.

    frames: her noktanın kare numarası (kesirli olabilir).
    points: her karede tekerlek-zemin temas noktası (px).
    pixel_sigma: işaretleme belirsizliği (px, 1σ) — konum ağırlıkları ve CI tabanı.
    length_sigma_m: bilinen uzunluğun belirsizliği (m, 1σ) — hıza oransal yayılır.

    CI: ağırlıklı doğrusal fit eğiminin standart hatası; gözlenen dağılım piksel varsayımından
    büyükse o kullanılır (max(χ²_red, 1)). Uzunluk belirsizliği karesel toplanır. Kaçış noktası
    belirsizliği bu fonksiyonun kapsamı dışındadır (çağıran taraf ekler).
    """
    if fps <= 0:
        raise ValueError("FPS pozitif olmalıdır.")
    if pixel_sigma <= 0:
        raise ValueError("pixel_sigma pozitif olmalıdır.")
    pts = _as_points(points)
    t = np.asarray(frames, dtype=np.float64) / fps
    n = len(pts)
    if n != len(t):
        raise ValueError("Kare ve nokta sayıları eşit olmalıdır.")
    if n < 2:
        raise ValueError("Hız için en az 2 işaretli kare gerekir.")
    if np.ptp(t) <= 0:
        raise ValueError("İşaretler farklı karelerde olmalıdır.")

    warnings: list[str] = []

    if scale.vp is not None:
        c = scale._coords(pts)
        if np.any(c <= 0):
            raise ValueError("Bir temas noktası kaçış noktasının ötesinde — VP veya işaret hatalı.")

    offsets = scale.offsets_px(pts)
    max_offset = float(max(offsets.max(), *scale.ref_offsets_px))
    if max_offset > _MAX_OFFSET_PX:
        warnings.append(
            f"Bazı noktalar ölçüm doğrusundan {max_offset:.1f} px sapıyor — araç bu aralıkta düz "
            "gitmiyor olabilir veya işaretler farklı tekerlek/şeritte. Daha düz bir bölüm seçin."
        )

    x = scale.position_m(pts)
    sigma_x = scale.position_sensitivity_m_per_px(pts) * pixel_sigma
    w = 1.0 / sigma_x**2

    # Ağırlıklı doğrusal regresyon: x = a + b·t
    tw = float(np.sum(w * t) / np.sum(w))
    xw = float(np.sum(w * x) / np.sum(w))
    sxx = float(np.sum(w * (t - tw) ** 2))
    slope = float(np.sum(w * (t - tw) * (x - xw)) / sxx)
    resid = x - (xw + slope * (t - tw))
    residual_rms = float(np.sqrt(np.mean(resid**2)))

    if n >= 3:
        chi2_red = float(np.sum(w * resid**2) / (n - 2))
        q = float(stats.t.ppf(0.975, n - 2))
    else:
        chi2_red = 1.0
        q = 1.96
        warnings.append("Yalnızca 2 kare işaretli — fit artığı ölçülemiyor; en az 3–4 kare önerilir.")
    se_slope = float(np.sqrt(max(chi2_red, 1.0) / sxx))

    speed_ms = abs(slope)
    rel_len = length_sigma_m / scale.length_m
    ci_ms = float(np.hypot(q * se_slope, 1.96 * rel_len * speed_ms))

    speed_kmh = speed_ms * 3.6
    ci_kmh = ci_ms * 3.6
    rel_ci = ci_kmh / speed_kmh if speed_kmh > 0 else np.inf
    if n >= 4 and rel_ci <= _HIGH_REL_CI and not warnings:
        confidence_level = "high"
    elif rel_ci <= _MEDIUM_REL_CI:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    return CrossRatioSpeedResult(
        speed_kmh=round(speed_kmh, 2),
        ci_kmh=round(ci_kmh, 2),
        confidence_level=confidence_level,
        n_points=n,
        direction="toward_ref_b" if slope >= 0 else "toward_ref_a",
        positions_m=[round(float(v), 4) for v in x],
        times_s=[round(float(v), 4) for v in t],
        residual_rms_m=round(residual_rms, 4),
        max_offset_px=round(max_offset, 2),
        warnings=warnings,
    )
