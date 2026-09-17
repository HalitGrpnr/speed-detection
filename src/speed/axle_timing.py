"""T27 — H-bağımsız dingil adımlama (axle timing).

Yöntem:
  Operatör sahnedeki görünür bir yol referans noktasını (çizgi, kenar, vb.) seçer.
  Her geçiş olayında ön ve arka tekeri referans noktası öncesi/sonrası karelerde işaretler.
  Mevcut interpolasyon kesirli kare hassasiyeti verir.
  hız = dingil_m / ((t_arka − t_ön) / fps) × 3.6

  H'ye bağımlılık sıfır: mesafe bilinen fiziksel ölçümden, zaman kare sayısından gelir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.calibration.interpolation import interpolate_calibration_point


@dataclass
class AxleTimingResult:
    speed_kmh: float
    ci_kmh: float
    confidence_level: str      # "high" | "medium" | "low"
    crossing_count: int
    crossing_speeds_kmh: list[float]   # audit izi
    delta_t_per_crossing_s: list[float]
    warnings: list[str] = field(default_factory=list)


def axle_timing_speed(
    crossings: list[dict],
    wheelbase_m: float,
    fps: float,
) -> AxleTimingResult:
    """H-bağımsız dingil adımlama ile hız hesapla.

    crossings: her eleman şu anahtarları taşır:
      front_frame_n, front_pixel_n, front_frame_n1, front_pixel_n1,
      rear_frame_n,  rear_pixel_n,  rear_frame_n1,  rear_pixel_n1,
      target_px   (yol referans noktası — ön ve arka için ortak)

    Algoritma:
      1. Ön tekerlek için interpolate_calibration_point → kesirli t_front
      2. Arka tekerlek için aynısı → kesirli t_rear
      3. speed_i = wheelbase_m / ((t_rear - t_front) / fps) × 3.6
      4. Özet: tek geçiş → CI çerçeve belirsizliğinden; çok geçiş → std tabanlı.
    """
    warnings: list[str] = []

    if not crossings:
        raise ValueError("En az 1 geçiş olayı gereklidir.")

    if wheelbase_m <= 0:
        raise ValueError("Dingil mesafesi pozitif olmalıdır.")

    crossing_speeds: list[float] = []
    delta_ts: list[float] = []

    for i, c in enumerate(crossings):
        target = tuple(c["target_px"])

        # Ön tekerlek bracket
        fn  = int(c["front_frame_n"])
        fn1 = int(c["front_frame_n1"])
        fp_n  = tuple(c["front_pixel_n"])
        fp_n1 = tuple(c["front_pixel_n1"])

        # Arka tekerlek bracket
        rn  = int(c["rear_frame_n"])
        rn1 = int(c["rear_frame_n1"])
        rp_n  = tuple(c["rear_pixel_n"])
        rp_n1 = tuple(c["rear_pixel_n1"])

        if fn1 != fn + 1:
            warnings.append(
                f"Geçiş {i+1}: ön tekerlek kareleri ardışık değil ({fn}, {fn1}) — "
                "interpolasyon yine de uygulanır, doğruluk düşebilir."
            )
        if rn1 != rn + 1:
            warnings.append(
                f"Geçiş {i+1}: arka tekerlek kareleri ardışık değil ({rn}, {rn1}) — "
                "interpolasyon yine de uygulanır, doğruluk düşebilir."
            )

        try:
            _, t_frac_front = interpolate_calibration_point(fp_n, fp_n1, target)
        except ValueError:
            warnings.append(f"Geçiş {i+1}: ön tekerlek hareketsiz — kare ortası kullanıldı.")
            t_frac_front = 0.5

        try:
            _, t_frac_rear = interpolate_calibration_point(rp_n, rp_n1, target)
        except ValueError:
            warnings.append(f"Geçiş {i+1}: arka tekerlek hareketsiz — kare ortası kullanıldı.")
            t_frac_rear = 0.5

        t_frac_front = float(np.clip(t_frac_front, 0.0, 1.0))
        t_frac_rear  = float(np.clip(t_frac_rear,  0.0, 1.0))

        t_front_s = (fn  + t_frac_front) / fps
        t_rear_s  = (rn  + t_frac_rear)  / fps
        delta_t   = t_rear_s - t_front_s

        if delta_t <= 0:
            warnings.append(
                f"Geçiş {i+1}: t_arka ≤ t_ön ({delta_t:.4f}s) — bu geçiş atlandı."
            )
            continue

        speed_kmh = wheelbase_m / delta_t * 3.6
        crossing_speeds.append(speed_kmh)
        delta_ts.append(delta_t)

    if not crossing_speeds:
        raise ValueError("Geçerli geçiş olayı bulunamadı — tüm geçişler atlandı.")

    n = len(crossing_speeds)
    value_kmh = float(np.median(crossing_speeds))

    if n == 1:
        # CI: çerçeve belirsizliğinden türetilir (±0.5 kare ön + ±0.5 kare arka)
        # Δt'nin maksimum belirsizliği = 1 kare / fps
        dt = delta_ts[0]
        # hız × (1 kare / (fps × Δt)) × 2  ≈  propagation
        frame_uncertainty_s = 1.0 / fps
        ci_kmh = float(wheelbase_m / (dt**2) * frame_uncertainty_s * 3.6)
        confidence_level = "medium"
    else:
        ci_kmh = float(np.std(crossing_speeds, ddof=1) * 2.0 / np.sqrt(n))
        if n >= 3 and ci_kmh < 5.0:
            confidence_level = "high"
        elif ci_kmh < 15.0:
            confidence_level = "medium"
        else:
            confidence_level = "low"

    return AxleTimingResult(
        speed_kmh=round(value_kmh, 1),
        ci_kmh=round(ci_kmh, 1),
        confidence_level=confidence_level,
        crossing_count=n,
        crossing_speeds_kmh=[round(v, 1) for v in crossing_speeds],
        delta_t_per_crossing_s=[round(dt, 4) for dt in delta_ts],
        warnings=warnings,
    )
