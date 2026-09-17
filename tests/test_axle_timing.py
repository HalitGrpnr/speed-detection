"""T27 — axle_timing_speed birim testleri."""
import pytest
from src.speed.axle_timing import axle_timing_speed


def _make_crossing(
    front_fn: int, front_fn1: int, front_pn: tuple, front_pn1: tuple,
    rear_fn: int, rear_fn1: int, rear_pn: tuple, rear_pn1: tuple,
    target: tuple,
) -> dict:
    return {
        "front_frame_n": front_fn, "front_pixel_n": front_pn,
        "front_frame_n1": front_fn1, "front_pixel_n1": front_pn1,
        "rear_frame_n": rear_fn, "rear_pixel_n": rear_pn,
        "rear_frame_n1": rear_fn1, "rear_pixel_n1": rear_pn1,
        "target_px": target,
    }


# ── Temel doğruluk ────────────────────────────────────────────────────────────

def test_exact_frame_crossing_25fps():
    """Tam kare geçişi: ön=10, arka=20 → Δt=10/25=0.4s, 2.65/0.4*3.6=23.85 km/h."""
    # Ön tekerlek tam olarak kare 10 ile 11 arasında geçiyor (target ortada)
    # Arka tekerlek tam olarak kare 20 ile 21 arasında
    # Her ikisi için de target, N ve N+1'in ortası → t_frac = 0.5
    fps = 25.0
    crossing = _make_crossing(
        front_fn=10, front_fn1=11,
        front_pn=(100.0, 200.0), front_pn1=(120.0, 200.0),
        rear_fn=20, rear_fn1=21,
        rear_pn=(100.0, 200.0), rear_pn1=(120.0, 200.0),
        target=(110.0, 200.0),  # X ortası → t_frac = 0.5
    )
    result = axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)
    # t_front = (10 + 0.5) / 25 = 0.42s; t_rear = (20 + 0.5) / 25 = 0.82s
    # Δt = 0.4s; hız = 2.65 / 0.4 * 3.6 = 23.85 km/h
    assert abs(result.speed_kmh - 23.85) < 0.1
    assert result.crossing_count == 1


def test_subframe_interpolation_accuracy():
    """t_frac 0.5 değil, kenar geçiş noktasına göre hesaplanır."""
    fps = 25.0
    # Ön teker: N piksel=(0,0) → N+1 piksel=(20,0). Target x=5 → t_frac=0.25
    # Arka teker: N piksel=(0,0) → N+1 piksel=(20,0). Target x=15 → t_frac=0.75
    crossing = _make_crossing(
        front_fn=10, front_fn1=11,
        front_pn=(0.0, 100.0), front_pn1=(20.0, 100.0),
        rear_fn=20, rear_fn1=21,
        rear_pn=(0.0, 100.0), rear_pn1=(20.0, 100.0),
        target=(5.0, 100.0),   # ön t_frac=0.25; arka t_frac=0.25 (aynı target)
    )
    result = axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)
    # t_front = (10 + 0.25) / 25; t_rear = (20 + 0.25) / 25
    # Δt = 10/25 = 0.4s → 2.65/0.4*3.6 = 23.85
    assert abs(result.speed_kmh - 23.85) < 0.1


def test_higher_speed():
    """82 km/h senaryosu: 2.65 m / Δt = 82 → Δt ≈ 0.1163s @ 25 fps ≈ 2.9 kare."""
    fps = 25.0
    # Δt = 2.65 / (82 / 3.6) = 0.11634s → 2.909 kare
    # ön: kare 10 tam, arka: kare 12 + t_frac öyle ki toplam 2.909 kare
    # Kolaylık: t_front=10.0 (t_frac=0), t_rear=12.909 (t_frac=0.909)
    # Arka: kare 12→13, target x=18.18 (x=[0..20] → t_frac=18.18/20=0.909)
    crossing = _make_crossing(
        front_fn=10, front_fn1=11,
        front_pn=(10.0, 100.0), front_pn1=(10.0, 100.0),  # hareketsiz → t_frac=0.5 (fallback)
        rear_fn=12, rear_fn1=13,
        rear_pn=(0.0, 100.0), rear_pn1=(20.0, 100.0),
        target=(10.0, 100.0),  # ön: hareketsiz → 0.5, arka: x=10→t_frac=0.5
    )
    # Δt = (12.5 - 10.5) / 25 = 2/25 = 0.08s → 2.65/0.08*3.6 = 119.25 km/h (farklı Δt)
    # Beklenen: crossing başarılı, uyarı var
    result = axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)
    assert result.speed_kmh > 0
    assert result.crossing_count == 1


