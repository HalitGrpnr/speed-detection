from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.calibration.homography import pixel_to_world


@dataclass
class WheelSpeedResult:
    value_kmh: float
    ci_kmh: float
    confidence_level: str  # "high" | "medium" | "low"
    mark_count: int
    residual_kmh: float
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProfilePoint:
    t_s: float          # saniye cinsinden zaman (segment orta noktası)
    speed_kmh: float    # pencereleme sonrası yumuşatılmış hız
    ci_kmh: float       # yaklaşık %95 CI (pencere std × 2 / √k)
    accel_ms2: float | None = None  # merkezi fark ivme, sınır noktalarında None


@dataclass
class WheelSpeedProfile:
    """T19 — Çok-işaretli tekerlek hız profili (kayan pencere yumuşatma)."""
    points: list[ProfilePoint]          # yumuşatılmış profil (n-1 nokta)
    raw_pairwise_kmh: list[float]       # ham ardışık çift hızlar (audit iz)
    summary: WheelSpeedResult           # T16 tek-değer özet (birincil hız korunur)
    smoothing_window: int               # audit iz: kaç segment pencerelendi
    warnings: list[str] = field(default_factory=list)


def wheel_contact_speed(
    marks: list[dict],
    H: np.ndarray,
    fps: float,
) -> WheelSpeedResult:
    """Operatör-işaretli tekerlek temas noktalarından hız hesapla.

    marks: [{"frame": float, "pixel": [x, y]}, ...] — en az 2 gerekli.
    H: kalibrasyon homografi matrisi (pixel → dünya m).
    fps: video kare hızı.

    Algoritma:
    - Her işaret pikseli H ile dünya koordinatına çevrilir.
    - Ardışık dünya noktaları arasında Öklid mesafesi (kümülatif odometer).
    - Mesafe vs. zaman doğrusal fit → eğim = hız (m/s) → km/h.
    - CI: ardışık çift hızlarının standart sapması üzerinden yaklaşık %95.
    """
    warnings: list[str] = []
    n = len(marks)

    if n < 2:
        raise ValueError("En az 2 işaret gereklidir.")

    if n < 3:
        warnings.append(
            "Yalnızca 2 işaret var; güven aralığı hesaplanamaz — en az 3 önerilir."
        )

    # Kare sırasına göre sırala (unsorted marks yanlış kümülatif verir)
    marks = sorted(marks, key=lambda m: float(m["frame"]))

    # T20: Onaylanmamış auto işaretler uyarı taşır
    auto_unconfirmed = [
        m for m in marks
        if m.get("source", "manual") == "auto"
    ]
    if auto_unconfirmed:
        warnings.append(
            f"{len(auto_unconfirmed)} otomatik (onaylanmamış) işaret içeriyor — "
            "operatör doğrulaması önerilir."
        )

    worlds = [
        pixel_to_world(H, (float(m["pixel"][0]), float(m["pixel"][1])))
        for m in marks
    ]
    times = [float(m["frame"]) / fps for m in marks]

    cumulative = [0.0]
    for i in range(1, n):
        d = float(np.hypot(worlds[i][0] - worlds[i - 1][0], worlds[i][1] - worlds[i - 1][1]))
        cumulative.append(cumulative[-1] + d)

    t_arr = np.array(times, dtype=float)
    d_arr = np.array(cumulative, dtype=float)

    coeffs = np.polyfit(t_arr, d_arr, 1)
    speed_ms = float(coeffs[0])
    # Kümülatif Öklid mesafesi herzaman >= 0 olduğundan speed_ms < 0 üretilmez.
    value_kmh = abs(speed_ms) * 3.6

    # Ardışık çift hızları (residual tahmini)
    pairwise_kmh: list[float] = []
    for i in range(1, n):
        dt = times[i] - times[i - 1]
        if dt > 0:
            pairwise_kmh.append((cumulative[i] - cumulative[i - 1]) / dt * 3.6)

    residual_kmh = float(np.std(pairwise_kmh)) if len(pairwise_kmh) >= 2 else 0.0

    # CI: yaklaşık %95 (standart hata × 2)
    if n >= 3 and residual_kmh > 0:
        ci_kmh = float(residual_kmh * 2.0 / np.sqrt(n - 1))
    else:
        ci_kmh = residual_kmh

    if n >= 4 and residual_kmh < 5.0:
        confidence_level = "high"
    elif n >= 2 and residual_kmh < 15.0:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    return WheelSpeedResult(
        value_kmh=round(value_kmh, 1),
        ci_kmh=round(ci_kmh, 1),
        confidence_level=confidence_level,
        mark_count=n,
        residual_kmh=round(residual_kmh, 1),
        warnings=warnings,
    )


