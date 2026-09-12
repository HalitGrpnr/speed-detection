"""T15 — Transverse kılavuz hesabı birim testleri."""
import math
import pytest
from src.calibration.transverse_guide import compute_transverse_direction, guide_line_endpoints


def test_vertical_road_gives_horizontal_transverse():
    # Dikey yol yönü (0, -1) → transverse yatay (1, 0) veya (-1, 0)
    p1 = (400.0, 300.0)
    p2 = (400.0, 100.0)  # yukarı doğru
    dx, dy = compute_transverse_direction(p1, p2)
    # 90° CCW rotasyon: road (-0, 200) → perp (-(-200), -0) = (200, 0) → normalized (1, 0)
    # road_dx = 0, road_dy = -200 → perp_x = -(-200) = 200, perp_y = 0 → (1, 0)
    assert dx == pytest.approx(1.0, abs=1e-9)
    assert dy == pytest.approx(0.0, abs=1e-9)


def test_horizontal_road_gives_vertical_transverse():
    # Yatay yol yönü (1, 0) → transverse dikey (0, 1) veya (0, -1)
    p1 = (100.0, 400.0)
    p2 = (300.0, 400.0)  # sağa doğru
    dx, dy = compute_transverse_direction(p1, p2)
    # road_dx=200, road_dy=0 → perp_x=-0, perp_y=200 → normalized (0, 1)
    assert dx == pytest.approx(0.0, abs=1e-9)
    assert dy == pytest.approx(1.0, abs=1e-9)


def test_normalized_result():
    # Sonuç her zaman birim vektör olmalı
    p1 = (0.0, 0.0)
    p2 = (3.0, 4.0)  # 5 uzunluğunda
    dx, dy = compute_transverse_direction(p1, p2)
    assert math.hypot(dx, dy) == pytest.approx(1.0, abs=1e-9)


def test_diagonal_road():
    # 45° açılı yol → transverse de 45° (başka yönde)
    p1 = (0.0, 0.0)
    p2 = (100.0, 100.0)  # 45° sağ-aşağı
    dx, dy = compute_transverse_direction(p1, p2)
    # road_dx=100, road_dy=100 → perp_x=-100, perp_y=100 → normalized (-1/√2, 1/√2)
    assert dx == pytest.approx(-1.0 / math.sqrt(2), abs=1e-9)
    assert dy == pytest.approx(1.0 / math.sqrt(2), abs=1e-9)


def test_degenerate_same_point():
    # Aynı nokta → varsayılan (1, 0)
    dx, dy = compute_transverse_direction((100.0, 100.0), (100.0, 100.0))
    assert dx == pytest.approx(1.0, abs=1e-9)
    assert dy == pytest.approx(0.0, abs=1e-9)


def test_guide_line_endpoints_horizontal():
    # Yatay transverse, canvas 800x600, teker ortada
    wheel = (400.0, 300.0)
    d = (1.0, 0.0)
    (x1, y1), (x2, y2) = guide_line_endpoints(wheel, d, 800, 600)
    assert x1 == pytest.approx(0.0, abs=1e-6)
    assert y1 == pytest.approx(300.0, abs=1e-6)
    assert x2 == pytest.approx(800.0, abs=1e-6)
    assert y2 == pytest.approx(300.0, abs=1e-6)


def test_guide_line_endpoints_vertical():
    # Dikey transverse, canvas 800x600, teker ortada
    wheel = (400.0, 300.0)
    d = (0.0, 1.0)
    (x1, y1), (x2, y2) = guide_line_endpoints(wheel, d, 800, 600)
    assert x1 == pytest.approx(400.0, abs=1e-6)
    assert y1 == pytest.approx(0.0, abs=1e-6)
    assert x2 == pytest.approx(400.0, abs=1e-6)
    assert y2 == pytest.approx(600.0, abs=1e-6)


def test_guide_line_passes_through_wheel():
    # Kılavuz çizgisi her zaman teker noktasından geçmeli
    wheel = (350.0, 250.0)
    d = compute_transverse_direction((100.0, 0.0), (200.0, 50.0))
    (x1, y1), (x2, y2) = guide_line_endpoints(wheel, d, 800, 600)
    # Doğrusal parametrik interpolasyon ile kontrol: midpoint teker noktasına eşit mi?
    # Daha doğrusu: (wheel - p1) / (p2 - p1) aynı t olmalı
    # Bunun yerine: wheel ile p1 arasındaki vektör d ile paralel mi?
    v1x, v1y = wheel[0] - x1, wheel[1] - y1
    cross = v1x * d[1] - v1y * d[0]
    assert abs(cross) < 1e-4  # neredeyse paralel (kayan nokta hatası toleransı)
