"""T22 — Otomatik kalibrasyon önerisi: vanishing-point tabanlı şerit tespiti.

Yol şerit çizgilerinden yakınsama noktası (VP) hesaplanır; VP + yatay ölçek
referansı (şerit genişliği) kullanılarak aday kontrol noktaları önerilir.

Kısıtlar (CLAUDE.md §kara-kutu):
  - Öneri her zaman operatör onayına sunulur, asla otomatik kabul edilmez.
  - VP dışı / yüksek-RMS durumlarda sessizce yanlış H üretilmez; kalite kapısı devreye girer.
  - Y ekseni tahmini izotropik ölçek yaklaşımına dayanır (uyarı gösterilir).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import cv2
import numpy as np

from .models import CalibrationError, ControlPoint


# ── Veri sınıfları ────────────────────────────────────────────────────────────

@dataclass
class AutoCalibProposal:
    vanishing_point: tuple[float, float] | None
    left_line_pts: list[tuple[float, float]] | None   # [bot_pt, top_pt] görüntü koordinatları
    right_line_pts: list[tuple[float, float]] | None
    proposed_points: list[ControlPoint]
    quality_gate_passed: bool
    quality_reason: str  # 'ok'|'no_lines'|'parallel_lines'|'vp_out_of_bounds'|'high_rms'|'degenerate'
    estimated_rms_m: float | None
    warning: str | None


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _fit_line_ransac(
    segments: list[tuple[float, float, float, float]],
    n_iter: int = 60,
    threshold_px: float = 8.0,
) -> tuple[float, float] | None:
    """RANSAC ile doğru y = a·x + b katsayılarını döner ya da None."""
    pts: list[tuple[float, float]] = []
    for x1, y1, x2, y2 in segments:
        pts.append((float(x1), float(y1)))
        pts.append((float(x2), float(y2)))
    if len(pts) < 4:
        return None

    arr = np.array(pts, dtype=np.float64)
    rng = np.random.default_rng(42)
    best_a: float | None = None
    best_b: float | None = None
    best_n = 0

    for _ in range(n_iter):
        idx = rng.choice(len(arr), 2, replace=False)
        p1, p2 = arr[idx[0]], arr[idx[1]]
        dx = p2[0] - p1[0]
        if abs(dx) < 1e-6:
            continue
        a = (p2[1] - p1[1]) / dx
        b = float(p1[1] - a * p1[0])
        dist = np.abs(arr[:, 1] - (a * arr[:, 0] + b)) / np.sqrt(1.0 + a * a)
        inlier_mask = dist < threshold_px
        n = int(inlier_mask.sum())
        if n > best_n and n >= 2:
            best_n = n
            inliers = arr[inlier_mask]
            coeffs = np.polyfit(inliers[:, 0], inliers[:, 1], 1)
            best_a, best_b = float(coeffs[0]), float(coeffs[1])

    if best_a is None:
        return None
    return (best_a, best_b)


def _intersect_lines(
    line1: tuple[float, float],
    line2: tuple[float, float],
) -> tuple[float, float] | None:
    """y = a1·x + b1 ile y = a2·x + b2 kesişimi. Paralel ise None."""
    a1, b1 = line1
    a2, b2 = line2
    denom = a1 - a2
    if abs(denom) < 1e-6:
        return None
    x = (b2 - b1) / denom
    y = a1 * x + b1
    return (float(x), float(y))


def _line_x_at_y(line: tuple[float, float], y: float) -> float:
    """y = a·x + b → x = (y − b) / a."""
    a, b = line
    if abs(a) < 1e-9:
        return 0.0
    return (y - b) / a


def _clamp_line_to_image(
    line: tuple[float, float],
    h: int,
    w: int,
    y_top: float,
    y_bot: float,
) -> list[tuple[float, float]]:
    """Doğrunun görüntü sınırına kırpılmış iki uç noktasını döner."""
    x_top = max(0.0, min(float(w), _line_x_at_y(line, y_top)))
    x_bot = max(0.0, min(float(w), _line_x_at_y(line, y_bot)))
    return [(x_top, y_top), (x_bot, y_bot)]


# ── Ana fonksiyonlar ──────────────────────────────────────────────────────────

def detect_vanishing_point(
    frame: np.ndarray,
    roi_top_frac: float = 0.20,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None:
    """
    Görüntüden yol yakınsama noktasını ve iki şerit çizgisini tespit eder.

    Döner: (vp, left_line, right_line) — her doğru (a, b) katsayı çifti şeklinde.
    Tespit başarısız olursa None döner.

    Algoritma: Canny + HoughLinesP → açı filtresi → yakın-satır x pozisyonuna göre
    sol/sağ küme → RANSAC fit → kesişim.

    Kümeleme eğim işaretine değil yakın satırdaki x pozisyonuna dayanır; bu sayede
    çapraz monte kameralar (her iki şerit de aynı eğim işaretine sahip olabilir) ve
    perspektif açısı geniş kameralar için de çalışır.
    """
    h, w = frame.shape[:2]
    roi_y = int(h * roi_top_frac)
    roi = frame[roi_y:, :]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    lines_raw = cv2.HoughLinesP(
        edges, 1, np.pi / 180.0,
        threshold=40, minLineLength=30, maxLineGap=12,
    )
    if lines_raw is None:
        return None

    # Yakın satır: görüntünün alt %88'i — kümeleme referansı
    y_ref = float(h * 0.88)
    valid_segs: list[tuple[float, float, float, float, float]] = []  # x1,y1,x2,y2,x_ref

    for seg in lines_raw:
        x1, y1, x2, y2 = [float(v) for v in seg[0]]
        y1 += roi_y
        y2 += roi_y

        dx = x2 - x1
        dy = y2 - y1
        length = float(np.hypot(dx, dy))
        if length < 1e-3:
            continue

        angle_deg = float(abs(np.degrees(np.arctan2(abs(dy), abs(dx)))))
        if not (5.0 <= angle_deg <= 80.0):
            continue

        # Yakın satır (y_ref) üzerindeki x konumu — kümeleme için
        if abs(dy) < 1e-3:
            x_ref = (x1 + x2) / 2.0
        else:
            t = (y_ref - y1) / (y2 - y1)
            x_ref = x1 + t * (x2 - x1)

        valid_segs.append((x1, y1, x2, y2, x_ref))

    if len(valid_segs) < 4:
        return None

    # Yakın satır x pozisyonuna göre sol/sağ küme (görüntü merkezini eşik al)
    cx = w / 2.0
    left_segs = [(x1, y1, x2, y2) for x1, y1, x2, y2, xr in valid_segs if xr < cx]
    right_segs = [(x1, y1, x2, y2) for x1, y1, x2, y2, xr in valid_segs if xr >= cx]

    # Fallback: eğer eşik çok dengesiz dağılıyorsa medyan tabanlı bölme
    if len(left_segs) < 2 or len(right_segs) < 2:
        x_refs = sorted(s[4] for s in valid_segs)
        split = x_refs[len(x_refs) // 2]
        left_segs = [(x1, y1, x2, y2) for x1, y1, x2, y2, xr in valid_segs if xr < split]
        right_segs = [(x1, y1, x2, y2) for x1, y1, x2, y2, xr in valid_segs if xr >= split]

    if len(left_segs) < 2 or len(right_segs) < 2:
        return None

    left_line = _fit_line_ransac(left_segs)
    right_line = _fit_line_ransac(right_segs)

    if left_line is None or right_line is None:
        return None

    vp = _intersect_lines(left_line, right_line)
    if vp is None:
        return None

    return vp, left_line, right_line


def propose_calibration(
    frame: np.ndarray,
    lane_width_m: float,
    n_pairs: int = 4,
) -> AutoCalibProposal:
    """
    Yol şerit çizgilerinden otomatik kalibrasyon noktaları önerir.

    VP + şerit genişliği kullanarak 2·n_pairs aday kontrol noktası üretir.
    Y eksen koordinatları izotropik ölçek yaklaşımıyla hesaplanır (uyarılı).

    Kalite kapısı: şerit tespiti başarısız, VP görüntü dışında, eğimler paralel
    veya tahmini RMS > eşik olursa quality_gate_passed=False döner.
    """
    from .homography import compute_homography  # döngüsel bağımlılığı önlemek için

    h, w = frame.shape[:2]

    detection = detect_vanishing_point(frame)
    if detection is None:
        return AutoCalibProposal(
            vanishing_point=None,
            left_line_pts=None,
            right_line_pts=None,
            proposed_points=[],
            quality_gate_passed=False,
            quality_reason='no_lines',
            estimated_rms_m=None,
            warning="Şerit çizgileri tespit edilemedi — elle işaretleyin.",
        )

    vp, left_line, right_line = detection
    vx, vy = vp

    # Kalite kapısı 1: VP yakın satırın üzerinde olmalı (yani perspektifin doğru yönde
    # yakınsaması — VP aşağıda olsaydı şeritler ters yönde ıraksıyor demektir).
    # X sınırı geniş (±2×genişlik): çapraz kameralarda VP görüntü dışına çıkabilir.
    y_near_ref = h * 0.88
    margin_x = 2.0 * w
    if not ((-margin_x <= vx <= w + margin_x) and (vy < y_near_ref)):
        return AutoCalibProposal(
            vanishing_point=vp,
            left_line_pts=None,
            right_line_pts=None,
            proposed_points=[],
            quality_gate_passed=False,
            quality_reason='vp_out_of_bounds',
            estimated_rms_m=None,
            warning="Yakınsama noktası beklenen konumda değil — şerit çizgileri net görünür mü?",
        )

    # Kalite kapısı 2: eğimler çok yakın değil (neredeyse paralel)
    a_l, _ = left_line
    a_r, _ = right_line
    if abs(a_l - a_r) < 0.05:
        return AutoCalibProposal(
            vanishing_point=vp,
            left_line_pts=None,
            right_line_pts=None,
            proposed_points=[],
            quality_gate_passed=False,
            quality_reason='parallel_lines',
            estimated_rms_m=None,
            warning="Şerit çizgileri neredeyse paralel — yakınsama noktası belirlenemedi.",
        )

    # n_pairs y seviyesini yakın satırdan (alt) uzak satıra (üst) örnekle.
    # VP görüntü içindeyse en az 40px altında kal; değilse görüntünün %35'ine in.
    y_near = h * 0.88
    y_far = h * 0.35
    if vy > 0:
        y_far = max(y_far, vy + 40.0)
    if y_far >= y_near:
        y_far = y_near - 40.0

    y_levels = np.linspace(y_near, y_far, n_pairs)

    # Yakın satır piksel genişliği → ölçek
    xl_near = _line_x_at_y(left_line, y_levels[0])
    xr_near = _line_x_at_y(right_line, y_levels[0])
    pixel_width_near = xr_near - xl_near

    if pixel_width_near < 20.0:
        return AutoCalibProposal(
            vanishing_point=vp,
            left_line_pts=None,
            right_line_pts=None,
            proposed_points=[],
            quality_gate_passed=False,
            quality_reason='degenerate',
            estimated_rms_m=None,
            warning="Yakın satırda şerit piksel genişliği çok dar — öneri güvenilmez.",
        )

    scale_near = lane_width_m / pixel_width_near  # m/px

    # Perspektif-aware y katsayısı: VP'den uzaklık ters orantılıdır.
    # world_y = K * (1/(y - vy) - 1/(y_near - vy))
    # K, yakın satırdaki izotropik ölçekten türetilir: K = scale_near * (y_near - vy)^2
    y_near_depth = y_near - vy  # VP'den yakın satıra olan piksel derinliği
    perspective_K = scale_near * (y_near_depth ** 2)

    proposed: list[ControlPoint] = []
    suffix = uuid.uuid4().hex[:4]
    for k, y in enumerate(y_levels):
        xl = _line_x_at_y(left_line, y)
        xr = _line_x_at_y(right_line, y)
        # Perspektif y: 1/(y-vy) terimiyle derinliği doğru modeller
        depth = y - vy
        if abs(depth) < 1e-3:
            depth = 1.0
        world_y = float(perspective_K * (1.0 / depth - 1.0 / y_near_depth))
        proposed.append(ControlPoint(
            id=f"av-L{k}-{suffix}",
            pixel=(float(xl), float(y)),
            world_m=(0.0, world_y),
            source="auto-vanishing",
        ))
        proposed.append(ControlPoint(
            id=f"av-R{k}-{suffix}",
            pixel=(float(xr), float(y)),
            world_m=(float(lane_width_m), world_y),
            source="auto-vanishing",
        ))

    # Tahmini RMS hesapla
    estimated_rms: float | None = None
    try:
        cal = compute_homography(proposed)
        estimated_rms = cal.reprojection_rms_m
    except CalibrationError:
        return AutoCalibProposal(
            vanishing_point=vp,
            left_line_pts=None,
            right_line_pts=None,
            proposed_points=proposed,
            quality_gate_passed=False,
            quality_reason='degenerate',
            estimated_rms_m=None,
            warning="H matrisi hesaplanamadı — noktalar dejenere konfigürasyonda.",
        )

    # Kalite kapısı 3: RMS eşiği
    _RMS_GATE_M = 0.8
    quality_gate_passed = estimated_rms < _RMS_GATE_M
    quality_reason = 'ok' if quality_gate_passed else 'high_rms'

    if quality_gate_passed:
        warning = (
            "Y ekseni izotropik ölçek tahminiyle hesaplandı. "
            "Adli kullanım için kontrol noktaları tablosundaki y-değerlerini doğrulayın."
        )
    else:
        warning = (
            f"Tahmini RMS yüksek ({estimated_rms:.2f} m ≥ {_RMS_GATE_M} m). "
            "Y-koordinatlarını düzeltin veya elle kalibrasyon yapın."
        )

    # Görselleştirme için şerit çizgisi uç noktaları (VP görüntü dışındaysa üstten başla)
    y_vis_top = max(0.0, min(vy, h * 0.30))
    left_pts = _clamp_line_to_image(left_line, h, w, y_vis_top, float(h - 1))
    right_pts = _clamp_line_to_image(right_line, h, w, y_vis_top, float(h - 1))

    return AutoCalibProposal(
        vanishing_point=vp,
        left_line_pts=left_pts,
        right_line_pts=right_pts,
        proposed_points=proposed,
        quality_gate_passed=quality_gate_passed,
        quality_reason=quality_reason,
        estimated_rms_m=estimated_rms,
        warning=warning,
    )
