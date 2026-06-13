"""Acceptance tests for M6 — automatic reference detection."""
from __future__ import annotations

import math

import cv2
import numpy as np
import pytest

from src.autoref.lane import detect_lane_edges, fit_lane_line, sample_line_at_depths
from src.autoref.markers import DashedMarker, detect_dashed_markers, estimate_depth_scale
from src.autoref.models import ProposedPoint
from src.autoref.proposer import AutoProposer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lane_frame(w=640, h=480) -> np.ndarray:
    """Siyah zemin üzerine iki diyagonal beyaz çizgi — sol ve sağ şerit."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Sol şerit: (160,479) → (280,216) — sol yarıda, açı ~65°
    cv2.line(frame, (160, h - 1), (280, int(h * 0.45)), (255, 255, 255), 4)
    # Sağ şerit: (480,479) → (360,216) — sağ yarıda, açı ~65°
    cv2.line(frame, (w - 160, h - 1), (w - 280, int(h * 0.45)), (255, 255, 255), 4)
    return frame


def _blank_frame(h=480, w=640, value=128) -> np.ndarray:
    """Düz gri kare — hiçbir kenar içermez."""
    return np.full((h, w, 3), value, dtype=np.uint8)


def _horizontal_frame(h=480, w=640) -> np.ndarray:
    """Yalnızca yatay çizgiler içeren kare."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    cv2.line(frame, (0, 300), (w - 1, 300), (255, 255, 255), 3)
    cv2.line(frame, (0, 380), (w - 1, 380), (255, 255, 255), 3)
    return frame


def _dash_frame(h=480, w=640) -> np.ndarray:
    """ROI içinde 3 adet ~60 piksel uzunluğunda dikey segment içeren kare."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for y_start in [400, 320, 240]:
        cv2.line(frame, (315, y_start), (325, y_start + 55), (255, 255, 255), 4)
    return frame


def _make_markers(n: int = 3, length: float = 60.0) -> list[DashedMarker]:
    return [
        DashedMarker(
            start_pixel=(300.0, float(300 + i * 80)),
            end_pixel=(300.0, float(300 + i * 80 + length)),
            length_px=length,
        )
        for i in range(n)
    ]


# ── Test 1: Şerit tespiti — sentetik kare ────────────────────────────────────

def test_detect_lane_edges_finds_both_lanes():
    frame = _lane_frame()
    left, right = detect_lane_edges(frame)
    assert left is not None, "Sol şerit tespit edilmeli"
    assert right is not None, "Sağ şerit tespit edilmeli"
    assert left.shape[1] == 2
    assert right.shape[1] == 2


# ── Test 2: Boş kare ─────────────────────────────────────────────────────────

def test_detect_lane_edges_blank_frame_returns_none():
    frame = _blank_frame()
    left, right = detect_lane_edges(frame)
    assert left is None
    assert right is None


# ── Test 3: Yatay çizgiler filtrelenir ────────────────────────────────────────

def test_detect_lane_edges_horizontal_lines_filtered():
    frame = _horizontal_frame()
    left, right = detect_lane_edges(frame)
    assert left is None, "Yatay çizgiler sol şerit sayılmamalı"
    assert right is None, "Yatay çizgiler sağ şerit sayılmamalı"


# ── Test 4: Doğru uydurma ────────────────────────────────────────────────────

def test_fit_lane_line_known_slope():
    # y = 2x + 10 doğrusu üzerindeki noktalar
    xs = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
    ys = 2.0 * xs + 10.0
    points = np.column_stack([xs, ys])
    result = fit_lane_line(points)
    assert result is not None
    m, b = result
    assert abs(m - 2.0) < 0.01, f"Eğim ≈2 bekleniyor, alınan {m:.4f}"
    assert abs(b - 10.0) < 0.01, f"Kesim ≈10 bekleniyor, alınan {b:.4f}"


def test_fit_lane_line_two_points():
    points = np.array([[0.0, 0.0], [10.0, 20.0]])
    result = fit_lane_line(points)
    assert result is not None
    m, b = result
    assert abs(m - 2.0) < 0.01


def test_fit_lane_line_none_for_single_point():
    points = np.array([[5.0, 10.0]])
    assert fit_lane_line(points) is None


def test_fit_lane_line_none_for_vertical_points():
    """Tüm x değerleri aynıysa None döner (dikey çizgi, ptp=0)."""
    points = np.array([[5.0, 10.0], [5.0, 20.0], [5.0, 30.0]])
    assert fit_lane_line(points) is None


def test_sample_line_at_depths_correct_x():
    # y = 2x + 10 → x = (y - 10) / 2
    y_test = [10.0, 20.0, 30.0]
    samples = sample_line_at_depths(2.0, 10.0, y_test)
    assert len(samples) == 3
    assert abs(samples[0][0] - 0.0) < 1e-6   # y=10 → x=0
    assert abs(samples[1][0] - 5.0) < 1e-6   # y=20 → x=5
    assert abs(samples[2][0] - 10.0) < 1e-6  # y=30 → x=10


def test_sample_line_at_depths_zero_slope():
    assert sample_line_at_depths(0.0, 5.0, [10.0, 20.0]) == []


# ── Test 5: Kesik çizgi tespiti ──────────────────────────────────────────────

def test_detect_dashed_markers_finds_segments():
    frame = _dash_frame()
    markers = detect_dashed_markers(frame, min_segment_px=20, max_segment_px=200)
    assert len(markers) >= 3, (
        f"En az 3 segment bekleniyor, {len(markers)} tespit edildi"
    )


def test_detect_dashed_markers_empty_on_blank():
    frame = _blank_frame()
    markers = detect_dashed_markers(frame)
    assert markers == []


def test_detect_dashed_markers_length_range_filter():
    """Çok kısa veya çok uzun segmentler filtrelenmeli."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # 250px çizgi — max_segment_px=100 ise filtrelenmeli
    cv2.line(frame, (300, 250), (300, 500), (255, 255, 255), 4)
    markers = detect_dashed_markers(frame, min_segment_px=20, max_segment_px=100)
    # 250px segment max_segment_px=100 dışında → 0 veya bölünmüş segment olabilir
    # Test: 250px üzeri tek parça olarak raporlanmamalı
    for m in markers:
        assert m.length_px <= 100 + 5, (
            f"Segment {m.length_px:.0f}px — max_segment_px=100'ü aşmamalı"
        )


