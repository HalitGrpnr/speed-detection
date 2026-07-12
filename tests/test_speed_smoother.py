"""Acceptance tests for M3 — sliding window smoother."""
from __future__ import annotations

import numpy as np
import pytest

from src.speed.models import SpeedSample
from src.speed.smoother import sliding_window_smooth


def _make_samples(speeds: list[float], fps: float = 25.0) -> list[SpeedSample]:
    return [
        SpeedSample(frame=i, t_s=i / fps, world_m=(float(i), 0.0), speed_kmh=v)
        for i, v in enumerate(speeds)
    ]


# ── Test 4: Yumuşatma gürültüyü azaltır ──────────────────────────────────────

def test_smoothing_reduces_variance_median():
    rng = np.random.default_rng(42)
    base = 60.0
    noisy_speeds = [base + rng.normal(0, 10) for _ in range(60)]
    samples = _make_samples(noisy_speeds)

    smoothed = sliding_window_smooth(samples, window_s=0.4, method="median")
    raw_std = float(np.std(noisy_speeds))
    sm_std = float(np.std([v for _, v in smoothed]))
    assert sm_std < raw_std, f"Yumuşatma std'yi azaltmadı: {raw_std:.2f} → {sm_std:.2f}"


def test_smoothing_reduces_variance_mean():
    rng = np.random.default_rng(1)
    noisy_speeds = [80.0 + rng.normal(0, 15) for _ in range(60)]
    samples = _make_samples(noisy_speeds)

    smoothed = sliding_window_smooth(samples, window_s=0.4, method="mean")
    assert np.std([v for _, v in smoothed]) < np.std(noisy_speeds)


def test_smoothing_reduces_variance_regression():
    rng = np.random.default_rng(2)
    noisy_speeds = [70.0 + rng.normal(0, 12) for _ in range(60)]
    samples = _make_samples(noisy_speeds)

    smoothed = sliding_window_smooth(samples, window_s=0.4, method="regression")
    assert np.std([v for _, v in smoothed]) < np.std(noisy_speeds)


# ── Test 5: Üç method tutarlı ────────────────────────────────────────────────

def test_three_methods_agree_within_5kmh():
    rng = np.random.default_rng(7)
    speeds = [60.0 + rng.normal(0, 5) for _ in range(50)]
    samples = _make_samples(speeds)

    sm_med = np.median([v for _, v in sliding_window_smooth(samples, 0.4, "median")])
    sm_mean = np.median([v for _, v in sliding_window_smooth(samples, 0.4, "mean")])
    sm_reg = np.median([v for _, v in sliding_window_smooth(samples, 0.4, "regression")])

    assert abs(sm_med - sm_mean) < 5.0, f"median vs mean: {sm_med:.1f} vs {sm_mean:.1f}"
    assert abs(sm_med - sm_reg) < 5.0, f"median vs regression: {sm_med:.1f} vs {sm_reg:.1f}"


# ── Uzunluk korunumu ──────────────────────────────────────────────────────────

def test_output_length_matches_input():
    samples = _make_samples([50.0] * 30)
    for method in ("median", "mean", "regression"):
        result = sliding_window_smooth(samples, 0.4, method)
        assert len(result) == 30, f"{method}: uzunluk {len(result)} != 30"


def test_empty_input():
    assert sliding_window_smooth([], 0.4) == []


def test_single_sample():
    samples = _make_samples([55.0])
    result = sliding_window_smooth(samples, 0.4)
    assert len(result) == 1
    assert result[0][1] == pytest.approx(55.0)


# ── Negatif hız olamaz ───────────────────────────────────────────────────────

def test_no_negative_speeds():
    # Sıfır civarı gürültülü seri — bazı ham değerler negatif gelebilir
    samples = _make_samples([0.5, -1.0, 0.2, -0.5, 0.1])
    for method in ("median", "mean", "regression"):
        result = sliding_window_smooth(samples, 0.4, method)
        for _, v in result:
            assert v >= 0.0, f"{method}: negatif smoothed hız {v}"


# ── Büyük pencere → daha fazla yumuşatma ────────────────────────────────────

def test_larger_window_smoother():
    rng = np.random.default_rng(99)
    speeds = [60.0 + rng.normal(0, 20) for _ in range(100)]
    samples = _make_samples(speeds)

    sm_small = [v for _, v in sliding_window_smooth(samples, 0.1, "mean")]
    sm_large = [v for _, v in sliding_window_smooth(samples, 1.0, "mean")]
    assert np.std(sm_large) < np.std(sm_small)


# ── t_s zamanları korunuyor ───────────────────────────────────────────────────

def test_output_times_match_input():
    samples = _make_samples([60.0] * 20)
    result = sliding_window_smooth(samples, 0.4)
    for s, (t, _) in zip(samples, result):
        assert t == pytest.approx(s.t_s)


# ── Bilinmeyen method → ValueError ───────────────────────────────────────────

def test_unknown_method_raises():
    samples = _make_samples([60.0] * 5)
    with pytest.raises(ValueError, match="Bilinmeyen method"):
        sliding_window_smooth(samples, 0.4, method="invalid")  # type: ignore


# ── Regresyon: ilk örneğin yapay 0.0'ı pencereyi kirletmemeli ────────────────
# track_to_world ilk noktaya her zaman speed_kmh=0.0 verir (önceki nokta yok — gerçek
# bir ölçüm değil). Araç track'e sabit hızla girse bile bu yapay değer, düşük
# örnek yoğunluğunda (ör. yüksek frame_step) medyanı/ortalamayı aşağı çekip
# overlay videoda "araç 25 km/h ile giriyor, sonra 65'e sıçrıyor" izlenimi verirdi.

def test_synthetic_first_zero_does_not_drag_down_median():
    """Track sabit 65 km/h ile başlasa bile ilk örneğin yapay 0.0'ı medyanı bozmamalı."""
    fps = 20.0
    frame_step = 3
    samples = [
        SpeedSample(frame=i * frame_step, t_s=(i * frame_step) / fps,
                    world_m=(float(i), 0.0), speed_kmh=0.0 if i == 0 else 65.0)
        for i in range(10)
    ]
    smoothed = sliding_window_smooth(samples, window_s=0.4, method="median")
    assert smoothed[0][1] == pytest.approx(65.0), (
        f"İlk örnek yapay 0.0'dan etkilendi: {smoothed[0][1]}"
    )


def test_synthetic_first_zero_does_not_drag_down_mean():
    fps = 20.0
    frame_step = 3
    samples = [
        SpeedSample(frame=i * frame_step, t_s=(i * frame_step) / fps,
                    world_m=(float(i), 0.0), speed_kmh=0.0 if i == 0 else 65.0)
        for i in range(10)
    ]
    smoothed = sliding_window_smooth(samples, window_s=0.4, method="mean")
    assert smoothed[0][1] == pytest.approx(65.0)


def test_single_sample_track_still_uses_own_value():
    """Track'te tek nokta varsa (yalnızca yapay 0.0) maskeleme sonucu boş pencereye
    düşülmemeli — kendi ham değeri kullanılmalı."""
    samples = [SpeedSample(frame=0, t_s=0.0, world_m=(0.0, 0.0), speed_kmh=0.0)]
    smoothed = sliding_window_smooth(samples, window_s=0.4, method="median")
    assert smoothed == [(0.0, 0.0)]
