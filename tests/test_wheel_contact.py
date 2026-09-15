"""T16/T19 — wheel_contact_speed ve wheel_contact_profile birim testleri.

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
from src.speed.wheel_contact import (
    wheel_contact_speed,
    wheel_contact_profile,
    WheelSpeedResult,
    WheelSpeedProfile,
    ProfilePoint,
)


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


# ── T19 — wheel_contact_profile birim testleri ────────────────────────────────


class TestWheelContactProfile:
    """Sentetik verilerle profil hesabı doğrulaması."""

    def _world_to_pixel(self, H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
        H_inv = np.linalg.inv(H)
        pt = np.array([world[0], world[1], 1.0])
        px = H_inv @ pt
        return (px[0] / px[2], px[1] / px[2])

    def _simple_homography(self):
        points = [
            ControlPoint(id="p1", pixel=(0.0, 0.0), world_m=(0.0, 0.0), source="operator"),
            ControlPoint(id="p2", pixel=(100.0, 0.0), world_m=(10.0, 0.0), source="operator"),
            ControlPoint(id="p3", pixel=(0.0, 100.0), world_m=(0.0, 10.0), source="operator"),
            ControlPoint(id="p4", pixel=(100.0, 100.0), world_m=(10.0, 10.0), source="operator"),
        ]
        return compute_homography(points).homography

    def _uniform_marks(self, H, fps, speed_kmh, n_frames=5, frame_step=25):
        """Sabit hızda n kare işareti (bilinen dünya yolu)."""
        speed_ms = speed_kmh / 3.6
        return [
            {"frame": float(i * frame_step),
             "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * (i * frame_step) / fps)))}
            for i in range(n_frames)
        ]

    def _decelerating_marks(self, H, fps, v0_kmh, v1_kmh, n_frames=6, frame_step=25):
        """Sabit ivmeli yavaşlama: v0'dan v1'e. Dünya Y ekseninde hareketi."""
        v0_ms = v0_kmh / 3.6
        v1_ms = v1_kmh / 3.6
        t_total = (n_frames - 1) * frame_step / fps
        # a = (v1 - v0) / t_total (sabit ivme)
        a_ms2 = (v1_ms - v0_ms) / t_total
        marks = []
        y = 0.0
        for i in range(n_frames):
            t = i * frame_step / fps
            y = v0_ms * t + 0.5 * a_ms2 * t ** 2
            pixel = self._world_to_pixel(H, (1.0, y))
            marks.append({"frame": float(i * frame_step), "pixel": list(pixel)})
        return marks

    def test_constant_speed_profile_summary_matches(self):
        """Sabit hızda profil özet değeri wheel_contact_speed ile uyuşmalı."""
        H = self._simple_homography()
        fps = 25.0
        marks = self._uniform_marks(H, fps, speed_kmh=60.0)

        profile = wheel_contact_profile(marks, H, fps)
        assert isinstance(profile, WheelSpeedProfile)
        assert abs(profile.summary.value_kmh - 60.0) < 1.0

    def test_profile_points_count(self):
        """n işaretten n-1 profil noktası elde edilmeli."""
        H = self._simple_homography()
        fps = 25.0
        n = 6
        marks = self._uniform_marks(H, fps, speed_kmh=80.0, n_frames=n)

        profile = wheel_contact_profile(marks, H, fps)
        assert len(profile.points) == n - 1
        assert len(profile.raw_pairwise_kmh) == n - 1

    def test_profile_points_have_ci(self):
        """Her profil noktası CI >= 0 taşımalı."""
        H = self._simple_homography()
        fps = 25.0
        marks = self._uniform_marks(H, fps, speed_kmh=70.0, n_frames=5)

        profile = wheel_contact_profile(marks, H, fps)
        for pt in profile.points:
            assert isinstance(pt, ProfilePoint)
            assert pt.ci_kmh >= 0.0
            assert pt.speed_kmh > 0.0

    def test_deceleration_detected(self):
        """Fren senaryosunda profil başlangıç > bitiş hız olmalı."""
        H = self._simple_homography()
        fps = 25.0
        # 100 km/h → 40 km/h, 6 kare
        marks = self._decelerating_marks(H, fps, v0_kmh=100.0, v1_kmh=40.0, n_frames=6)

        profile = wheel_contact_profile(marks, H, fps)
        assert len(profile.points) >= 2
        first_speed = profile.points[0].speed_kmh
        last_speed = profile.points[-1].speed_kmh
        assert first_speed > last_speed, (
            f"Fren bekleniyor: başlangıç {first_speed:.1f} > bitiş {last_speed:.1f}"
        )

    def test_deceleration_accel_negative(self):
        """Fren senaryosunda iç noktalarda ivme negatif olmalı (yavaşlama)."""
        H = self._simple_homography()
        fps = 25.0
        marks = self._decelerating_marks(H, fps, v0_kmh=90.0, v1_kmh=30.0, n_frames=7)

        profile = wheel_contact_profile(marks, H, fps)
        # İç noktaların (None olmayan) ivmeleri negatif bekleniyor
        interior_accels = [pt.accel_ms2 for pt in profile.points if pt.accel_ms2 is not None]
        assert len(interior_accels) > 0, "İç ivme noktası bulunmalı"
        assert all(a < 0 for a in interior_accels), (
            f"Tüm iç ivmeler negatif bekleniyor: {interior_accels}"
        )

    def test_smoothing_window_audit(self):
        """Smoothing window değeri profil nesnesinde korunmalı (audit trail)."""
        H = self._simple_homography()
        fps = 25.0
        marks = self._uniform_marks(H, fps, speed_kmh=50.0, n_frames=5)

        profile = wheel_contact_profile(marks, H, fps, smoothing_window=5)
        assert profile.smoothing_window == 5

    def test_insufficient_marks_raises(self):
        """1 işaret ValueError fırlatmalı."""
        H = self._simple_homography()
        with pytest.raises(ValueError, match="En az 2"):
            wheel_contact_profile([{"frame": 0, "pixel": [50.0, 50.0]}], H, fps=25.0)

    def test_two_marks_profile_has_one_point_with_warning(self):
        """2 işaretten 1 profil noktası + uyarı bekleniyor."""
        H = self._simple_homography()
        fps = 25.0
        speed_ms = 60.0 / 3.6
        marks = [
            {"frame": 0.0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0)))},
            {"frame": 25.0, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 1.0)))},
        ]
        profile = wheel_contact_profile(marks, H, fps)
        assert len(profile.points) == 1
        assert any("profil" in w.lower() for w in profile.warnings)

    def test_profile_sorted_by_time(self):
        """Profil noktaları artan zaman sırasıyla gelmeli."""
        H = self._simple_homography()
        fps = 25.0
        marks = self._uniform_marks(H, fps, speed_kmh=75.0, n_frames=6)

        profile = wheel_contact_profile(marks, H, fps)
        times = [pt.t_s for pt in profile.points]
        assert times == sorted(times)

    def test_raw_pairwise_preserved(self):
        """Ham ardışık çift hızlar liste olarak korunmalı (audit trail)."""
        H = self._simple_homography()
        fps = 25.0
        marks = self._uniform_marks(H, fps, speed_kmh=80.0, n_frames=5)

        profile = wheel_contact_profile(marks, H, fps)
        assert len(profile.raw_pairwise_kmh) == 4
        for v in profile.raw_pairwise_kmh:
            assert isinstance(v, float)
            assert abs(v - 80.0) < 2.0
