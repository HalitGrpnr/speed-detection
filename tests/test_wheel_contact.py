"""T16 — wheel_contact_speed birim testleri.

Doğrulama harness 1: sentetik bilinen-hız testi (deterministik, CI'da çalışır).
Doğrulama harness 2: GPS oturum kalibrasyon noktaları + bbox alt-orta piksellerinden
~74 km/h beklenir (gps-dogrulama-bulgulari.md'deki gözlemlenen bbox değer).
Kabul kriteri: gerçek tekerlek-zemin temas piksellerinin ~78-82 km/h üretmesi gerekir
— bu pistlerin UI oturumundan elle doldurulacak bir TODO'dur.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.homography import compute_homography
from src.calibration.models import ControlPoint
from src.speed.wheel_contact import wheel_contact_speed, WheelSpeedResult


# ── Yardımcılar ───────────────────────────────────────────────────────────────


def _simple_homography():
    """4 köşe noktası ile basit dikdörtgen homografi.
    1 piksel ≈ 0.1 m (hem X hem Y) — sentetik testler için yeterli."""
    points = [
        ControlPoint(id="p1", pixel=(0.0, 0.0), world_m=(0.0, 0.0), source="operator"),
        ControlPoint(id="p2", pixel=(100.0, 0.0), world_m=(10.0, 0.0), source="operator"),
        ControlPoint(id="p3", pixel=(0.0, 100.0), world_m=(0.0, 10.0), source="operator"),
        ControlPoint(id="p4", pixel=(100.0, 100.0), world_m=(10.0, 10.0), source="operator"),
    ]
    return compute_homography(points).homography


def _gps_session_homography():
    """GPS doğrulama oturumundan gerçek kalibrasyon noktaları.
    Kaynak: data/sessions/f11938f5-…/session_log.jsonl, calibration_confirmed eventi.
    RMS: 14.89 cm (pt10 RANSAC ile dışlanıyor), fps=25.
    """
    points = [
        ControlPoint(id="cp1", pixel=(308.5, 351.6), world_m=(0.0, 0.0), source="operator"),
        ControlPoint(id="cp2", pixel=(370.6, 388.4), world_m=(0.0, 2.65), source="operator"),
        ControlPoint(id="cp3", pixel=(463.4, 444.1), world_m=(0.0, 5.3), source="operator"),
        ControlPoint(id="cp4", pixel=(583.1, 519.7), world_m=(0.0, 7.95), source="operator"),
        ControlPoint(id="cp5", pixel=(748.4, 623.7), world_m=(0.0, 10.6), source="operator"),
        ControlPoint(id="cp6", pixel=(362.9, 260.0), world_m=(3.5, 0.0), source="operator"),
        ControlPoint(id="cp7", pixel=(432.3, 283.9), world_m=(3.5, 2.65), source="operator"),
        ControlPoint(id="cp8", pixel=(534.6, 323.4), world_m=(3.5, 5.3), source="operator"),
        ControlPoint(id="cp9", pixel=(665.9, 380.4), world_m=(3.5, 7.95), source="operator"),
        ControlPoint(id="cp10", pixel=(840.9, 467.6), world_m=(3.5, 10.6), source="operator"),
    ]
    return compute_homography(points).homography


# ── Sentetik testler ──────────────────────────────────────────────────────────


class TestSyntheticKnownSpeed:
    """Bilinen dünya yolu → piksel back-projeksiyon → hız doğrulama."""

    def _world_to_pixel(self, H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
        H_inv = np.linalg.inv(H)
        pt = np.array([world[0], world[1], 1.0])
        px = H_inv @ pt
        return (px[0] / px[2], px[1] / px[2])

    def test_known_speed_72kmh(self):
        H = _simple_homography()
        fps = 25.0
        # Araç 20 m/s = 72 km/h ile Y ekseninde ilerliyor
        speed_ms = 72 / 3.6
        frames = [0, 25, 50, 75]  # 0, 1, 2, 3 saniye
        marks = []
        for frame in frames:
            t = frame / fps
            world = (1.0, speed_ms * t)  # X=1 sabit, Y artar
            pixel = self._world_to_pixel(H, world)
            marks.append({"frame": frame, "pixel": list(pixel)})

        result = wheel_contact_speed(marks, H, fps)
        assert abs(result.value_kmh - 72.0) < 0.5, f"Beklenen ~72, alınan {result.value_kmh}"
        assert result.mark_count == 4
        assert result.confidence_level in ("high", "medium")

    def test_known_speed_120kmh(self):
        H = _simple_homography()
        fps = 25.0
        speed_ms = 120 / 3.6
        frames = [0, 15, 30]
        marks = []
        for frame in frames:
            t = frame / fps
            world = (0.5, speed_ms * t)
            pixel = self._world_to_pixel(H, world)
            marks.append({"frame": frame, "pixel": list(pixel)})

        result = wheel_contact_speed(marks, H, fps)
        assert abs(result.value_kmh - 120.0) < 1.0, f"Beklenen ~120, alınan {result.value_kmh}"

    def test_subframe_marks(self):
        """T14 alt-kare enterpolasyonu: frame=62.35 gibi kesirli kareler desteklenmeli."""
        H = _simple_homography()
        fps = 25.0
        speed_ms = 80 / 3.6
        marks = [
            {"frame": 0.0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0)))},
            {"frame": 24.5, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 24.5 / fps)))},
            {"frame": 50.0, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 50.0 / fps)))},
        ]
        result = wheel_contact_speed(marks, H, fps)
        assert abs(result.value_kmh - 80.0) < 1.0

    def test_two_marks_minimum(self):
        H = _simple_homography()
        fps = 25.0
        speed_ms = 50 / 3.6
        marks = [
            {"frame": 0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0)))},
            {"frame": 25, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 1.0)))},
        ]
        result = wheel_contact_speed(marks, H, fps)
        assert abs(result.value_kmh - 50.0) < 0.5
        # 2 işaretli CI tanımsız → uyarı var
        assert any("2 işaret" in w for w in result.warnings)

    def test_insufficient_marks_raises(self):
        H = _simple_homography()
        with pytest.raises(ValueError, match="En az 2"):
            wheel_contact_speed([{"frame": 0, "pixel": [50.0, 50.0]}], H, fps=25.0)

    def test_empty_marks_raises(self):
        H = _simple_homography()
        with pytest.raises(ValueError):
            wheel_contact_speed([], H, fps=25.0)

    def test_negative_speed_warning(self):
        """İşaretler ters kare sırası → negatif hız uyarısı, pozitif değer döner."""
        H = _simple_homography()
        fps = 25.0
        speed_ms = 60 / 3.6
        marks = [
            {"frame": 50, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 2.0)))},
            {"frame": 25, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 1.0)))},
            {"frame": 0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0)))},
        ]
        result = wheel_contact_speed(marks, H, fps)
        # Hız pozitif (abs alınıyor) ama uyarı var
        assert result.value_kmh > 0
        assert any("negatif" in w for w in result.warnings)

    def test_high_confidence_4_marks_low_residual(self):
        H = _simple_homography()
        fps = 25.0
        speed_ms = 80 / 3.6
        frames = [0, 25, 50, 75]
        marks = [
            {"frame": f, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * f / fps)))}
            for f in frames
        ]
        result = wheel_contact_speed(marks, H, fps)
        assert result.confidence_level == "high", f"Beklenen high, alınan {result.confidence_level}"
        assert result.residual_kmh < 1.0


# ── GPS oturum doğrulama harness ──────────────────────────────────────────────


class TestGpsSessionBboxMarks:
    """GPS oturumundan gerçek kalibrasyon + bbox alt-orta piksel işaretleri.

    Kaynak: data/track8_bboxes.json, çerçeve 60-68 (GPS plato bölgesi).
    Bbox alt-ortası (parallax'lı) ~74 km/h bekleniyor.
    GPS referans: 82 km/h; gerçek tekerlek temas piksellerinin ~78-82 km/h
    üretmesi gerekir (T16 hedefi) — bu test bbox davranışını doğrular.
    """

    # data/track8_bboxes.json'dan alınan bbox alt-orta noktalara karşılık gelen
    # piksel koordinatları (cx=(x1+x2)/2, cy=y2) — GPS plateau, frame 60-68
    BBOX_MARKS = [
        {"frame": 60, "pixel": [423.6, 342.4]},
        {"frame": 62, "pixel": [478.9, 373.8]},
        {"frame": 64, "pixel": [546.7, 413.3]},
        {"frame": 66, "pixel": [628.5, 463.1]},
        {"frame": 68, "pixel": [724.0, 527.9]},
    ]

    def test_bbox_marks_give_74kmh_range(self):
        H = _gps_session_homography()
        result = wheel_contact_speed(self.BBOX_MARKS, H, fps=25.0)
        # Bbox alt-orta ile GPS testinde gözlemlenen 74-76 km/h aralığı
        assert 68.0 <= result.value_kmh <= 80.0, (
            f"Bbox işaretleriyle ~74 km/h bekleniyor, alınan {result.value_kmh}"
        )

    def test_result_has_required_fields(self):
        H = _gps_session_homography()
        result = wheel_contact_speed(self.BBOX_MARKS, H, fps=25.0)
        assert isinstance(result, WheelSpeedResult)
        assert result.mark_count == 5
        assert result.value_kmh > 0
        assert result.ci_kmh >= 0
        assert result.confidence_level in ("high", "medium", "low")

    # TODO: GPS oturum gerçek tekerlek piksellerini buraya ekle.
    # GPS referansı 82 km/h; UI'dan elle işaretlenince ~78-82 km/h beklenir.
    # Bbox değerinden (~74) belirgin üstte olması T16'nın kök nedeni kapatıldığını kanıtlar.
