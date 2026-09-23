"""T28 Faz 1 — cross-ratio çekirdeği: sentetik pinhole kamerayla bilinen hızı geri üretme."""
from __future__ import annotations

import numpy as np
import pytest

from src.speed.cross_ratio import (
    cross_ratio_speed,
    fit_line_direction,
    line_scale_from_vp,
)

FPS = 25.0
WHEELBASE = 2.65


def _camera(yaw_deg: float, pitch_deg: float, height: float = 6.0, f: float = 1000.0):
    """Yol düzlemi Z=0; kamera (0, 0, h) konumunda, yaw/pitch ile bakıyor. P → piksel."""
    K = np.array([[f, 0, 960], [0, f, 540], [0, 0, 1.0]])
    yaw, pitch = np.radians(yaw_deg), np.radians(pitch_deg)
    # Kamera ekseni: x sağ, y aşağı, z ileri. Önce dünya→kamera (yaw=0, pitch=0: +Y'ye bakar).
    base = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)
    Rz = np.array([[np.cos(yaw), np.sin(yaw), 0], [-np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
    R = Rx @ base @ Rz
    C = np.array([0.0, 0.0, height])

    def project(P):
        P = np.atleast_2d(np.asarray(P, dtype=float))
        pc = (R @ (P - C).T)
        uv = K @ pc
        return (uv[:2] / uv[2]).T

    def vanishing(direction):
        v = K @ R @ np.asarray(direction, dtype=float)
        return None if abs(v[2]) < 1e-12 else (v[0] / v[2], v[1] / v[2])

    return project, vanishing


def _scenario(speed_kmh=80.0, yaw=15.0, pitch=20.0, lateral=3.0, y0=15.0, n=12, away=True):
    """Arka tekerlek teması, düz bir yol doğrusu (X=lateral) boyunca sabit hızla gider."""
    project, vanishing = _camera(yaw, pitch)
    v = speed_kmh / 3.6 * (1 if away else -1)
    frames = np.arange(n, dtype=float) * 2  # her 2 karede bir işaret
    ys = y0 + v * frames / FPS
    contacts = project(np.column_stack([np.full(n, lateral), ys, np.zeros(n)]))
    rear0 = project([lateral, ys[0], 0])[0]
    front0 = project([lateral, ys[0] + WHEELBASE, 0])[0]
    vp = vanishing([0, 1, 0])
    return vp, rear0, front0, frames, contacts


def test_noise_free_recovers_speed_exactly():
    vp, rear, front, frames, pts = _scenario()
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE, line_points=pts)
    res = cross_ratio_speed(scale, frames, pts, FPS)
    assert res.speed_kmh == pytest.approx(80.0, rel=1e-4)
    assert res.max_offset_px < 1e-6
    assert res.direction == "toward_ref_b"
    assert res.positions_m[0] == pytest.approx(0.0, abs=1e-6)


def test_positions_match_ground_truth():
    vp, rear, front, frames, pts = _scenario(speed_kmh=50.0)
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE)
    x = scale.position_m(pts)
    expected = 50.0 / 3.6 * frames / FPS
    np.testing.assert_allclose(x, expected, atol=1e-6)


@pytest.mark.parametrize("speed", [30.0, 82.0, 130.0])
@pytest.mark.parametrize("away", [True, False])
def test_noisy_marks_within_two_percent(speed, away):
    y0 = 15.0 if away else 15.0 + speed / 3.6 * 24 / FPS
    vp, rear, front, frames, pts = _scenario(speed_kmh=speed, away=away, y0=y0)
    rng = np.random.default_rng(42)
    noisy = pts + rng.normal(0, 0.5, pts.shape)
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE, line_points=noisy)
    res = cross_ratio_speed(scale, frames, noisy, FPS, pixel_sigma=0.5)
    assert res.speed_kmh == pytest.approx(speed, rel=0.02)
    assert res.ci_kmh > 0
    # Gerçek değer %95 CI içinde (seed sabit)
    assert abs(res.speed_kmh - speed) <= res.ci_kmh
    assert res.direction == ("toward_ref_b" if away else "toward_ref_a")


def test_vanishing_at_infinity_reduces_to_linear_ratio():
    # Yol görüntü düzlemine paralel: kamera +Y'ye bakar, araç X ekseninde gider → VP yok.
    project, vanishing = _camera(yaw_deg=0.0, pitch_deg=20.0)
    assert vanishing([1, 0, 0]) is None
    v = 60.0 / 3.6
    frames = np.arange(8, dtype=float)
    xs = -5 + v * frames / FPS
    pts = project(np.column_stack([xs, np.full(8, 20.0), np.zeros(8)]))
    rear, front = project([-5, 20, 0])[0], project([-5 + WHEELBASE, 20, 0])[0]
    scale = line_scale_from_vp(None, rear, front, WHEELBASE, line_points=pts)
    res = cross_ratio_speed(scale, frames, pts, FPS)
    assert res.speed_kmh == pytest.approx(60.0, rel=1e-6)


