"""T28 Faz 2 — VP sağlayıcıları (şerit + araç izi), ortak arayüz ve uyum kontrolü."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.calibration.vp_sources import (
    compare_vanishing,
    fit_line,
    vanishing_from_lane_detection,
    vanishing_from_lines,
    vanishing_from_trajectories,
)
from src.detection.feature_tracks import track_features_in_box
from src.speed.cross_ratio import cross_ratio_speed, line_scale_from_vp
from tests.test_cross_ratio import _camera

FPS = 25.0


def _lane_lines(project, xs=(-1.75, 1.75, 5.25), y_range=(8.0, 40.0)):
    return [project([[x, y_range[0], 0], [x, y_range[1], 0]]) for x in xs]


def _body_trajectories(project, n_frames=12, speed_kmh=70.0, y0=14.0):
    """Araç üzerindeki rijit noktalar (farklı yükseklik/yanal konum) — hepsi +Y'de öteleniyor."""
    offsets = [(-0.8, 0.0, 0.3), (0.8, 0.0, 0.3), (-0.7, 0.0, 1.0), (0.7, 0.0, 1.0),
               (0.0, 0.0, 1.4), (-0.6, 3.5, 0.8), (0.6, 3.5, 0.8), (0.0, 4.2, 0.5)]
    ys = y0 + speed_kmh / 3.6 * np.arange(n_frames) / FPS
    trajs = []
    for ox, oy, oz in offsets:
        P = np.column_stack([np.full(n_frames, 3.0 + ox), ys + oy, np.full(n_frames, oz)])
        trajs.append(project(P))
    return trajs


# ── Doğru uydurma ─────────────────────────────────────────────────────────────

def test_fit_line_exact_points():
    line = fit_line([[0, 0], [10, 10], [20, 20]])
    assert line.rms_px == pytest.approx(0.0, abs=1e-9)
    assert line.distance_to([10, 0]) == pytest.approx(10 / np.sqrt(2))
    assert line.sigma_at([100, 100]) > line.sigma_at([10, 10])  # uzaklaştıkça belirsizlik artar


# ── Şerit (elle) ──────────────────────────────────────────────────────────────

def test_manual_lanes_recover_analytic_vp():
    project, vanishing = _camera(15.0, 20.0)
    truth = np.array(vanishing([0, 1, 0]))
    est = vanishing_from_lines(_lane_lines(project))
    assert est.source == "lane_manual"
    assert est.n_inliers == 3
    np.testing.assert_allclose(est.point, truth, atol=1e-6)
    assert est.covariance is not None


def test_noisy_lanes_truth_within_uncertainty():
    project, vanishing = _camera(15.0, 20.0)
    truth = np.array(vanishing([0, 1, 0]))
    rng = np.random.default_rng(1)
    lines = []
    for x in (-1.75, 1.75, 5.25, 8.75):
        pts = project(np.column_stack([np.full(6, x), np.linspace(8, 40, 6), np.zeros(6)]))
        lines.append(pts + rng.normal(0, 1.0, pts.shape))
    est = vanishing_from_lines(lines)
    diff = np.asarray(est.point) - truth
    m2 = float(diff @ np.linalg.solve(np.asarray(est.covariance), diff))
    assert m2 < 13.8  # χ²(2) %99.9
    assert est.sigma_px[0] > est.sigma_px[1] > 0


def test_two_lines_warn_about_consistency():
    project, _ = _camera(15.0, 20.0)
    est = vanishing_from_lines(_lane_lines(project, xs=(-1.75, 1.75)))
    assert any("Yalnızca 2 çizgi" in w for w in est.warnings)


def test_parallel_lines_give_infinite_vp():
    est = vanishing_from_lines([[[0, 0], [100, 50]], [[0, 30], [100, 80]], [[0, 90], [100, 140]]])
    assert est.at_infinity
    d = np.asarray(est.direction)
    assert abs(d[1] / d[0]) == pytest.approx(0.5, rel=1e-6)
    assert any("paralel" in w for w in est.warnings)