# ── Test 6: Derinlik ölçeği tahmini ─────────────────────────────────────────

def test_estimate_depth_scale_correct():
    markers = _make_markers(n=3, length=60.0)
    result = estimate_depth_scale(markers, dash_length_m=3.0)
    assert result is not None
    assert abs(result - 20.0) < 0.1, f"60px / 3m = 20 px/m bekleniyor, {result:.2f}"


def test_estimate_depth_scale_uses_median():
    # Uzunluklar: 50, 60, 70 → medyan=60 → 60/3=20
    markers = [
        DashedMarker((0, 0), (0, 50), 50.0),
        DashedMarker((0, 0), (0, 60), 60.0),
        DashedMarker((0, 0), (0, 70), 70.0),
    ]
    result = estimate_depth_scale(markers, dash_length_m=3.0)
    assert result is not None
    assert abs(result - 20.0) < 0.1


def test_estimate_depth_scale_none_for_fewer_than_3():
    markers = _make_markers(n=2)
    assert estimate_depth_scale(markers) is None


def test_estimate_depth_scale_none_for_empty():
    assert estimate_depth_scale([]) is None


# ── Test 7: ProposedPoint → ControlPoint ─────────────────────────────────────

def test_proposed_point_to_control_point_source():
    p = ProposedPoint(pixel=(100.0, 200.0), world_m=(0.0, 5.0),
                      detection_confidence=0.8, description="left_lane_near")
    cp = p.to_control_point("cp_auto_1")
    assert cp.source == "auto"
    assert cp.id == "cp_auto_1"
    assert cp.pixel == (100.0, 200.0)
    assert cp.world_m == (0.0, 5.0)


