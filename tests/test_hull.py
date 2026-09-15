"""T17: Kalibrasyon hull guardrail birim testleri."""
import pytest
import numpy as np
from src.calibration.models import ControlPoint
from src.reliability.hull import (
    calibration_hull,
    point_in_hull,
    hull_inside_fraction,
    OUT_OF_ZONE_FRACTION,
)


def _cp(x: float, y: float, id_: str = "cp") -> ControlPoint:
    return ControlPoint(id=id_, pixel=(0.0, 0.0), world_m=(x, y), source="operator")


# Birim kare: (0,0)-(3.5,0)-(3.5,7)-(0,7) — 4 kontrol noktası
SQUARE_PTS = [
    _cp(0.0, 0.0, "a"),
    _cp(3.5, 0.0, "b"),
    _cp(3.5, 7.0, "c"),
    _cp(0.0, 7.0, "d"),
]


def test_hull_built_from_4_points():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None


def test_hull_none_for_fewer_than_3_points():
    assert calibration_hull([_cp(0, 0, "a"), _cp(1, 0, "b")]) is None


def test_point_in_hull_center():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    assert point_in_hull((1.75, 3.5), hull) is True


def test_point_in_hull_on_edge():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    # Kenar üzerindeki nokta — içinde sayılmalı (tolerans: 1e-10)
    assert point_in_hull((0.0, 3.5), hull) is True


def test_point_outside_hull_counter_lane():
    """T17 kök-neden: karşı şerit X≈4.0, kalibrasyon X=0..3.5 → dışarıda."""
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    assert point_in_hull((4.0, 3.5), hull) is False


def test_point_outside_hull_far():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    assert point_in_hull((10.0, 50.0), hull) is False


def test_hull_inside_fraction_all_inside():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    pts = [(0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (3.0, 6.5)]
    assert hull_inside_fraction(pts, hull) == pytest.approx(1.0)


def test_hull_inside_fraction_all_outside():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    pts = [(5.0, 5.0), (6.0, 6.0), (7.0, 7.0)]
    assert hull_inside_fraction(pts, hull) == pytest.approx(0.0)


def test_hull_inside_fraction_mixed():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    # 2 içeride, 2 dışarıda
    pts = [(1.0, 3.0), (2.0, 4.0), (5.0, 5.0), (6.0, 6.0)]
    frac = hull_inside_fraction(pts, hull)
    assert frac == pytest.approx(0.5)


def test_hull_inside_fraction_empty():
    hull = calibration_hull(SQUARE_PTS)
    assert hull is not None
    assert hull_inside_fraction([], hull) == pytest.approx(0.0)


def test_hull_with_used_ids_filter():
    """used_ids sadece inlier noktaları kullanır."""
    pts = SQUARE_PTS + [_cp(100.0, 100.0, "outlier")]
    hull_all = calibration_hull(pts)
    hull_inliers = calibration_hull(pts, used_ids={"a", "b", "c", "d"})
    # Outlier dahil edilince hull daha büyük; inlier-only hull karşı şerit noktasını dışlar
    assert hull_inliers is not None
    assert point_in_hull((4.0, 3.5), hull_inliers) is False


def test_out_of_zone_threshold_value():
    """OUT_OF_ZONE_FRACTION 0 < threshold < 1 aralığında olmalı."""
    assert 0.0 < OUT_OF_ZONE_FRACTION < 1.0


def test_collinear_points_returns_none():
    """Collinear noktalar hull oluşturamaz → None döner."""
    collinear = [_cp(0.0, 0.0, "a"), _cp(1.0, 0.0, "b"), _cp(2.0, 0.0, "c")]
    result = calibration_hull(collinear)
    assert result is None
