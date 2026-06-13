"""Acceptance tests for M3 — speed calculator."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.homography import pixel_to_world
from src.calibration.models import CalibrationResult
from src.detection.models import Track, TrackPoint
from src.speed.calculator import track_to_world, estimate_speed


# ── Synthetic track helpers ───────────────────────────────────────────────────

def _make_H() -> np.ndarray:
    return np.array([
        [0.05,  0.001, -10.0],
        [0.001, 0.05,  -5.0],
        [0.0,   0.0,    1.0],
    ], dtype=np.float64)


def _make_cal_result(
    layer: str = "operator",
    rms: float = 0.05,
    planarity: bool = False,
) -> CalibrationResult:
    return CalibrationResult(
        homography=_make_H(),
        used_point_ids=[],
        excluded_point_ids=[],
        reprojection_rms_m=rms,
        confidence_layer=layer,
        planarity_warning=planarity,
    )


def _world_to_pixel(H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
    return pixel_to_world(np.linalg.inv(H), world)


def _make_constant_speed_track(
    H: np.ndarray,
    speed_kmh: float,
    fps: float,
    n_frames: int,
    frame_step: int = 1,
    track_id: int = 1,
) -> Track:
    """Sabit hızda hareket eden sentetik track (X ekseninde)."""
    speed_ms = speed_kmh / 3.6
    step_m = speed_ms * frame_step / fps
    points = []
    for i in range(n_frames):
        frame = i * frame_step
        world = (i * step_m, 5.0)
        pix = _world_to_pixel(H, world)
        tp = TrackPoint(
            frame=frame,
            t_s=frame / fps,
            contact_pixel=pix,
            bbox=(pix[0] - 50, pix[1] - 40, pix[0] + 50, pix[1]),
        )
        points.append(tp)
    return Track(track_id=track_id, vehicle_class="car", points=points)


# ── Test 1: Sabit hız doğruluğu ──────────────────────────────────────────────

def test_estimate_speed_constant_60kmh():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=60.0, fps=25.0, n_frames=30)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert abs(est.value_kmh - 60.0) < 1.0, (
        f"Beklenen ~60 km/h, alınan {est.value_kmh:.2f} km/h"
    )


def test_estimate_speed_constant_100kmh():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=100.0, fps=25.0, n_frames=30)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert abs(est.value_kmh - 100.0) < 1.0


# ── Test 2: Ham seri doğruluğu ────────────────────────────────────────────────

def test_track_to_world_speed_values():
    H = _make_H()
    speed_kmh = 72.0
    fps = 25.0
    track = _make_constant_speed_track(H, speed_kmh=speed_kmh, fps=fps, n_frames=20)
    samples = track_to_world(track, H, fps)

    # İlk nokta 0.0 olmalı
    assert samples[0].speed_kmh == 0.0

    # Geri kalan noktalar beklenen hıza yakın olmalı
    speeds = [s.speed_kmh for s in samples[1:]]
    for v in speeds:
        assert abs(v - speed_kmh) < 0.5, f"Beklenen ~{speed_kmh}, alınan {v:.2f}"


def test_track_to_world_world_positions():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=50.0, fps=25.0, n_frames=10)
    samples = track_to_world(track, H, 25.0)

    for i, s in enumerate(samples):
        speed_ms = 50.0 / 3.6
        expected_x = i * speed_ms / 25.0
        assert abs(s.world_m[0] - expected_x) < 0.01


# ── Test 3: Δt = Δframe/fps (frame_step hatası önlemi) ───────────────────────

def test_delta_t_uses_frame_difference_not_fps():
    """frame_step=3 ile oluşturulan track'te Δt = 3/fps olmalı; 1/fps kullanılsaydı 3x hatalı."""
    H = _make_H()
    fps = 25.0
    speed_kmh = 60.0
    # frame_step=3: her 3 karede bir nokta var
    track = _make_constant_speed_track(H, speed_kmh=speed_kmh, fps=fps,
                                        n_frames=15, frame_step=3)

    # Frame farkları: 0,3,6,... → Δframe=3
    samples = track_to_world(track, H, fps)
    speeds = [s.speed_kmh for s in samples[1:]]

    for v in speeds:
        # Doğru Δt=3/25 → doğru hız. Yanlış Δt=1/25 → hız 3x büyük (180 km/h)
        assert abs(v - speed_kmh) < 1.0, (
            f"Δt yanlış hesaplanıyor olabilir: beklenen ~{speed_kmh}, alınan {v:.1f}"
        )


# ── Test 6: Duran araç ≈ 0 km/h ─────────────────────────────────────────────

def test_stationary_vehicle_near_zero():
    H = _make_H()
    pix = _world_to_pixel(H, (5.0, 5.0))
    points = [
        TrackPoint(frame=i, t_s=i/25.0, contact_pixel=pix,
                   bbox=(pix[0]-50, pix[1]-40, pix[0]+50, pix[1]))
        for i in range(25)
    ]
    track = Track(track_id=1, vehicle_class="car", points=points)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert est.value_kmh < 1.0, f"Duran araç için hız {est.value_kmh:.2f} km/h — sıfır olmalı"


# ── Test 7: Kısa track güven seviyesi ────────────────────────────────────────

def test_short_track_low_confidence():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=50.0, fps=25.0, n_frames=3)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert est.track_quality.frame_count == 3
    assert est.confidence_level == "low"


def test_long_track_no_occlusion_medium_confidence():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=50.0, fps=25.0, n_frames=25)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert est.confidence_level == "medium"


# ── Test 8: Oklüzyon bayrağı ──────────────────────────────────────────────────

def test_occlusion_flag_propagated():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=60.0, fps=25.0, n_frames=25)
    track.occlusion_gaps = [(10, 13)]
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert est.track_quality.has_occlusion is True


def test_no_occlusion_flag():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=60.0, fps=25.0, n_frames=25)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert est.track_quality.has_occlusion is False


# ── Test 9: CI hesaplanabilir ────────────────────────────────────────────────

def test_ci_nonnegative():
    H = _make_H()
    track = _make_constant_speed_track(H, speed_kmh=60.0, fps=25.0, n_frames=30)
    est = estimate_speed(track, H, fps=25.0, calibration_result=_make_cal_result())
    assert est.ci_kmh >= 0.0


def test_noisy_track_larger_ci():
    """Gürültülü track daha büyük CI üretmeli."""
    H = _make_H()
    rng = np.random.default_rng(0)
    fps = 25.0
    speed_ms = 60.0 / 3.6

    clean_track = _make_constant_speed_track(H, 60.0, fps, 40)

    # Gürültülü: temas noktalarına piksel gürültüsü ekle
    noisy_points = []
    for tp in clean_track.points:
        noise = rng.normal(0, 2.0, 2)
        noisy_pix = (tp.contact_pixel[0] + noise[0], tp.contact_pixel[1] + noise[1])
        noisy_points.append(TrackPoint(
            frame=tp.frame, t_s=tp.t_s,
            contact_pixel=noisy_pix, bbox=tp.bbox,
        ))
    noisy_track = Track(track_id=2, vehicle_class="car", points=noisy_points)

    cal = _make_cal_result()
    est_clean = estimate_speed(clean_track, H, fps, calibration_result=cal)
    est_noisy = estimate_speed(noisy_track, H, fps, calibration_result=cal)

    assert est_noisy.ci_kmh >= est_clean.ci_kmh, (
        "Gürültülü track CI'ı temiz track'ten küçük olamaz"
    )
