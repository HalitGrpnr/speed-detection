"""T28 Faz 2 — Kaçış noktası (VP) sağlayıcıları: ortak arayüz.

Cross-ratio çekirdeği (`src/speed/cross_ratio.py`) yalnızca bir `(x, y)` noktası (veya sonsuz)
ister; bu modül o noktayı farklı kaynaklardan, belirsizliğiyle birlikte üretir:

  - "lane_manual"  — operatörün işaretlediği şerit/kenar çizgileri (her biri ≥ 2 nokta)
  - "lane_auto"    — `vanishing.detect_vanishing_point` (Canny+Hough+RANSAC) — öneri, onay gerekir
  - "trajectory"   — araç üzerindeki rijit noktaların izleri. Düz giden araç yalnızca öteleme
                     yaptığı için gövdedeki HER noktanın izi aynı VP'de buluşur. Tek bir iz VP'yi
                     belirlemez (yalnızca bir doğru verir) — en az 2 bağımsız iz gerekir.

Hepsi `VanishingEstimate` döndürür (nokta veya sonsuz yön + 2×2 kovaryans + uyarılar).
İki kaynak varsa `compare_vanishing` ile uyum kontrolü yapılır (bedava çapraz doğrulama).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
from typing import Literal, Sequence

import numpy as np

VpSource = Literal["lane_manual", "lane_auto", "trajectory"]

_CHI2_2DOF_95 = 5.991            # χ²(2) %95 — iki VP'nin uyum testi
_NEAR_PARALLEL_DEG = 1.0         # çizgiler arası açı bunun altındaysa VP çok belirsiz
_INLIER_K = 3.0                  # RANSAC: doğruya dik uzaklık ≤ k·σ
_MAX_RANSAC_PAIRS = 400


# ── Doğru uydurma ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FittedLine:
    """Toplam en küçük kareler doğrusu + belirsizliği (px)."""

    centroid: tuple[float, float]
    direction: tuple[float, float]     # birim
    n_points: int
    rms_px: float                      # noktaların doğruya dik RMS sapması
    sigma_perp_px: float               # nokta başına dik belirsizlik (max(rms, piksel σ))
    sigma_angle_rad: float
    extent: tuple[tuple[float, float], tuple[float, float]]  # görselleştirme için uç noktalar

    def distance_to(self, p: Sequence[float]) -> float:
        d = np.asarray(self.direction)
        rel = np.asarray(p, dtype=np.float64) - np.asarray(self.centroid)
        return float(abs(rel[0] * d[1] - rel[1] * d[0]))

    def sigma_at(self, p: Sequence[float]) -> float:
        """Doğrunun p konumundaki dik belirsizliği: ofset + açı × mesafe."""
        rel = np.asarray(p, dtype=np.float64) - np.asarray(self.centroid)
        along = float(rel @ np.asarray(self.direction))
        s_off = self.sigma_perp_px / np.sqrt(self.n_points)
        return float(np.hypot(s_off, along * self.sigma_angle_rad))


def fit_line(points: Sequence[Sequence[float]] | np.ndarray, pixel_sigma: float = 1.0) -> FittedLine:
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2:
        raise ValueError("Doğru için en az 2 nokta (N, 2) gerekir.")
    c = pts.mean(axis=0)
    _, sing, vt = np.linalg.svd(pts - c, full_matrices=False)
    if sing[0] < 1e-9:
        raise ValueError("Doğru noktaları çakışık.")
    d = vt[0] / np.linalg.norm(vt[0])
    proj = (pts - c) @ d
    perp = (pts - c) @ np.array([-d[1], d[0]])
    n = len(pts)
    rms = float(np.sqrt(np.sum(perp**2) / (n - 2))) if n > 2 else 0.0
    sigma_perp = max(rms, pixel_sigma)
    sigma_angle = sigma_perp / float(np.sqrt(np.sum(proj**2)))
    lo, hi = c + d * proj.min(), c + d * proj.max()
    return FittedLine(
        centroid=(float(c[0]), float(c[1])),
        direction=(float(d[0]), float(d[1])),
        n_points=n,
        rms_px=rms,
        sigma_perp_px=sigma_perp,
        sigma_angle_rad=sigma_angle,
        extent=((float(lo[0]), float(lo[1])), (float(hi[0]), float(hi[1]))),
    )


# ── Kesişim ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VanishingEstimate:
    point: tuple[float, float] | None           # None → sonsuzda (doğrular paralel)
    direction: tuple[float, float] | None       # yalnızca sonsuzda: görüntüdeki ortak yön
    covariance: tuple[tuple[float, float], tuple[float, float]] | None
    source: VpSource
    n_lines: int                                # değerlendirilen doğru sayısı
    n_inliers: int                              # kesişime katılan doğru sayısı
    residual_rms_sigma: float                   # doğruların VP'ye normalize dik sapması (≈1 iyi)
    lines: tuple[FittedLine, ...]               # kesişime katılan doğrular (UI + audit)
    warnings: tuple[str, ...] = ()

    @property
    def at_infinity(self) -> bool:
        return self.point is None

    @property
    def sigma_px(self) -> tuple[float, float] | None:
        """Kovaryans elipsinin (büyük, küçük) yarı eksenleri, 1σ."""
        if self.covariance is None:
            return None
        ev = np.linalg.eigvalsh(np.asarray(self.covariance))
        return (float(np.sqrt(max(ev[1], 0.0))), float(np.sqrt(max(ev[0], 0.0))))


def _cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _homogeneous(line: FittedLine) -> np.ndarray:
    d = np.asarray(line.direction)
    nrm = np.array([-d[1], d[0]])
    return np.array([nrm[0], nrm[1], -float(nrm @ np.asarray(line.centroid))])


def _intersect(lines: Sequence[FittedLine], iterations: int = 3):
    """Ağırlıklı en küçük kareler kesişimi.

    Döner: (nokta | None, sonsuz yön | None, kovaryans | None, normalize RMS).
    """
    L = np.array([_homogeneous(l) for l in lines])
    # Koşullama: koordinatları doğru merkezlerine göre ölçekle
    cents = np.array([l.centroid for l in lines])
    t = cents.mean(axis=0)
    s = max(float(np.std(cents)), 1.0)
    T_inv = np.array([[s, 0, t[0]], [0, s, t[1]], [0, 0, 1.0]])   # normalize → piksel
    Ln = L @ T_inv                                                 # l' = l · T⁻¹

    w = np.ones(len(lines))
    v = None
    for _ in range(iterations):
        A = Ln / np.linalg.norm(Ln[:, :2], axis=1, keepdims=True) * np.sqrt(w)[:, None]
        _, _, vt = np.linalg.svd(A)
        vn = vt[-1]
        v = T_inv @ vn
        if abs(v[2]) < 1e-12 * np.linalg.norm(v[:2]):
            break
        p = v[:2] / v[2]
        sig_px = np.array([max(l.sigma_at(p), 1e-6) for l in lines])
        w = (s / sig_px) ** 2  # normalize ölçekte 1/σ²

    if abs(v[2]) < 1e-12 * np.linalg.norm(v[:2]):
        d = v[:2] / np.linalg.norm(v[:2])
        ang = [np.arcsin(min(1.0, abs(_cross2(np.asarray(l.direction), d)))) / l.sigma_angle_rad for l in lines]
        rms = float(np.sqrt(np.mean(np.square(ang))))
        return None, (float(d[0]), float(d[1])), None, rms

    p = v[:2] / v[2]
    N = np.array([_homogeneous(l)[:2] for l in lines])
    sig = np.array([max(l.sigma_at(p), 1e-6) for l in lines])
    W = 1.0 / sig**2
    resid = np.array([l.distance_to(p) for l in lines]) / sig
    dof = len(lines) - 2
    chi2_red = float(np.sum(resid**2) / dof) if dof > 0 else 1.0
    info = N.T @ (N * W[:, None])
    cov = np.linalg.inv(info) * max(chi2_red, 1.0)
    rms = float(np.sqrt(np.mean(resid**2)))
    return (float(p[0]), float(p[1])), None, (tuple(cov[0]), tuple(cov[1])), rms


def _parallel_warning(lines: Sequence[FittedLine]) -> list[str]:
    dirs = [np.asarray(l.direction) for l in lines]
    max_angle = max(
        np.degrees(np.arcsin(min(1.0, abs(_cross2(a, b)))))
        for a, b in combinations(dirs, 2)
    )
    if max_angle < _NEAR_PARALLEL_DEG:
        return [
            f"Çizgiler neredeyse paralel (en büyük açı {max_angle:.2f}°) — perspektif referansı çok "
            "uzakta ve belirsiz. Ölçüm yine çalışır ama güven aralığı genişler."
        ]
    return []


def _estimate(lines: list[FittedLine], source: VpSource, n_total: int, warnings: list[str]) -> VanishingEstimate:
    point, direction, cov, rms = _intersect(lines)
    warnings = warnings + _parallel_warning(lines)
    if len(lines) == 2:
        warnings.append(
            "Yalnızca 2 çizgi — kesişimin tutarlılığı kontrol edilemiyor; mümkünse 3. çizgi ekleyin."
        )
    if rms > 3.0:
        warnings.append(
            f"Çizgiler tek bir noktada buluşmuyor (normalize sapma {rms:.1f}) — işaretleri kontrol edin."
        )
    return VanishingEstimate(
        point=point,
        direction=direction,
        covariance=cov,
        source=source,
        n_lines=n_total,
        n_inliers=len(lines),
        residual_rms_sigma=round(rms, 3),
        lines=tuple(lines),
        warnings=tuple(warnings),
    )


# ── Sağlayıcılar ──────────────────────────────────────────────────────────────

def vanishing_from_lines(
    lines_points: Sequence[Sequence[Sequence[float]]],
    source: VpSource = "lane_manual",
    pixel_sigma: float = 1.0,
) -> VanishingEstimate:
    """Operatörün işaretlediği çizgilerden (her biri ≥ 2 nokta) VP. Tüm çizgiler kullanılır."""
    if len(lines_points) < 2:
        raise ValueError("Perspektif referansı için en az 2 çizgi gerekir.")
    lines = [fit_line(pts, pixel_sigma) for pts in lines_points]
    return _estimate(lines, source, len(lines), [])


def vanishing_from_lane_detection(frame: np.ndarray, pixel_sigma: float = 2.0) -> VanishingEstimate | None:
    """Otomatik şerit tespiti (öneri). Tespit başarısızsa None."""
    from .vanishing import detect_vanishing_point

    det = detect_vanishing_point(frame)
    if det is None:
        return None
    _, left, right = det
    h = frame.shape[0]
    lines_points = []
    for a, b in (left, right):           # y = a·x + b
        if abs(a) < 1e-9:
            return None
        ys = (0.55 * h, 0.95 * h)
        lines_points.append([((y - b) / a, y) for y in ys])
    est = vanishing_from_lines(lines_points, source="lane_auto", pixel_sigma=pixel_sigma)
    return replace(est, warnings=est.warnings + (
        "Otomatik şerit tespiti — çizgilerin yolla örtüştüğünü onaylayın.",
    ))


def vanishing_from_trajectories(
    trajectories: Sequence[Sequence[Sequence[float]]],
    pixel_sigma: float = 1.0,
    min_points: int = 3,
    max_curve_rms_px: float = 2.0,
    seed: int = 0,
) -> VanishingEstimate:
    """Araç üzerindeki rijit noktaların izlerinden VP (RANSAC ile aykırı izler elenir).

    Aykırı izler: tekerlek jantı (dönme), yansıma, arka plana kayan takip noktaları.
    Eğri izler (araç bu aralıkta dönüyor) elenir ve uyarı verilir.
    """
    warnings: list[str] = []
    candidates: list[FittedLine] = []
    curved = 0
    for traj in trajectories:
        pts = np.asarray(traj, dtype=np.float64)
        if len(pts) < min_points:
            continue
        try:
            line = fit_line(pts, pixel_sigma)
        except ValueError:
            continue
        if line.rms_px > max(max_curve_rms_px, 2 * pixel_sigma):
            curved += 1
            continue
        candidates.append(line)

    n_total = len(candidates) + curved
    if curved:
        warnings.append(
            f"{curved}/{n_total} iz doğruya oturmuyor — araç bu aralıkta tam düz gitmiyor olabilir; "
            "daha düz bir kare aralığı seçin."
        )
    if len(candidates) < 2:
        raise ValueError(
            "Araç izinden perspektif referansı için en az 2 bağımsız düz iz gerekir "
            "(tek iz yalnızca bir doğru verir, noktayı belirlemez)."
        )

    pairs = list(combinations(range(len(candidates)), 2))
    if len(pairs) > _MAX_RANSAC_PAIRS:
        rng = np.random.default_rng(seed)
        pairs = [tuple(p) for p in rng.choice(len(candidates), size=(_MAX_RANSAC_PAIRS, 2)) if p[0] != p[1]]

    best: list[int] = []
    best_cost = np.inf
    for i, j in pairs:
        point, _, _, _ = _intersect([candidates[i], candidates[j]], iterations=1)
        if point is None:
            continue
        ratios = np.array([l.distance_to(point) / max(l.sigma_at(point), 1e-6) for l in candidates])
        inl = np.flatnonzero(ratios <= _INLIER_K)
        cost = float(np.sum(np.minimum(ratios, _INLIER_K) ** 2))
        if len(inl) > len(best) or (len(inl) == len(best) and cost < best_cost):
            best, best_cost = list(inl), cost

    inliers = [candidates[k] for k in best] if len(best) >= 2 else candidates
    outliers = len(candidates) - len(inliers)
    if outliers:
        frac = outliers / len(candidates)
        msg = f"{outliers} iz ortak noktaya uymadığı için elendi (tekerlek dönmesi, yansıma vb.)."
        if frac > 0.5:
            msg += " Elenen oran yüksek — sonuç şüpheli, şerit çizgisiyle çapraz kontrol önerilir."
        warnings.append(msg)
    return _estimate(inliers, "trajectory", n_total, warnings)


# ── Uyum kontrolü ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VanishingAgreement:
    status: Literal["agree", "disagree", "indeterminate"]
    angle_deg: float                  # ölçüm bölgesinden bakınca iki VP yönü arasındaki açı
    relative_distance: float | None   # |d_a − d_b| / min(d_a, d_b), ikisi de sonluysa
    mahalanobis2: float | None
    message: str


def _dir_from(at: np.ndarray, est: VanishingEstimate) -> np.ndarray:
    if est.point is None:
        return np.asarray(est.direction)
    v = np.asarray(est.point) - at
    return v / np.linalg.norm(v)


def compare_vanishing(
    a: VanishingEstimate,
    b: VanishingEstimate,
    at: Sequence[float],
    max_angle_deg: float = 1.0,
    max_relative_distance: float = 0.10,
) -> VanishingAgreement:
    """İki kaynaktan gelen VP'lerin ölçüm bölgesi (`at`, ör. iz merkezi) açısından uyumu.

    İkisinin de kovaryansı varsa karar χ²(2) %95 testiyle verilir; yoksa açı + göreli uzaklık
    eşikleriyle. Açı ve uzaklık her durumda operatöre gösterilmek üzere raporlanır.
    """
    at_ = np.asarray(at, dtype=np.float64)
    da, db = _dir_from(at_, a), _dir_from(at_, b)
    cosang = abs(float(da @ db))  # sonsuz yönün işareti belirsiz
    angle = float(np.degrees(np.arccos(min(1.0, cosang))))

    rel = None
    m2 = None
    if a.point is not None and b.point is not None:
        ra = float(np.linalg.norm(np.asarray(a.point) - at_))
        rb = float(np.linalg.norm(np.asarray(b.point) - at_))
        rel = abs(ra - rb) / min(ra, rb)
        if a.covariance is not None and b.covariance is not None:
            S = np.asarray(a.covariance) + np.asarray(b.covariance)
            diff = np.asarray(a.point) - np.asarray(b.point)
            m2 = float(diff @ np.linalg.solve(S, diff))

    if m2 is not None:
        agree = m2 <= _CHI2_2DOF_95
        basis = f"istatistiksel test (χ²={m2:.2f}, eşik {_CHI2_2DOF_95})"
    elif rel is not None:
        agree = angle <= max_angle_deg and rel <= max_relative_distance
        basis = f"açı {angle:.2f}°, uzaklık farkı %{rel * 100:.1f}"
    elif a.point is None and b.point is None:
        agree = angle <= max_angle_deg
        basis = f"iki referans da sonsuzda, yön farkı {angle:.2f}°"
    else:
        return VanishingAgreement(
            status="indeterminate", angle_deg=round(angle, 3), relative_distance=None,
            mahalanobis2=None,
            message="Bir kaynak sonsuz (paralel), diğeri sonlu — konum karşılaştırılamıyor; yalnızca "
                    f"yön farkı {angle:.2f}°.",
        )

    name = {"lane_manual": "şerit", "lane_auto": "otomatik şerit", "trajectory": "araç izi"}
    label = f"{name[a.source]} ve {name[b.source]} referansı"
    msg = (f"{label} uyuşuyor ✓ ({basis})." if agree else
           f"{label} ayrışıyor ⚠ ({basis}) — çizgileri ve seçilen kare aralığını kontrol edin.")
    return VanishingAgreement(
        status="agree" if agree else "disagree",
        angle_deg=round(angle, 3),
        relative_distance=None if rel is None else round(rel, 4),
        mahalanobis2=None if m2 is None else round(m2, 3),
        message=msg,
    )
