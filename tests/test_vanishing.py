"""T22 — Vanishing-point tabanlı otomatik kalibrasyon önerisi birim testleri."""
from __future__ import annotations

import numpy as np
import pytest
import cv2

from src.calibration.vanishing import (
    _fit_line_ransac,
    _intersect_lines,
    _line_x_at_y,
    detect_vanishing_point,
    propose_calibration,
)


# ── Sentetik çerçeve üretici ──────────────────────────────────────────────────

def _make_road_frame(width: int = 640, height: int = 480) -> tuple[np.ndarray, tuple[float, float]]:
    """İki şerit çizgisi VP'ye yakınsayan sentetik kare."""
    frame = np.full((height, width, 3), 64, dtype=np.uint8)
    vp_x, vp_y = float(width // 2), float(height * 0.35)
    # Sol şerit: VP → sol-alt
    bl_x, bl_y = float(width * 0.15), float(height - 1)
    # Sağ şerit: VP → sağ-alt
    br_x, br_y = float(width * 0.85), float(height - 1)
    cv2.line(frame, (int(vp_x), int(vp_y)), (int(bl_x), int(bl_y)), (220, 220, 220), 3)
    cv2.line(frame, (int(vp_x), int(vp_y)), (int(br_x), int(br_y)), (220, 220, 220), 3)
    return frame, (vp_x, vp_y)


def _make_blank_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """Şerit çizgisi olmayan düz gri kare."""
    return np.full((height, width, 3), 100, dtype=np.uint8)


def _make_horizontal_lines_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """Yatay çizgiler (açı filtresiyle elenecek) içeren kare."""
    frame = np.full((height, width, 3), 80, dtype=np.uint8)
    for y in [200, 250, 300, 350]:
        cv2.line(frame, (0, y), (width, y), (200, 200, 200), 2)
    return frame


# ── _fit_line_ransac testleri ─────────────────────────────────────────────────

def test_fit_line_ransac_clean():
    # y = -1.5*x + 800 doğrusundaki segmentler
    segs = [(100.0, 650.0, 200.0, 500.0), (200.0, 500.0, 300.0, 350.0)]
    result = _fit_line_ransac(segs)
    assert result is not None
    a, b = result
    assert abs(a - (-1.5)) < 0.2
    assert abs(b - 800.0) < 20.0


def test_fit_line_ransac_insufficient():
    segs = [(0.0, 0.0, 10.0, 5.0)]  # tek segment → 2 nokta
    result = _fit_line_ransac(segs)
    assert result is None


# ── _intersect_lines testleri ─────────────────────────────────────────────────

def test_intersect_lines_basic():
    # y = -x + 100 ve y = x - 20 → x=60, y=40
    vp = _intersect_lines((-1.0, 100.0), (1.0, -20.0))
    assert vp is not None
    x, y = vp
    assert abs(x - 60.0) < 1e-6
    assert abs(y - 40.0) < 1e-6


def test_intersect_lines_parallel():
    # Paralel doğrular → None
    result = _intersect_lines((2.0, 10.0), (2.0, 30.0))
    assert result is None


# ── _line_x_at_y testleri ─────────────────────────────────────────────────────

def test_line_x_at_y():
    # y = 2*x + 1 → x = (y-1)/2
    assert abs(_line_x_at_y((2.0, 1.0), 5.0) - 2.0) < 1e-9


# ── detect_vanishing_point testleri ──────────────────────────────────────────

def test_detect_vp_synthetic_frame():
    frame, expected_vp = _make_road_frame()
    result = detect_vanishing_point(frame)
    assert result is not None, "Sentetik karede VP tespit edilemedi"
    vp, left_line, right_line = result
    # VP yaklaşık doğru konumda mı?
    assert abs(vp[0] - expected_vp[0]) < 60, f"VP x hatası: {abs(vp[0] - expected_vp[0]):.1f}px"
    # Sol eğim negatif, sağ eğim pozitif
    assert left_line[0] < 0, "Sol şerit eğimi negatif olmalı"
    assert right_line[0] > 0, "Sağ şerit eğimi pozitif olmalı"


def test_detect_vp_blank_frame():
    frame = _make_blank_frame()
    result = detect_vanishing_point(frame)
    assert result is None, "Boş karede VP dönmemeli"


def test_detect_vp_horizontal_lines():
    frame = _make_horizontal_lines_frame()
    result = detect_vanishing_point(frame)
    # Yatay çizgiler açı filtresiyle elenir → tespit başarısız
    assert result is None, "Yatay çizgilerden VP dönmemeli"


# ── propose_calibration testleri ─────────────────────────────────────────────

def test_propose_calibration_synthetic():
    frame, _ = _make_road_frame()
    proposal = propose_calibration(frame, lane_width_m=3.5, n_pairs=4)
    assert proposal.quality_gate_passed, (
        f"Sentetik karede kalite kapısı geçmeli — reason: {proposal.quality_reason}"
    )
    assert len(proposal.proposed_points) == 8  # 4 çift
    assert proposal.vanishing_point is not None
    assert proposal.estimated_rms_m is not None
    assert proposal.estimated_rms_m >= 0.0


def test_propose_calibration_point_sources():
    frame, _ = _make_road_frame()
    proposal = propose_calibration(frame, lane_width_m=3.5, n_pairs=3)
    for pt in proposal.proposed_points:
        assert pt.source == "auto-vanishing"


def test_propose_calibration_world_coords():
    """Sol noktalar x=0, sağ noktalar x=lane_width_m; y=0 yakın satırda."""
    frame, _ = _make_road_frame()
    proposal = propose_calibration(frame, lane_width_m=3.5, n_pairs=4)
    assert proposal.quality_gate_passed
    left_pts = [p for p in proposal.proposed_points if p.id.startswith("av-L")]
    right_pts = [p for p in proposal.proposed_points if p.id.startswith("av-R")]
    for p in left_pts:
        assert p.world_m[0] == pytest.approx(0.0)
    for p in right_pts:
        assert p.world_m[0] == pytest.approx(3.5)
    # En yakın satır y=0
    y_vals = sorted([p.world_m[1] for p in proposal.proposed_points])
    assert y_vals[0] == pytest.approx(0.0)


def test_propose_calibration_blank_frame_fails():
    frame = _make_blank_frame()
    proposal = propose_calibration(frame, lane_width_m=3.5)
    assert not proposal.quality_gate_passed
    assert proposal.quality_reason == 'no_lines'
    assert len(proposal.proposed_points) == 0


def test_propose_calibration_line_pts_clamped():
    """Şerit çizgisi görselleştirme noktaları görüntü sınırları içinde olmalı."""
    frame, _ = _make_road_frame(640, 480)
    proposal = propose_calibration(frame, lane_width_m=3.5)
    if not proposal.quality_gate_passed:
        return  # Bu test sadece başarılı öneri için geçerli
    for pt in (proposal.left_line_pts or []):
        assert 0 <= pt[0] <= 640
        assert 0 <= pt[1] <= 480
    for pt in (proposal.right_line_pts or []):
        assert 0 <= pt[0] <= 640
        assert 0 <= pt[1] <= 480