def test_needs_two_lines():
    with pytest.raises(ValueError):
        vanishing_from_lines([[[0, 0], [1, 1]]])


# ── Şerit (otomatik) ──────────────────────────────────────────────────────────

def test_lane_detection_wrapper_marks_as_suggestion():
    img = np.zeros((720, 960, 3), np.uint8)
    vp = (480, 180)
    for x_bot in (160, 800):
        cv2.line(img, (x_bot, 719), vp, (255, 255, 255), 6)
    est = vanishing_from_lane_detection(img)
    assert est is not None and est.source == "lane_auto"
    assert np.linalg.norm(np.asarray(est.point) - vp) < 15
    assert any("onaylayın" in w for w in est.warnings)


def test_lane_detection_blank_returns_none():
    assert vanishing_from_lane_detection(np.zeros((480, 640, 3), np.uint8)) is None


# ── Araç izi ──────────────────────────────────────────────────────────────────

def test_body_trajectories_converge_at_road_vp():
    project, vanishing = _camera(15.0, 20.0)
    truth = np.array(vanishing([0, 1, 0]))
    est = vanishing_from_trajectories(_body_trajectories(project))
    assert est.source == "trajectory"
    np.testing.assert_allclose(est.point, truth, atol=1e-4)


def test_trajectory_outliers_rejected():
    project, vanishing = _camera(15.0, 20.0)
    truth = np.array(vanishing([0, 1, 0]))
    rng = np.random.default_rng(3)
    trajs = [t + rng.normal(0, 0.3, t.shape) for t in _body_trajectories(project)]
    # Aykırı: düz ama yanlış yöne giden iki iz (ör. yansıma / komşu araç)
    trajs.append(np.column_stack([np.linspace(100, 400, 12), np.linspace(900, 850, 12)]))
    trajs.append(np.column_stack([np.linspace(1500, 1300, 12), np.linspace(300, 700, 12)]))
    est = vanishing_from_trajectories(trajs, pixel_sigma=0.3)
    assert est.n_inliers == 8 and est.n_lines == 10
    assert any("elendi" in w for w in est.warnings)
    assert np.linalg.norm(np.asarray(est.point) - truth) < 3 * est.sigma_px[0] + 1.0


def test_curved_trajectories_flagged():
    project, _ = _camera(15.0, 20.0)
    trajs = _body_trajectories(project)
    t = np.linspace(0, np.pi, 12)
    trajs.append(np.column_stack([500 + 200 * np.cos(t), 600 + 200 * np.sin(t)]))  # dönen araç
    est = vanishing_from_trajectories(trajs)
    assert any("doğruya oturmuyor" in w for w in est.warnings)


def test_single_trajectory_cannot_define_vp():
    project, _ = _camera(15.0, 20.0)
    with pytest.raises(ValueError, match="en az 2"):
        vanishing_from_trajectories(_body_trajectories(project)[:1])


# ── Uyum kontrolü ─────────────────────────────────────────────────────────────

def test_lane_and_trajectory_agree():
    project, _ = _camera(15.0, 20.0)
    rng = np.random.default_rng(5)
    lanes = [l + rng.normal(0, 0.5, l.shape) for l in _lane_lines(project)]
    trajs = [t + rng.normal(0, 0.5, t.shape) for t in _body_trajectories(project)]
    a = vanishing_from_lines(lanes, pixel_sigma=0.5)
    b = vanishing_from_trajectories(trajs, pixel_sigma=0.5)
    agr = compare_vanishing(a, b, at=trajs[0].mean(axis=0))
    assert agr.status == "agree", agr.message
    assert "uyuşuyor" in agr.message


