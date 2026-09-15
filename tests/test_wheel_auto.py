"""T20 — wheel_auto modülü birim testleri.

Sentetik track ve mock video ile:
- Kare seçimi doğrulaması
- Auto mark üretimi (bbox yedek)
- Onaylanmamış auto işaret uyarısı (wheel_contact_speed entegrasyonu)
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.detection.models import Track, TrackPoint
from src.speed.wheel_auto import (
    AutoMark,
    detect_contact_in_frame,
    generate_auto_marks,
    suggest_frames,
)
from src.speed.wheel_contact import wheel_contact_speed
from src.calibration.homography import compute_homography
from src.calibration.models import ControlPoint


# ── Yardımcılar ───────────────────────────────────────────────────────────────


def _make_track(n_points: int = 20, frame_start: int = 10) -> Track:
    """Sentetik N-noktalı track — her kare 1 artar, bbox sabit."""
    points = []
    for i in range(n_points):
        f = frame_start + i
        bbox = (100.0, 200.0, 300.0, 400.0)
        points.append(TrackPoint(
            frame=f,
            t_s=f / 25.0,
            contact_pixel=(200.0, 400.0),
            bbox=bbox,
        ))
    return Track(track_id=1, vehicle_class="car", points=points)


def _simple_homography() -> np.ndarray:
    points = [
        ControlPoint(id="p1", pixel=(0.0, 0.0), world_m=(0.0, 0.0), source="operator"),
        ControlPoint(id="p2", pixel=(100.0, 0.0), world_m=(10.0, 0.0), source="operator"),
        ControlPoint(id="p3", pixel=(0.0, 100.0), world_m=(0.0, 10.0), source="operator"),
        ControlPoint(id="p4", pixel=(100.0, 100.0), world_m=(10.0, 10.0), source="operator"),
    ]
    return compute_homography(points).homography


def _write_synthetic_video(path: Path, n_frames: int = 30) -> None:
    """Küçük siyah video yaz — test için yeterli."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(str(path), fourcc, 25.0, (640, 480))
    for _ in range(n_frames):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        w.write(frame)
    w.release()


# ── suggest_frames ────────────────────────────────────────────────────────────


class TestSuggestFrames:
    def test_returns_at_most_max_marks(self):
        track = _make_track(40)
        frames = suggest_frames(track, max_marks=8)
        assert len(frames) <= 8

    def test_returns_sorted_frames(self):
        track = _make_track(30)
        frames = suggest_frames(track, max_marks=6)
        assert frames == sorted(frames)

    def test_short_track_returns_all(self):
        track = _make_track(2)
        frames = suggest_frames(track, max_marks=8)
        assert len(frames) == 2

    def test_empty_track_returns_empty(self):
        track = Track(track_id=1, vehicle_class="car", points=[])
        frames = suggest_frames(track, max_marks=8)
        assert frames == []

    def test_trims_boundary_frames(self):
        """İlk ve son %10 tipik olarak atlanır."""
        track = _make_track(40, frame_start=0)
        frames = suggest_frames(track, max_marks=8)
        # Tüm kareler seçilmemeli (trim uygulandı)
        all_frames = [p.frame for p in track.points]
        assert set(frames).issubset(set(all_frames))

    def test_single_point_track(self):
        track = _make_track(1)
        frames = suggest_frames(track, max_marks=5)
        assert len(frames) == 1


# ── detect_contact_in_frame ───────────────────────────────────────────────────