def test_far_vp_converges_to_parallel_branch():
    # Aynı noktalar: VP çok uzakta verilirse sonuç vp=None ile örtüşmeli (yumuşak bozulma).
    rear, front = np.array([100.0, 500.0]), np.array([300.0, 520.0])
    d = (front - rear) / np.linalg.norm(front - rear)
    pts = rear + np.outer(np.linspace(0, 400, 6), d)
    frames = np.arange(6) * 3.0
    par = line_scale_from_vp(None, rear, front, WHEELBASE).position_m(pts)
    errs = []
    for dist in (1e5, 1e6, 1e7, 1e9):
        vp = rear - d * dist  # doğru üzerinde, noktaların gerisinde
        far = line_scale_from_vp(vp, rear, front, WHEELBASE).position_m(pts)
        errs.append(np.max(np.abs(far - par)))
    # Sapma ~ (nokta açıklığı / VP uzaklığı) ile sıfıra iner — çökme yok, yumuşak bozulma.
    assert all(a > b for a, b in zip(errs, errs[1:]))
    assert errs[-1] < 1e-5
    s_par = cross_ratio_speed(line_scale_from_vp(None, rear, front, WHEELBASE), frames, pts, FPS)
    s_far = cross_ratio_speed(line_scale_from_vp(rear - d * 1e9, rear, front, WHEELBASE), frames, pts, FPS)
    assert s_far.speed_kmh == pytest.approx(s_par.speed_kmh, rel=1e-6)


def test_scene_distance_as_known_length():
    # Bilinen uzunluk olarak olay yeri mesafesi (10 m, yol üzerinde iki işaret) — aynı doğru.
    project, vanishing = _camera(15.0, 20.0)
    vp = vanishing([0, 1, 0])
    a, b = project([3.0, 12.0, 0])[0], project([3.0, 22.0, 0])[0]
    frames = np.arange(10, dtype=float)
    ys = 14 + 70 / 3.6 * frames / FPS
    pts = project(np.column_stack([np.full(10, 3.0), ys, np.zeros(10)]))
    res = cross_ratio_speed(line_scale_from_vp(vp, a, b, 10.0), frames, pts, FPS)
    assert res.speed_kmh == pytest.approx(70.0, rel=1e-4)


def test_length_uncertainty_widens_ci():
    vp, rear, front, frames, pts = _scenario()
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE)
    base = cross_ratio_speed(scale, frames, pts, FPS)
    wide = cross_ratio_speed(scale, frames, pts, FPS, length_sigma_m=0.1)
    assert wide.ci_kmh > base.ci_kmh
    # %95: 1.96 · (0.1/2.65) · 80 ≈ 5.9 km/h baskın terim
    assert wide.ci_kmh == pytest.approx(1.96 * 0.1 / WHEELBASE * 80.0, rel=0.1)


def test_off_line_points_warn_and_lower_confidence():
    vp, rear, front, frames, pts = _scenario()
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE)
    bent = pts.copy()
    bent[-4:, 0] += 25.0  # araç sonda şerit değiştiriyor
    res = cross_ratio_speed(scale, frames, bent, FPS)
    assert res.max_offset_px > 4.0
    assert any("düz" in w for w in res.warnings)
    assert res.confidence_level != "high"


def test_clean_many_points_is_high_confidence():
    vp, rear, front, frames, pts = _scenario()
    res = cross_ratio_speed(line_scale_from_vp(vp, rear, front, WHEELBASE), frames, pts, FPS)
    assert res.confidence_level == "high"
    assert res.warnings == []


def test_two_points_warns():
    vp, rear, front, frames, pts = _scenario(n=2)
    res = cross_ratio_speed(line_scale_from_vp(vp, rear, front, WHEELBASE), frames, pts, FPS)
    assert res.n_points == 2
    assert res.ci_kmh > 0
    assert any("2 kare" in w for w in res.warnings)


def test_far_points_are_more_sensitive():
    vp, rear, front, frames, pts = _scenario()
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE)
    sens = scale.position_sensitivity_m_per_px(pts)
    assert np.all(np.diff(sens) > 0)  # araç uzaklaştıkça 1 px daha çok metre


def test_invalid_inputs():
    vp, rear, front, frames, pts = _scenario()
    with pytest.raises(ValueError):
        line_scale_from_vp(vp, rear, rear, WHEELBASE)
    with pytest.raises(ValueError):
        line_scale_from_vp(vp, rear, front, 0.0)
    scale = line_scale_from_vp(vp, rear, front, WHEELBASE)
    with pytest.raises(ValueError):
        cross_ratio_speed(scale, frames[:1], pts[:1], FPS)
    with pytest.raises(ValueError):
        cross_ratio_speed(scale, [0, 0], pts[:2], FPS)
    with pytest.raises(ValueError):
        cross_ratio_speed(scale, frames, pts, 0.0)
    beyond = np.array(vp) - (np.array(rear) - np.array(vp))  # VP'nin öbür tarafı
    with pytest.raises(ValueError):
        cross_ratio_speed(scale, [0, 1], [rear, beyond], FPS)


def test_fit_line_direction_points_away_from_vp():
    d = fit_line_direction([[10, 10], [20, 20]], vp=(0, 0))
    np.testing.assert_allclose(d, np.array([1, 1]) / np.sqrt(2))
