"""T28 Faz 3 — cross-ratio ölçüm servisi: CI bileşenleri, VP yayılımı, kalite kapıları."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.vp_sources import vanishing_from_lines, vanishing_from_trajectories
from src.speed.cross_ratio_service import (
    ContactMark,
    KnownLength,
    measure_cross_ratio,
    select_vp,
)
from tests.test_cross_ratio import _camera
from tests.test_vp_sources import _body_trajectories, _lane_lines

FPS = 25.0
WB = 2.65


def _setup(speed=80.0, n=10, noise=0.0, lane_noise=0.5, seed=0, step=2, y0=12.0):
    project, vanishing = _camera(15.0, 20.0)
    rng = np.random.default_rng(seed)
    frames = np.arange(n) * step
    ys = y0 + speed / 3.6 * frames / FPS
    pts = project(np.column_stack([np.full(n, 3.0), ys, np.zeros(n)]))
    pts = pts + rng.normal(0, noise, pts.shape) if noise else pts
    rear, front = project([3.0, ys[0], 0])[0], project([3.0, ys[0] + WB, 0])[0]
    lanes = [l + rng.normal(0, lane_noise, l.shape) for l in _lane_lines(project)]
    lane = vanishing_from_lines(lanes, pixel_sigma=max(lane_noise, 0.1))
    marks = [ContactMark(frame=float(f), pixel=(float(p[0]), float(p[1]))) for f, p in zip(frames, pts)]
    kl = KnownLength("wheelbase", WB, tuple(rear), tuple(front), sigma_m=0.01, frame=0)
    return project, lane, marks, kl


def test_speed_and_ci_components():
    _, lane, marks, kl = _setup(noise=0.5)
    m = measure_cross_ratio(lane, kl, marks, FPS, pixel_sigma=0.5)
    assert m.speed_kmh == pytest.approx(80.0, rel=0.02)
    c = m.ci_components_kmh
    assert c["fit"] > 0 and c["vp"] > 0 and c["length"] > 0
    assert m.ci_kmh == pytest.approx(np.sqrt(c["fit"]**2 + c["vp"]**2 + c["length"]**2), abs=0.06)
    assert abs(m.speed_kmh - 80.0) <= m.ci_kmh
    assert m.vp_mc_samples == 400 and m.vp_mc_invalid_fraction == 0.0


def test_reproducible_with_fixed_seed():
    _, lane, marks, kl = _setup(noise=0.5)
    a = measure_cross_ratio(lane, kl, marks, FPS)
    b = measure_cross_ratio(lane, kl, marks, FPS)
    assert a.ci_kmh == b.ci_kmh and a.ci_components_kmh == b.ci_components_kmh


def test_vp_uncertainty_grows_with_lane_noise():
    _, lane_good, marks, kl = _setup(lane_noise=0.3)
    _, lane_bad, _, _ = _setup(lane_noise=4.0)
    good = measure_cross_ratio(lane_good, kl, marks, FPS)
    bad = measure_cross_ratio(lane_bad, kl, marks, FPS)
    assert bad.ci_components_kmh["vp"] > good.ci_components_kmh["vp"]


def test_clean_measurement_high_confidence_no_warnings():
    _, lane, marks, kl = _setup(lane_noise=0.2)
    m = measure_cross_ratio(lane, kl, marks, FPS)
    assert m.confidence_level == "high", [g.code for g in m.gates]
    assert not [g for g in m.gates if g.severity != "info"]


def test_default_length_sigma_reported():
    _, lane, marks, kl = _setup()
    kl = KnownLength("wheelbase", WB, kl.point_a, kl.point_b)
    m = measure_cross_ratio(lane, kl, marks, FPS)
    assert m.length_sigma_m == 0.05
    assert any(g.code == "length_sigma_default" for g in m.gates)


def test_far_marks_gate():
    _, lane, marks, kl = _setup(n=12, step=6, y0=12.0)  # araç ~40 m'den fazla uzaklaşıyor
    m = measure_cross_ratio(lane, kl, marks, FPS)
    assert any(g.code == "far_marks" for g in m.gates)
    assert m.confidence_level != "high"


def test_not_straight_gate():
    _, lane, marks, kl = _setup()
    bent = marks[:-3] + [ContactMark(mk.frame, (mk.pixel[0] + 30, mk.pixel[1])) for mk in marks[-3:]]
    m = measure_cross_ratio(lane, kl, bent, FPS)
    g = next(g for g in m.gates if g.code == "not_straight")
    assert g.action  # operatöre ne yapacağını söylüyor


def test_scene_distance_off_line_gate():
    project, lane, marks, _ = _setup()
    # Mesafe karşı şeritte işaretlenmiş (X=-1.75) — aracın izinde değil
    a, b = project([-1.75, 12.0, 0])[0], project([-1.75, 22.0, 0])[0]
    kl = KnownLength("scene", 10.0, tuple(a), tuple(b), sigma_m=0.02)
    m = measure_cross_ratio(lane, kl, marks, FPS)
    g = next(g for g in m.gates if g.code == "ref_off_line")
    assert "aracın geçtiği" in g.message


def test_auto_marks_and_two_marks_gates():
    _, lane, marks, kl = _setup(n=2)
    marks = [marks[0], ContactMark(marks[1].frame, marks[1].pixel, source="auto")]
    m = measure_cross_ratio(lane, kl, marks, FPS)
    codes = {g.code for g in m.gates}
    assert {"too_few_marks", "auto_marks_unconfirmed"} <= codes
    assert m.confidence_level != "high"


def test_fps_gates():
    _, lane, marks, kl = _setup()
    assert any(g.code == "fps_suspicious" for g in measure_cross_ratio(lane, kl, marks, 27.3).gates)
    assert not any(g.code.startswith("fps") for g in measure_cross_ratio(lane, kl, marks, 29.97).gates)
    ov = measure_cross_ratio(lane, kl, marks, 30.0, fps_source="operator_override")
    assert any(g.code == "fps_override" for g in ov.gates)


def test_lane_and_trajectory_agreement_gate():
    project, lane, marks, kl = _setup()
    traj = vanishing_from_trajectories(_body_trajectories(project))
    used, alt = select_vp(lane, traj, prefer="lane")
    m = measure_cross_ratio(used, kl, marks, FPS, vp_alternative=alt)
    assert m.agreement is not None and m.agreement.status == "agree"
    assert any(g.code == "vp_agree" for g in m.gates)


def test_disagreeing_vp_lowers_confidence():
    project, lane, marks, kl = _setup(lane_noise=0.2)
    wrong = vanishing_from_lines([l + [60.0, 0.0] * np.linspace(0, 1, len(l))[:, None]
                                  for l in _lane_lines(project)])
    m = measure_cross_ratio(lane, kl, marks, FPS, vp_alternative=wrong)
    assert any(g.code == "vp_disagree" and g.severity == "warn" for g in m.gates)
    assert m.confidence_level != "high"


def test_infinite_vp_gate():
    rear, front = np.array([100.0, 500.0]), np.array([300.0, 520.0])
    d = (front - rear) / np.linalg.norm(front - rear)
    pts = rear + np.outer(np.linspace(0, 400, 6), d)
    par = vanishing_from_lines([[rear + [0, k], front + [0, k]] for k in (-60, 0, 60)])
    assert par.point is None
    marks = [ContactMark(float(i * 3), tuple(p)) for i, p in enumerate(pts)]
    m = measure_cross_ratio(par, KnownLength("wheelbase", WB, tuple(rear), tuple(front), 0.01), marks, FPS)
    assert any(g.code == "vp_infinite" for g in m.gates)
    assert m.ci_components_kmh["vp"] == 0.0


def test_select_vp():
    project, lane, _, _ = _setup()
    traj = vanishing_from_trajectories(_body_trajectories(project))
    assert select_vp(lane, None) == (lane, None)
    assert select_vp(None, traj) == (traj, None)
    assert select_vp(lane, traj, prefer="trajectory") == (traj, lane)
    with pytest.raises(ValueError):
        select_vp(None, None)
