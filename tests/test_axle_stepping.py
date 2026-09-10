"""Birim testler — AxleStepper (T8)."""
from __future__ import annotations

import numpy as np
import pytest

from src.speed.axle_stepping import AxleStepper, AxleStep


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def _identity_H() -> np.ndarray:
    """H = birim matris: piksel = dünya (metre cinsinden, küçük test koordinatları)."""
    return np.eye(3, dtype=np.float64)


def _scaled_H(scale: float = 0.01) -> np.ndarray:
    """H: piksel * scale = metre (örn. 1 px = 0.01 m)."""
    H = np.eye(3, dtype=np.float64)
    H[0, 0] = scale
    H[1, 1] = scale
    return H


def pixel_to_world_manual(H: np.ndarray, p: tuple[float, float]) -> tuple[float, float]:
    """El hesabı — H * [px, py, 1]^T ve normalize."""
    v = H @ np.array([p[0], p[1], 1.0])
    return (v[0] / v[2], v[1] / v[2])


# ── Temel hız hesabı ─────────────────────────────────────────────────────────

class TestBasicSpeedEstimation:
    def test_constant_speed_two_steps(self):
        """Sabit hızda 2 adım → doğru hız."""
        fps = 25.0
        wheelbase_m = 2.65
        speed_kmh = 50.0
        speed_ms = speed_kmh / 3.6

        H = _identity_H()
        # Araç Y ekseninde hareket ediyor (yukarı = ileri)
        front_px = (0.0, wheelbase_m)   # ön teker (1 wheelbase ileride)
        rear_px = (0.0, 0.0)             # arka teker (referans)

        stepper = AxleStepper(H, front_px, rear_px, wheelbase_m, fps)

        # Başlangıç (frame 0, arka teker orijinde)
        stepper.feed(0, (0.0, 0.0))

        # Her frame_dt'de speed_ms * frame_dt metre ilerle
        frame_dt = 1.0  # frame_step = 1
        n_frames = 100
        for i in range(1, n_frames + 1):
            y = speed_ms * i / fps
            stepper.feed(i, (0.0, y))

        speed, ci = stepper.estimate_speed()
        assert speed is not None
        assert abs(speed - speed_kmh) < 0.5  # 0.5 km/h tolerans

    def test_single_step_returns_none(self):
        """1 adım → hız hesaplanamaz."""
        H = _identity_H()
        wheelbase_m = 2.65
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps=25.0)
        stepper.feed(0, (0.0, 0.0))
        # Yalnızca 1 adım tamamlanacak kadar ilerleme
        stepper.feed(10, (0.0, wheelbase_m + 0.1))
        assert len(stepper._steps) == 1
        speed, ci = stepper.estimate_speed()
        assert speed is None
        assert ci is None

    def test_no_steps_returns_none(self):
        """Hiç adım tamamlanmadan None döner."""
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, 2.65), (0.0, 0.0), 2.65, fps=25.0)
        stepper.feed(0, (0.0, 0.0))
        stepper.feed(5, (0.0, 1.0))  # < wheelbase
        assert stepper.estimate_speed() == (None, None)


# ── Alt-kare enterpolasyon ────────────────────────────────────────────────────

class TestSubFrameInterpolation:
    def test_interpolation_precision(self):
        """Eşik tam karelerin arasında geçilince kesirli frame doğru hesaplanır."""
        fps = 25.0
        wheelbase_m = 2.65
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps)

        # Frame 0: y=0.0 (başlangıç)
        # Frame 10: y=3.0 → eşik (2.65) ortada geçiliyor
        stepper.feed(0, (0.0, 0.0))
        new = stepper.feed(10, (0.0, 3.0))

        assert len(new) == 1
        step = new[0]
        # f* = 0 + (2.65 - 0) / (3.0 - 0) * 10 = 8.833...
        expected_frame = 2.65 / 3.0 * 10
        assert abs(step.frame - expected_frame) < 0.01

    def test_multiple_steps_same_feed(self):
        """Tek feed çağrısında birden fazla eşik geçilebilir."""
        fps = 25.0
        wheelbase_m = 1.0
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, 1.0), (0.0, 0.0), wheelbase_m, fps,
                               max_gap_frames=100)

        stepper.feed(0, (0.0, 0.0))
        # Frame 50'de 5 m ilerleme → 5 adım
        new = stepper.feed(50, (0.0, 5.5))
        assert len(new) == 5
        assert len(stepper._steps) == 5

    def test_step_frames_monotonically_increasing(self):
        """Adım frame'leri her zaman artan sıradadır."""
        fps = 25.0
        wheelbase_m = 2.0
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, 2.0), (0.0, 0.0), wheelbase_m, fps)
        stepper.feed(0, (0.0, 0.0))

        for i in range(1, 30):
            stepper.feed(i, (0.0, float(i) * 0.5))

        frames = [s.frame for s in stepper._steps]
        assert frames == sorted(frames)