def test_shifted_vp_disagrees():
    project, _ = _camera(15.0, 20.0)
    a = vanishing_from_lines(_lane_lines(project))
    wrong = [l + np.array([40.0, 0.0]) * np.linspace(0, 1, len(l))[:, None]
             for l in _lane_lines(project)]  # çizgiler döndürülmüş → farklı VP
    b = vanishing_from_lines(wrong)
    agr = compare_vanishing(a, b, at=(900, 800))
    assert agr.status == "disagree"
    assert "ayrışıyor" in agr.message


def test_infinite_vs_finite_is_indeterminate():
    project, _ = _camera(15.0, 20.0)
    a = vanishing_from_lines(_lane_lines(project))
    b = vanishing_from_lines([[[0, 0], [100, 50]], [[0, 30], [100, 80]]])
    assert compare_vanishing(a, b, at=(0, 0)).status == "indeterminate"


# ── Uçtan uca: iz VP'si → cross-ratio hız ─────────────────────────────────────

def test_trajectory_vp_feeds_cross_ratio_speed():
    project, _ = _camera(15.0, 20.0)
    trajs = _body_trajectories(project, speed_kmh=70.0)
    vp = vanishing_from_trajectories(trajs).point
    ys = 14.0 + 70.0 / 3.6 * np.arange(12) / FPS
    contacts = project(np.column_stack([np.full(12, 3.8), ys, np.zeros(12)]))
    rear = project([3.8, ys[0], 0])[0]
    front = project([3.8, ys[0] + 2.65, 0])[0]
    scale = line_scale_from_vp(vp, rear, front, 2.65, line_points=contacts)
    res = cross_ratio_speed(scale, np.arange(12), contacts, FPS)
    assert res.speed_kmh == pytest.approx(70.0, rel=1e-3)


# ── KLT izleri (sentetik video) ───────────────────────────────────────────────

def _synthetic_video(vp=(640.0, 160.0), n=10, shrink=0.035):
    """Dokulu 'araç' VP merkezli homotetiyle uzaklaşıyor (öteleme → görüntüde VP'ye yakınsama)."""
    rng = np.random.default_rng(0)
    h, w = 720, 960
    background = np.full((h, w), 90, np.uint8)
    car = cv2.GaussianBlur(rng.integers(0, 255, (h, w)).astype(np.uint8), (0, 0), 1.5)
    rect = np.array([[480, 430], [800, 430], [800, 640], [480, 640]], np.float64)
    car_mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(car_mask, [rect.astype(np.int32)], 255)
    frames, boxes = [], []
    for k in range(n):
        s = 1.0 - shrink * k
        M = np.array([[s, 0, (1 - s) * vp[0]], [0, s, (1 - s) * vp[1]]])
        warped = cv2.warpAffine(car, M, (w, h), flags=cv2.INTER_LINEAR)
        m = cv2.warpAffine(car_mask, M, (w, h), flags=cv2.INTER_NEAREST)
        frame = np.where(m > 0, warped, background).astype(np.uint8)
        frames.append(cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR))
        r = rect @ np.diag([s, s]) + (1 - s) * np.asarray(vp)
        boxes.append((r[:, 0].min(), r[:, 1].min(), r[:, 0].max(), r[:, 1].max()))
    return frames, boxes, np.asarray(vp)


def test_klt_tracks_converge_to_vp():
    frames, boxes, vp = _synthetic_video()
    tracks = track_features_in_box(frames, boxes, frame_indices=range(100, 110))
    assert len(tracks) >= 10
    assert tracks[0].frame_indices[0] == 100
    est = vanishing_from_trajectories([t.points for t in tracks], pixel_sigma=0.5)
    assert np.linalg.norm(np.asarray(est.point) - vp) < 5.0


def test_klt_ignores_static_background():
    frames, boxes, _ = _synthetic_video(shrink=0.0)  # araç hareketsiz
    assert track_features_in_box(frames, boxes) == []


def test_klt_input_validation():
    frames, boxes, _ = _synthetic_video(n=2)
    with pytest.raises(ValueError):
        track_features_in_box(frames[:1], boxes[:1])
    with pytest.raises(ValueError):
        track_features_in_box(frames, boxes[:1])
