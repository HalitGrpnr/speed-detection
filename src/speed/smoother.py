from __future__ import annotations

from typing import Literal

import numpy as np

from .models import SpeedSample


def sliding_window_smooth(
    samples: list[SpeedSample],
    window_s: float,
    method: Literal["median", "mean", "regression"] = "median",
    min_detectable_kmh: float = 0.0,
) -> list[tuple[float, float]]:
    """Kayan pencere yumuşatma — her nokta için çevresindeki window_s saniyelik örnekleri kullanır.

    min_detectable_kmh: bu değerin altı ölçüm gürültüsü sayılır → 0 olarak raporlanır
    (durmuş araçtaki tespit jitter'ından kaynaklanan sahte hız baskılanır).
    Dönüş: [(t_s, smoothed_kmh)] — girdiyle aynı uzunluk.
    """
    if not samples:
        return []

    times = np.array([s.t_s for s in samples])
    speeds = np.array([s.speed_kmh for s in samples])
    half = window_s / 2.0
    result: list[tuple[float, float]] = []

    for i, s in enumerate(samples):
        t = s.t_s
        mask = (times >= t - half) & (times <= t + half)
        w_times = times[mask]
        w_speeds = speeds[mask]

        if len(w_speeds) == 0:
            smoothed = s.speed_kmh
        elif method == "median":
            smoothed = float(np.median(w_speeds))
        elif method == "mean":
            smoothed = float(np.mean(w_speeds))
        elif method == "regression":
            if len(w_speeds) >= 2:
                from scipy.stats import linregress
                slope, intercept, *_ = linregress(w_times, w_speeds)
                smoothed = float(slope * t + intercept)
            else:
                smoothed = float(w_speeds[0])
        else:
            raise ValueError(f"Bilinmeyen method: {method!r}")

        clamped = max(0.0, smoothed)
        result.append((t, 0.0 if clamped < min_detectable_kmh else clamped))

    return result
