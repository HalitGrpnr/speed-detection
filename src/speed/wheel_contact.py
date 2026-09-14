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

    if speed_ms < 0:
        warnings.append("Hesaplanan hız negatif — işaretlerin kare sırasını kontrol edin.")

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