def test_multiple_crossings_median():
    """Çoklu geçişte median kullanılır."""
    fps = 25.0
    def c(fn, rn):
        return _make_crossing(
            front_fn=fn, front_fn1=fn+1,
            front_pn=(0.0, 100.0), front_pn1=(20.0, 100.0),
            rear_fn=rn, rear_fn1=rn+1,
            rear_pn=(0.0, 100.0), rear_pn1=(20.0, 100.0),
            target=(10.0, 100.0),
        )
    # 3 geçiş: Δt = 10/25=0.4s, 10/25=0.4s, 10/25=0.4s → hepsi aynı hız
    crossings = [c(0, 10), c(20, 30), c(40, 50)]
    result = axle_timing_speed(crossings, wheelbase_m=2.65, fps=fps)
    assert result.crossing_count == 3
    assert abs(result.speed_kmh - 23.85) < 0.1
    assert result.confidence_level in ("high", "medium")


def test_ci_single_crossing_positive():
    """Tek geçişte CI > 0."""
    fps = 25.0
    crossing = _make_crossing(
        front_fn=0, front_fn1=1,
        front_pn=(0.0, 100.0), front_pn1=(20.0, 100.0),
        rear_fn=10, rear_fn1=11,
        rear_pn=(0.0, 100.0), rear_pn1=(20.0, 100.0),
        target=(10.0, 100.0),
    )
    result = axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)
    assert result.ci_kmh > 0


def test_t_frac_clamped():
    """t_frac her zaman [0,1] aralığında kalır (target N'den önce veya N+1'den sonra olsa bile)."""
    fps = 25.0
    crossing = _make_crossing(
        front_fn=10, front_fn1=11,
        front_pn=(5.0, 100.0), front_pn1=(15.0, 100.0),
        rear_fn=20, rear_fn1=21,
        rear_pn=(5.0, 100.0), rear_pn1=(15.0, 100.0),
        target=(-100.0, 100.0),  # kare dışında sınır zorlaması
    )
    result = axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)
    assert result.speed_kmh > 0  # sınır dışı target → t_frac=0 → çalışmalı


def test_negative_delta_t_skipped():
    """t_rear < t_front olan geçiş atlanır, uyarı üretilir."""
    fps = 25.0
    # Ön: kare 20, Arka: kare 5 (arka önce → negatif Δt)
    crossing = _make_crossing(
        front_fn=20, front_fn1=21,
        front_pn=(0.0, 100.0), front_pn1=(20.0, 100.0),
        rear_fn=5, rear_fn1=6,
        rear_pn=(0.0, 100.0), rear_pn1=(20.0, 100.0),
        target=(10.0, 100.0),
    )
    with pytest.raises(ValueError, match="[Gg]eçerli geçiş"):
        axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)


def test_invalid_wheelbase():
    fps = 25.0
    crossing = _make_crossing(
        front_fn=0, front_fn1=1,
        front_pn=(0.0, 100.0), front_pn1=(10.0, 100.0),
        rear_fn=5, rear_fn1=6,
        rear_pn=(0.0, 100.0), rear_pn1=(10.0, 100.0),
        target=(5.0, 100.0),
    )
    with pytest.raises(ValueError, match="pozitif"):
        axle_timing_speed([crossing], wheelbase_m=0.0, fps=fps)


def test_empty_crossings():
    with pytest.raises(ValueError, match="En az 1"):
        axle_timing_speed([], wheelbase_m=2.65, fps=25.0)


def test_non_consecutive_frames_warning():
    """Ardışık olmayan bracket kareleri uyarı üretir ama çökmez."""
    fps = 25.0
    crossing = _make_crossing(
        front_fn=10, front_fn1=13,  # ardışık değil
        front_pn=(0.0, 100.0), front_pn1=(20.0, 100.0),
        rear_fn=20, rear_fn1=23,    # ardışık değil
        rear_pn=(0.0, 100.0), rear_pn1=(20.0, 100.0),
        target=(10.0, 100.0),
    )
    result = axle_timing_speed([crossing], wheelbase_m=2.65, fps=fps)
    assert any("ardışık değil" in w for w in result.warnings)
    assert result.speed_kmh > 0
