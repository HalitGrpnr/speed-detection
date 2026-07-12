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

    samples[0].speed_kmh her zaman 0.0'dır (önceki nokta yok, gerçek bir ölçüm değil —
    bkz. track_to_world). Bu yapay değer pencere istatistiklerinden hariç tutulur; aksi
    halde track'in başındaki birkaç kare, gerçek hız ne olursa olsun yapay olarak düşük
    görünür (overlay videoda "araç 25 km/h ile giriyor, sonra 65'e sıçrıyor" gibi — track
    hızı sabit 65 olsa bile, bkz. DECISIONS.md).
    """
    if not samples:
        return []

    times = np.array([s.t_s for s in samples])
    speeds = np.array([s.speed_kmh for s in samples])
    valid = np.ones(len(samples), dtype=bool)
    if len(samples) > 1:
        valid[0] = False  # ilk örnek: gerçek ölçüm değil, yalnızca yer tutucu
    half = window_s / 2.0
    result: list[tuple[float, float]] = []

    for i, s in enumerate(samples):
        t = s.t_s
        mask = (times >= t - half) & (times <= t + half) & valid
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