def wheel_contact_profile(
    marks: list[dict],
    H: np.ndarray,
    fps: float,
    smoothing_window: int = 3,
) -> WheelSpeedProfile:
    """Çok-işaretli tekerlek temas noktalarından kayan pencere hız profili.

    marks: [{"frame": float, "pixel": [x, y]}, ...] — profil için ≥ 3 önerilir.
    smoothing_window: pencereleme boyutu (tek sayı önerilir; sınırlarda kırpılır).

    Algoritma:
    1. wheel_contact_speed ile tek-değer özet hesaplanır (T16 birincil hız korunur).
    2. Her ardışık çift → segment hızı (km/h) ve segment orta nokta zamanı.
    3. Kayan pencere (boyut=smoothing_window) ile her noktada ortalama ve std.
    4. CI = 2 × std / √k (yaklaşık %95, k = pencere içindeki segment sayısı).
    5. İvme: merkezi sonlu fark (sınır noktaları için None).

    Tuzak (PROGRESS.md dersi): ilk örnek yapay sıfır hız pencereye GİRMEZ —
    burada sıfır hız riski yok (tüm segment hızları gerçek ölçüm).
    """
    warnings: list[str] = []

    # İşaretleri kare numarasına göre sırala
    marks_sorted = sorted(marks, key=lambda m: float(m["frame"]))
    n = len(marks_sorted)

    if n < 2:
        raise ValueError("En az 2 işaret gereklidir.")
    if n < 3:
        warnings.append(
            "Profil için en az 3 işaret önerilir; 2 işaretle tek segment elde edilir, "
            "pencereleme ve ivme hesaplanamaz."
        )
    elif n < 5:
        warnings.append(
            f"{n} işaretle profil sınırlı hassasiyet taşır; 5+ işaret önerilir."
        )

    # T16 tek-değer özet (birincil hız korunur, raporda birincil olarak kullanılır)
    summary = wheel_contact_speed(marks_sorted, H, fps)

    # Dünya koordinatları ve zaman dizisi
    worlds = [
        pixel_to_world(H, (float(m["pixel"][0]), float(m["pixel"][1])))
        for m in marks_sorted
    ]
    times = [float(m["frame"]) / fps for m in marks_sorted]

    cumulative = [0.0]
    for i in range(1, n):
        d = float(np.hypot(
            worlds[i][0] - worlds[i - 1][0],
            worlds[i][1] - worlds[i - 1][1],
        ))
        cumulative.append(cumulative[-1] + d)

    # Ardışık çift hızları ve segment orta nokta zamanları
    raw_pairwise_kmh: list[float] = []
    midpoint_times: list[float] = []
    for i in range(1, n):
        dt = times[i] - times[i - 1]
        if dt <= 0:
            continue
        v_kmh = (cumulative[i] - cumulative[i - 1]) / dt * 3.6
        raw_pairwise_kmh.append(v_kmh)
        midpoint_times.append((times[i] + times[i - 1]) / 2.0)

    m = len(raw_pairwise_kmh)

    # Kayan pencere yumuşatma
    half_w = smoothing_window // 2
    smoothed_speeds: list[float] = []
    smoothed_cis: list[float] = []
    for i in range(m):
        lo = max(0, i - half_w)
        hi = min(m - 1, i + half_w)
        window = raw_pairwise_kmh[lo : hi + 1]
        smoothed_speeds.append(float(np.mean(window)))
        if len(window) >= 2:
            ci = float(np.std(window, ddof=1) * 2.0 / np.sqrt(len(window)))
        else:
            ci = 0.0
        smoothed_cis.append(ci)

    # İvme: merkezi sonlu fark (sınır noktaları None)
    accels: list[float | None] = [None] * m
    for i in range(1, m - 1):
        dt = midpoint_times[i + 1] - midpoint_times[i - 1]
        if dt > 0:
            dv_ms = (smoothed_speeds[i + 1] - smoothed_speeds[i - 1]) / 3.6
            accels[i] = round(dv_ms / dt, 3)

    points = [
        ProfilePoint(
            t_s=round(midpoint_times[i], 4),
            speed_kmh=round(smoothed_speeds[i], 1),
            ci_kmh=round(smoothed_cis[i], 1),
            accel_ms2=accels[i],
        )
        for i in range(m)
    ]

    return WheelSpeedProfile(
        points=points,
        raw_pairwise_kmh=[round(v, 1) for v in raw_pairwise_kmh],
        summary=summary,
        smoothing_window=smoothing_window,
        warnings=warnings,
    )
