"""T14 — Alt-kare kalibrasyon noktası enterpolasyonu birim testleri."""
import pytest
from src.calibration.interpolation import interpolate_calibration_point


def test_vertical_movement_midpoint():
    # Araç Y ekseninde hareket ediyor; hedef tam ortada
    frame_n = (100.0, 200.0)
    frame_n1 = (102.0, 300.0)
    target = (0.0, 250.0)  # Y hedef = 250, ortada
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(0.5, abs=1e-9)
    assert y == pytest.approx(250.0, abs=1e-9)
    assert x == pytest.approx(101.0, abs=1e-9)  # 100 + 0.5 * 2


def test_vertical_movement_at_frame_n():
    frame_n = (50.0, 100.0)
    frame_n1 = (50.0, 200.0)
    target = (0.0, 100.0)
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(100.0, abs=1e-9)
    assert x == pytest.approx(50.0, abs=1e-9)


def test_vertical_movement_at_frame_n1():
    frame_n = (50.0, 100.0)
    frame_n1 = (60.0, 200.0)
    target = (0.0, 200.0)
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(1.0, abs=1e-9)
    assert y == pytest.approx(200.0, abs=1e-9)
    assert x == pytest.approx(60.0, abs=1e-9)


def test_horizontal_movement_primary():
    # X hareketi Y'den büyük; X ekseninde enterpolasyon
    frame_n = (100.0, 200.0)
    frame_n1 = (300.0, 210.0)
    target = (200.0, 0.0)  # X hedef = 200
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(0.5, abs=1e-9)
    assert x == pytest.approx(200.0, abs=1e-9)
    assert y == pytest.approx(205.0, abs=1e-9)  # 200 + 0.5 * 10


def test_equal_dx_dy_uses_dy():
    # |dx| == |dy| → dy kullanılır (>= koşulu)
    frame_n = (0.0, 0.0)
    frame_n1 = (10.0, 10.0)
    target = (0.0, 5.0)
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(0.5, abs=1e-9)
    assert y == pytest.approx(5.0, abs=1e-9)
    assert x == pytest.approx(5.0, abs=1e-9)


def test_same_pixel_raises():
    with pytest.raises(ValueError, match="same pixel"):
        interpolate_calibration_point((100.0, 200.0), (100.0, 200.0), (100.0, 200.0))


def test_fractional_t_outside_bracket():
    # t > 1 durumu: arka teker zaten hedefi geçmiş (operatör yanlış kare seçmiş)
    # Fonksiyon yine de hesap yapar — çağıran karar verir
    frame_n = (0.0, 0.0)
    frame_n1 = (0.0, 50.0)
    target = (0.0, 100.0)  # hedef frame_n1'in ötesinde
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(2.0, abs=1e-9)
    assert y == pytest.approx(100.0, abs=1e-9)


def test_subpixel_precision():
    # Küçük piksel adımlarında hassasiyet kontrolü
    frame_n = (500.0, 300.0)
    frame_n1 = (501.0, 303.0)
    target = (0.0, 301.0)
    (x, y), t = interpolate_calibration_point(frame_n, frame_n1, target)
    assert t == pytest.approx(1.0 / 3.0, abs=1e-9)
    assert y == pytest.approx(301.0, abs=1e-9)
    assert x == pytest.approx(500.0 + 1.0 / 3.0, abs=1e-9)