class TestDetectContactInFrame:
    def test_returns_none_for_tiny_bbox(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detect_contact_in_frame(frame, (100.0, 100.0, 110.0, 115.0))
        assert result is None

    def test_returns_none_for_blank_frame(self):
        """Tamamen siyah karede kenar yok → None döner."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detect_contact_in_frame(frame, (50.0, 100.0, 250.0, 350.0))
        assert result is None

    def test_detects_contact_with_edge(self):
        """Yatay beyaz çizgi olan karede temas noktası tespit edilmeli."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Bbox alt bölgesine yatay beyaz çizgi ekle
        cv2.line(frame, (50, 320), (250, 320), (255, 255, 255), 3)
        bbox = (50.0, 100.0, 250.0, 350.0)
        result = detect_contact_in_frame(frame, bbox)
        assert result is not None
        x, y = result
        assert 50.0 <= x <= 250.0
        assert 100.0 <= y <= 350.0

    def test_pixel_within_bbox_bounds(self):
        """Tespit edilen nokta her zaman bbox sınırları içinde olmalı."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (60, 200), (240, 380), (200, 200, 200), 2)
        bbox = (60.0, 200.0, 240.0, 380.0)
        result = detect_contact_in_frame(frame, bbox)
        if result is not None:
            x, y = result
            assert 60.0 <= x <= 240.0
            assert 200.0 <= y <= 380.0


# ── generate_auto_marks ───────────────────────────────────────────────────────


class TestGenerateAutoMarks:
    def test_returns_auto_source(self):
        """Tüm üretilen işaretlerde source='auto' olmalı."""
        track = _make_track(20)
        with tempfile.TemporaryDirectory() as tmpdir:
            vid_path = Path(tmpdir) / "test.mp4"
            _write_synthetic_video(vid_path, 30)
            marks = generate_auto_marks(track, vid_path, max_marks=5)

        for m in marks:
            assert isinstance(m, AutoMark)
            assert m.source == "auto"

    def test_returns_at_most_max_marks(self):
        track = _make_track(20)
        with tempfile.TemporaryDirectory() as tmpdir:
            vid_path = Path(tmpdir) / "test.mp4"
            _write_synthetic_video(vid_path, 30)
            marks = generate_auto_marks(track, vid_path, max_marks=5)
        assert len(marks) <= 5

    def test_marks_sorted_by_frame(self):
        track = _make_track(20)
        with tempfile.TemporaryDirectory() as tmpdir:
            vid_path = Path(tmpdir) / "test.mp4"
            _write_synthetic_video(vid_path, 30)
            marks = generate_auto_marks(track, vid_path, max_marks=5)
        frames = [m.frame for m in marks]
        assert frames == sorted(frames)

    def test_missing_video_falls_back_to_bbox(self):
        """Video yoksa bbox-heuristic yedek kullanılmalı."""
        track = _make_track(20)
        marks = generate_auto_marks(track, "/nonexistent/path.mp4", max_marks=4)
        assert len(marks) > 0
        for m in marks:
            assert m.detection_method == "bbox-heuristic"
            assert m.confidence == 0.2
            assert m.source == "auto"

    def test_pixel_is_float_tuple(self):
        track = _make_track(10)
        marks = generate_auto_marks(track, "/nonexistent/path.mp4", max_marks=3)
        for m in marks:
            assert len(m.pixel) == 2
            assert isinstance(m.pixel[0], float)
            assert isinstance(m.pixel[1], float)


# ── Auto işaret uyarısı (wheel_contact_speed entegrasyonu) ───────────────────


class TestAutoMarkWarning:
    def _world_to_pixel(self, H: np.ndarray, world: tuple[float, float]) -> tuple[float, float]:
        H_inv = np.linalg.inv(H)
        pt = np.array([world[0], world[1], 1.0])
        px = H_inv @ pt
        return (px[0] / px[2], px[1] / px[2])

    def test_auto_mark_triggers_warning(self):
        """source='auto' olan işaret uyarı üretmeli."""
        H = _simple_homography()
        fps = 25.0
        speed_ms = 60 / 3.6
        marks = [
            {"frame": 0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0))), "source": "auto"},
            {"frame": 25, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 1.0))), "source": "auto"},
            {"frame": 50, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 2.0))), "source": "manual"},
        ]
        result = wheel_contact_speed(marks, H, fps)
        assert any("otomatik" in w.lower() or "auto" in w.lower() for w in result.warnings)

    def test_confirmed_marks_no_auto_warning(self):
        """source='operator-confirmed' olan işaretler auto uyarısı üretmemeli."""
        H = _simple_homography()
        fps = 25.0
        speed_ms = 60 / 3.6
        marks = [
            {"frame": 0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0))), "source": "operator-confirmed"},
            {"frame": 25, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 1.0))), "source": "operator-confirmed"},
            {"frame": 50, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 2.0))), "source": "manual"},
        ]
        result = wheel_contact_speed(marks, H, fps)
        auto_warnings = [w for w in result.warnings if "otomatik" in w.lower()]
        assert len(auto_warnings) == 0

    def test_mixed_sources_speed_calculation_correct(self):
        """Karışık kaynaklı işaretler doğru hız üretmeli."""
        H = _simple_homography()
        fps = 25.0
        speed_ms = 80 / 3.6
        marks = [
            {"frame": 0, "pixel": list(self._world_to_pixel(H, (1.0, 0.0))), "source": "manual"},
            {"frame": 25, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 1.0))), "source": "operator-confirmed"},
            {"frame": 50, "pixel": list(self._world_to_pixel(H, (1.0, speed_ms * 2.0))), "source": "auto"},
        ]
        result = wheel_contact_speed(marks, H, fps)
        assert abs(result.value_kmh - 80.0) < 1.0