# ── Track boşluğu (okluzyona bağlı) ─────────────────────────────────────────

class TestGapDetection:
    def test_gap_interrupts_stepping(self):
        """max_gap_frames'i aşan frame boşluğu adımlamayı durdurur."""
        fps = 25.0
        wheelbase_m = 2.65
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps,
                               max_gap_frames=5)

        stepper.feed(0, (0.0, 0.0))
        stepper.feed(3, (0.0, 1.0))
        # 6 kare boşluk (> max_gap_frames=5)
        stepper.feed(9, (0.0, 5.0))

        assert stepper.interrupted is True
        assert stepper.interrupt_reason is not None
        assert "boşluk" in stepper.interrupt_reason.lower() or "gap" in stepper.interrupt_reason.lower()

    def test_gap_stops_future_feeds(self):
        """Kesintiden sonra gelen feed çağrıları yeni adım üretmez."""
        fps = 25.0
        wheelbase_m = 2.65
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps,
                               max_gap_frames=3)

        stepper.feed(0, (0.0, 0.0))
        stepper.feed(10, (0.0, 5.0))  # gap → interrupt

        count_before = len(stepper._steps)
        stepper.feed(11, (0.0, 6.0))
        assert len(stepper._steps) == count_before  # ek adım yok

    def test_small_gap_allowed(self):
        """max_gap_frames içindeki boşluklar devam ettirir."""
        fps = 25.0
        wheelbase_m = 2.65
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps,
                               max_gap_frames=5)

        stepper.feed(0, (0.0, 0.0))
        stepper.feed(4, (0.0, 1.0))  # 4 kare boşluk → izin verilir
        assert stepper.interrupted is False


# ── Yön ve mesafe doğrulaması ─────────────────────────────────────────────────

class TestDirectionAndDistance:
    def test_initial_distance_measured(self):
        """Başlangıç ön-arka mesafesi doğru hesaplanır."""
        H = _identity_H()
        wheelbase_m = 2.65
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps=25.0)
        assert abs(stepper.initial_distance_m - wheelbase_m) < 1e-9

    def test_too_close_raises(self):
        """Çok yakın piksel konumları ValueError fırlatır."""
        H = _identity_H()
        with pytest.raises(ValueError, match="yakın"):
            AxleStepper(H, (10.0, 10.0), (10.0, 10.001), 2.65, fps=25.0)

    def test_diagonal_travel_direction(self):
        """Çapraz hareket yönü de doğru çalışır."""
        fps = 25.0
        wheelbase_m = 2.0
        H = _identity_H()
        # Araç 45° açıyla hareket ediyor: Δx = Δy = 1/√2 * wheelbase
        diag = wheelbase_m / np.sqrt(2)
        stepper = AxleStepper(H, (diag, diag), (0.0, 0.0), wheelbase_m, fps,
                               max_gap_frames=50)
        stepper.feed(0, (0.0, 0.0))

        # Bir wheelbase sonrası konumu: projeksiyon = wheelbase_m (tam eşik)
        # Eşik ≥ koşuluna dahil → 1 adım tamamlanır
        stepper.feed(25, (diag + 0.001, diag + 0.001))
        steps = stepper._steps
        assert len(steps) == 1
        assert abs(steps[0].distance_m - wheelbase_m) < 1e-9


# ── result() kısayolu ─────────────────────────────────────────────────────────

class TestResultHelper:
    def test_result_structure(self):
        fps = 25.0
        wheelbase_m = 2.65
        H = _identity_H()
        stepper = AxleStepper(H, (0.0, wheelbase_m), (0.0, 0.0), wheelbase_m, fps)
        stepper.feed(0, (0.0, 0.0))
        stepper.feed(50, (0.0, 10.0))

        r = stepper.result()
        assert r.step_count == len(stepper._steps)
        assert r.initial_distance_m == pytest.approx(wheelbase_m)
        assert isinstance(r.steps, list)
        if r.step_count >= 2:
            assert r.speed_kmh is not None
