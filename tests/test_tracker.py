"""Unit tests for VehicleTracker using mocked YOLO model."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
import torch

from src.detection.models import VEHICLE_CLASSES, contact_point
from src.detection.video import read_video_meta


# ── Synthetic video helper ────────────────────────────────────────────────────

def _make_synthetic_video(path: Path, n_frames: int = 20, fps: float = 25.0) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (640, 480))
    for i in range(n_frames):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        x = 50 + i * 15
        cv2.rectangle(frame, (x, 200), (min(x + 120, 639), 280), (0, 200, 0), -1)
        writer.write(frame)
    writer.release()


def _make_fake_box(tid: int, frame: int, x_offset: int = 0):
    """Create a mock Ultralytics box result for a single tracked vehicle."""
    box = MagicMock()
    x1, y1, x2, y2 = 50.0 + x_offset, 200.0, 170.0 + x_offset, 280.0
    box.xyxy = torch.tensor([[x1, y1, x2, y2]])
    box.id = torch.tensor([tid], dtype=torch.float32)
    box.cls = torch.tensor([2], dtype=torch.float32)   # car
    box.conf = torch.tensor([0.85])
    return box


def _make_fake_result(tid: int, frame: int, x_offset: int = 0):
    result = MagicMock()
    boxes = _make_fake_box(tid, frame, x_offset)
    # Simulate Ultralytics API: boxes.id, boxes.xyxy, etc.
    result.boxes = MagicMock()
    result.boxes.id = boxes.id
    result.boxes.xyxy = boxes.xyxy
    result.boxes.cls = boxes.cls
    result.boxes.conf = boxes.conf
    result.names = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
    return result


# ── Test 7: device="auto" safe on CPU ────────────────────────────────────────

def test_device_auto_resolves_to_cpu_without_cuda():
    from src.detection.tracker import _resolve_device
    with patch("torch.cuda.is_available", return_value=False):
        assert _resolve_device("auto") == "cpu"


def test_device_explicit_passed_through():
    from src.detection.tracker import _resolve_device
    assert _resolve_device("cpu") == "cpu"
    assert _resolve_device("cuda") == "cuda"


# ── Test 4: VehicleTracker builds Track objects from mocked YOLO ──────────────

def test_tracker_builds_tracks_from_mock():
    from src.detection.tracker import VehicleTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=10)

        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model

            # Return a single tracked "car" in every frame
            def fake_track(frame, **kwargs):
                return [_make_fake_result(tid=1, frame=0, x_offset=0)]

            mock_model.track.side_effect = fake_track

            tracker = VehicleTracker.__new__(VehicleTracker)
            tracker._device = "cpu"
            tracker._conf = 0.25
            tracker._tracker_config = "bytetrack.yaml"
            tracker._model = mock_model

            tracks, meta = tracker.process_video(path)

    assert len(tracks) >= 1
    t = tracks[0]
    assert t.track_id == 1
    assert t.vehicle_class == "car"
    assert len(t.points) == 10  # one point per frame


def test_tracker_contact_points_are_bottom_center():
    from src.detection.tracker import VehicleTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=5)

        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model
            mock_model.track.return_value = [_make_fake_result(tid=2, frame=0, x_offset=0)]

            tracker = VehicleTracker.__new__(VehicleTracker)
            tracker._device = "cpu"
            tracker._conf = 0.25
            tracker._tracker_config = "bytetrack.yaml"
            tracker._model = mock_model

            tracks, _ = tracker.process_video(path)

    assert len(tracks) == 1
    tp = tracks[0].points[0]
    x1, y1, x2, y2 = tp.bbox
    expected = contact_point(tp.bbox)
    assert tp.contact_pixel == expected
    assert tp.contact_pixel[1] == y2  # must be bottom, not center


def test_tracker_non_vehicle_classes_excluded():
    from src.detection.tracker import VehicleTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=5)

        def fake_result_person():
            result = MagicMock()
            result.boxes = MagicMock()
            result.boxes.id = torch.tensor([99], dtype=torch.float32)
            result.boxes.xyxy = torch.tensor([[10.0, 10.0, 60.0, 180.0]])
            result.boxes.cls = torch.tensor([0])   # person — not a vehicle
            result.boxes.conf = torch.tensor([0.9])
            result.names = {0: "person", 2: "car"}
            return result

        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model
            mock_model.track.return_value = [fake_result_person()]

            tracker = VehicleTracker.__new__(VehicleTracker)
            tracker._device = "cpu"
            tracker._conf = 0.25
            tracker._tracker_config = "bytetrack.yaml"
            tracker._model = mock_model

            tracks, _ = tracker.process_video(path)

    assert len(tracks) == 0, "Person detections must be excluded from tracks"


def test_tracker_occlusion_gaps_detected():
    """Track missing for some frames → occlusion_gaps populated."""
    from src.detection.tracker import VehicleTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.mp4"
        _make_synthetic_video(path, n_frames=10)

        call_count = [0]

        def fake_track_with_gap(frame, **kwargs):
            i = call_count[0]
            call_count[0] += 1
            # Frames 3,4,5 have no detections (simulated gap)
            if i in (3, 4, 5):
                r = MagicMock()
                r.boxes = MagicMock()
                r.boxes.id = None
                return [r]
            return [_make_fake_result(tid=7, frame=i, x_offset=i * 10)]

        with patch("ultralytics.YOLO") as MockYOLO:
            mock_model = MagicMock()
            MockYOLO.return_value = mock_model
            mock_model.track.side_effect = fake_track_with_gap

            tracker = VehicleTracker.__new__(VehicleTracker)
            tracker._device = "cpu"
            tracker._conf = 0.25
            tracker._tracker_config = "bytetrack.yaml"
            tracker._model = mock_model

            tracks, _ = tracker.process_video(path)

    assert len(tracks) == 1
    assert len(tracks[0].occlusion_gaps) > 0