# ── Test 8: Öneri confidence_layer ───────────────────────────────────────────

def test_proposed_points_give_standard_assumption_layer():
    from src.calibration.homography import compute_homography
    # Elle oluşturulmuş 4 nokta çifti (düzgün homografi için)
    proposals = [
        ProposedPoint(pixel=(160.0, 480.0), world_m=(0.0, 0.0), detection_confidence=0.9),
        ProposedPoint(pixel=(480.0, 480.0), world_m=(3.5, 0.0), detection_confidence=0.9),
        ProposedPoint(pixel=(200.0, 300.0), world_m=(0.0, 10.0), detection_confidence=0.8),
        ProposedPoint(pixel=(440.0, 300.0), world_m=(3.5, 10.0), detection_confidence=0.8),
    ]
    cps = [p.to_control_point(f"cp_{i}") for i, p in enumerate(proposals)]
    # Hepsi source="auto" → confidence_layer = "standard_assumption"
    result = compute_homography(cps)
    assert result.confidence_layer == "standard_assumption"


# ── Test 9: draw_proposals çizim yapar ───────────────────────────────────────

def test_draw_proposals_modifies_frame():
    proposer = AutoProposer()
    frame = _blank_frame()
    proposal = ProposedPoint(pixel=(300.0, 300.0), world_m=(0.0, 0.0),
                             detection_confidence=0.8, description="left_lane_near")
    out = proposer.draw_proposals(frame, [proposal])
    assert not np.array_equal(frame, out), "Overlay frame orijinalle aynı olmamalı"


# ── Test 10: draw_proposals boş öneriyle değişmez ────────────────────────────

def test_draw_proposals_empty_unchanged():
    proposer = AutoProposer()
    frame = _lane_frame()
    out = proposer.draw_proposals(frame, [])
    assert np.array_equal(frame, out), "Boş öneriyle kare değişmemeli"


# ── Test 11: AutoProposer uçtan uca ──────────────────────────────────────────

def test_auto_proposer_lane_frame_produces_proposals():
    proposer = AutoProposer(n_sample_depths=3)
    frame = _lane_frame()
    proposals = proposer.propose(frame)
    assert len(proposals) > 0, "Şerit içeren karede öneri üretilmeli"


def test_auto_proposer_blank_frame_returns_empty():
    proposer = AutoProposer()
    proposals = proposer.propose(_blank_frame())
    assert proposals == []


def test_auto_proposer_left_world_x_zero():
    proposer = AutoProposer(lane_width_m=3.5)
    proposals = proposer.propose(_lane_frame())
    left = [p for p in proposals if "left" in p.description]
    assert len(left) > 0
    for p in left:
        assert abs(p.world_m[0] - 0.0) < 1e-9, "Sol şerit x_world=0 olmalı"


def test_auto_proposer_right_world_x_lane_width():
    proposer = AutoProposer(lane_width_m=3.5)
    proposals = proposer.propose(_lane_frame())
    right = [p for p in proposals if "right" in p.description]
    assert len(right) > 0
    for p in right:
        assert abs(p.world_m[0] - 3.5) < 1e-9, "Sağ şerit x_world=3.5 olmalı"


def test_auto_proposer_y_world_increases_with_distance():
    """Uzaktaki noktalar daha büyük y_world değeri taşımalı (derin = yüksek y_world)."""
    proposer = AutoProposer(n_sample_depths=3)
    proposals = proposer.propose(_lane_frame())
    left = sorted(
        [p for p in proposals if "left" in p.description],
        key=lambda p: p.pixel[1],   # y piksel artan = yakın → uzak
        reverse=True,               # yakın önce (büyük y_px)
    )
    if len(left) >= 2:
        # Yakın nokta: y_world küçük; uzak nokta: y_world büyük
        assert left[0].world_m[1] <= left[-1].world_m[1], (
            "Uzak noktanın y_world değeri yakın noktanınkinden büyük olmalı"
        )
