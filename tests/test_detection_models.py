"""Unit tests for M2 models, contact point, occlusion gap, and video reading."""
from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.detection.models import (
    Detection, TrackPoint, Track,
    VEHICLE_CLASSES, VEHICLE_CLASS_IDS,
    contact_point, compute_occlusion_gaps,
)
from src.detection.video import read_video_meta, iter_video_frames


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_synthetic_video(
    path: Path,
    n_frames: int = 30,
    fps: float = 25.0,
    width: int = 640,
    height: int = 480,
) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    for i in range(n_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        x = 50 + i * 10
        cv2.rectangle(frame, (x, 200), (min(x + 120, width - 1), 280), (0, 200, 0), -1)
        writer.write(frame)
    writer.release()


# ── Test 1: Contact point ─────────────────────────────────────────────────────

def test_contact_point_center_bottom():
    bbox = (100.0, 50.0, 300.0, 250.0)
    cp = contact_point(bbox)
    assert cp == (200.0, 250.0), f"Expected (200.0, 250.0), got {cp}"


def test_contact_point_not_bbox_center():
    bbox = (0.0, 0.0, 200.0, 100.0)
    cp = contact_point(bbox)
    bbox_center = (100.0, 50.0)
    assert cp != bbox_center, "contact_point must not be the bbox center"
    assert cp == (100.0, 100.0)


# ── Test 2: Class filter ──────────────────────────────────────────────────────

def test_vehicle_classes_content():
    assert VEHICLE_CLASSES == {"car", "truck", "bus", "motorcycle"}


def test_vehicle_class_ids_content():
    assert VEHICLE_CLASS_IDS == {2, 3, 5, 7}


def test_non_vehicle_not_in_classes():
    assert "person" not in VEHICLE_CLASSES
    assert "bicycle" not in VEHICLE_CLASSES
    assert "dog" not in VEHICLE_CLASSES


# ── Test 5: Occlusion gap ─────────────────────────────────────────────────────

def test_no_gap():
    frames = [10, 11, 12, 13]
    assert compute_occlusion_gaps(frames) == []


def test_single_gap():
    frames = [10, 11, 15, 16]
    gaps = compute_occlusion_gaps(frames)
    assert gaps == [(12, 14)]


def test_multiple_gaps():
    frames = [1, 2, 5, 6, 10]
    gaps = compute_occlusion_gaps(frames)
    assert gaps == [(3, 4), (7, 9)]


def test_empty_frame_list():
    assert compute_occlusion_gaps([]) == []


def test_single_frame_no_gap():
    assert compute_occlusion_gaps([42]) == []


# ── Test 3 & 6: VideoMeta reading ────────────────────────────────────────────

def test_read_video_meta():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=30, fps=25.0, width=640, height=480)

        meta = read_video_meta(path)

    assert meta.fps == pytest.approx(25.0, abs=0.1)
    assert meta.width == 640
    assert meta.height == 480
    assert meta.frame_count == 30
    assert meta.fps_source == "container"


def test_read_video_meta_invalid_path():
    with pytest.raises(IOError):
        read_video_meta("/nonexistent/video.mp4")


# ── Test 3: iter_video_frames ─────────────────────────────────────────────────

def test_iter_video_frames_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=30)

        frames = list(iter_video_frames(path))

    assert len(frames) == 30
    for i, (idx, frame) in enumerate(frames):
        assert idx == i
        assert frame.shape == (480, 640, 3)


def test_iter_video_frames_step():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=30)

        frames = list(iter_video_frames(path, frame_step=3))

    # Frames 0, 3, 6, ..., 27 → 10 frames
    assert len(frames) == 10
    assert frames[0][0] == 0
    assert frames[1][0] == 3


# ── Track dataclass sanity ────────────────────────────────────────────────────

def test_track_dataclass_defaults():
    t = Track(track_id=1, vehicle_class="car")
    assert t.points == []
    assert t.occlusion_gaps == []


def test_track_point_fields():
    tp = TrackPoint(frame=5, t_s=0.2, contact_pixel=(320.0, 240.0), bbox=(200.0, 100.0, 440.0, 240.0))
    assert tp.frame == 5
    assert tp.t_s == pytest.approx(0.2)
    assert tp.contact_pixel == (320.0, 240.0)
