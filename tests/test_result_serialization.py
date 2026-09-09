"""T6 kabul testleri — PipelineResult round-trip JSON serileştirme."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from src.calibration.models import CalibrationResult, ControlPoint
from src.detection.models import Track, TrackPoint
from src.detection.video import VideoMeta
from src.output.models import PipelineResult
from src.output.serialization import (
    read_result_data,
    result_from_dict,
    result_to_dict,
    write_result_data,
)
from src.speed.models import SpeedEstimate, SpeedSample, TrackQuality


def _make_pipeline_result(with_plan_view: bool = False) -> PipelineResult:
    H = np.eye(3, dtype=np.float64)
    H[0, 2] = 0.5  # 항등 değil ama deterministik

    cal = CalibrationResult(
        homography=H,
        used_point_ids=["p1", "p2", "p3", "p4"],
        excluded_point_ids=["p5"],
        reprojection_rms_m=0.023,
        confidence_layer="operator",
        planarity_warning=False,
        planarity_evaluated=True,
        holdout_rows=[{"id": "p5", "measured_m": (0.0, 1.0), "predicted_m": (0.01, 0.99), "error_m": 0.014}],
        loo_rms_m=0.031,
    )

    points = [TrackPoint(frame=i, t_s=float(i) / 30.0, contact_pixel=(float(i), 20.0), bbox=(float(i), 10.0, float(i) + 20, 30.0)) for i in range(5)]
    track = Track(track_id=7, vehicle_class="car", points=points)

    samples = [SpeedSample(frame=p.frame, t_s=p.t_s, world_m=(float(p.frame), 20.0), speed_kmh=50.0 + p.frame) for p in points[1:]]
    est = SpeedEstimate(
        track_id=7,
        value_kmh=52.3,
        ci_kmh=3.1,
        confidence_level="high",
        speed_series=samples,
        smoothed_series=[(s.t_s, s.speed_kmh) for s in samples],
        track_quality=TrackQuality(frame_count=5, has_occlusion=False, smoothness_residual=0.8),
    )

    cps = [
        ControlPoint(id="p1", pixel=(10.0, 20.0), world_m=(0.0, 0.0), source="operator", held_out=False),
        ControlPoint(id="p2", pixel=(100.0, 20.0), world_m=(3.5, 0.0), source="operator", held_out=False),
        ControlPoint(id="p3", pixel=(100.0, 80.0), world_m=(3.5, 7.0), source="operator", held_out=False),
        ControlPoint(id="p4", pixel=(10.0, 80.0), world_m=(0.0, 7.0), source="operator", held_out=False),
    ]

    return PipelineResult(
        video_path="/tmp/test.mp4",
        video_meta=VideoMeta(fps=30.0, frame_count=300, width=1280, height=720, fps_source="container"),
        calibration_result=cal,
        control_points=cps,
        speed_estimates=[est],
        tracks=[track],
        processed_at=datetime.now(timezone.utc).isoformat(),
        frame_step=2,
        model_name="yolo11n.pt",
        video_sha256="abc123",
        plan_view_png=b"\x89PNG\r\n\x1a\n" if with_plan_view else None,
    )


def _assert_results_equal(a: PipelineResult, b: PipelineResult) -> None:
    assert a.video_path == b.video_path
    assert a.processed_at == b.processed_at
    assert a.frame_step == b.frame_step
    assert a.model_name == b.model_name
    assert a.video_sha256 == b.video_sha256
    assert a.plan_view_png == b.plan_view_png

    # VideoMeta
    assert a.video_meta.fps == b.video_meta.fps
    assert a.video_meta.frame_count == b.video_meta.frame_count
    assert a.video_meta.width == b.video_meta.width
    assert a.video_meta.height == b.video_meta.height
    assert a.video_meta.fps_source == b.video_meta.fps_source

    # CalibrationResult
    np.testing.assert_array_almost_equal(a.calibration_result.homography, b.calibration_result.homography)
    assert a.calibration_result.used_point_ids == b.calibration_result.used_point_ids
    assert a.calibration_result.excluded_point_ids == b.calibration_result.excluded_point_ids
    assert abs(a.calibration_result.reprojection_rms_m - b.calibration_result.reprojection_rms_m) < 1e-9
    assert a.calibration_result.confidence_layer == b.calibration_result.confidence_layer
    assert a.calibration_result.planarity_warning == b.calibration_result.planarity_warning
    assert a.calibration_result.planarity_evaluated == b.calibration_result.planarity_evaluated
    assert a.calibration_result.loo_rms_m == b.calibration_result.loo_rms_m

    # ControlPoints
    assert len(a.control_points) == len(b.control_points)
    for ca, cb in zip(a.control_points, b.control_points):
        assert ca.id == cb.id
        assert ca.pixel == cb.pixel
        assert ca.world_m == cb.world_m
        assert ca.source == cb.source
        assert ca.held_out == cb.held_out

    # Tracks
    assert len(a.tracks) == len(b.tracks)
    for ta, tb in zip(a.tracks, b.tracks):
        assert ta.track_id == tb.track_id
        assert ta.vehicle_class == tb.vehicle_class
        assert len(ta.points) == len(tb.points)
        for pa, pb in zip(ta.points, tb.points):
            assert pa.frame == pb.frame
            assert abs(pa.t_s - pb.t_s) < 1e-9
            assert pa.contact_pixel == pb.contact_pixel
            assert pa.bbox == pb.bbox

    # SpeedEstimates
    assert len(a.speed_estimates) == len(b.speed_estimates)
    for ea, eb in zip(a.speed_estimates, b.speed_estimates):
        assert ea.track_id == eb.track_id
        assert abs(ea.value_kmh - eb.value_kmh) < 1e-6
        assert abs(ea.ci_kmh - eb.ci_kmh) < 1e-6
        assert ea.confidence_level == eb.confidence_level
        assert len(ea.speed_series) == len(eb.speed_series)
        assert len(ea.smoothed_series) == len(eb.smoothed_series)
        assert ea.track_quality.frame_count == eb.track_quality.frame_count
        assert ea.track_quality.has_occlusion == eb.track_quality.has_occlusion


class TestRoundTrip:
    def test_to_dict_from_dict(self):
        result = _make_pipeline_result()
        d = result_to_dict(result)
        # JSON-serileştirilebilir olmalı
        raw = json.dumps(d)
        d2 = json.loads(raw)
        restored = result_from_dict(d2)
        _assert_results_equal(result, restored)

    def test_with_plan_view_png(self):
        result = _make_pipeline_result(with_plan_view=True)
        assert result.plan_view_png is not None
        d = result_to_dict(result)
        assert isinstance(d["plan_view_png"], str)
        restored = result_from_dict(d)
        assert restored.plan_view_png == result.plan_view_png

    def test_write_and_read_result_data(self, tmp_path):
        result = _make_pipeline_result()
        path = write_result_data(result, tmp_path)
        assert path.exists()
        assert path.name == "result_data.json"
        restored = read_result_data(tmp_path)
        _assert_results_equal(result, restored)

    def test_json_is_valid_utf8(self, tmp_path):
        result = _make_pipeline_result()
        path = write_result_data(result, tmp_path)
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "video_path" in data
        assert "calibration_result" in data
        assert "speed_estimates" in data

    def test_homography_preserved(self):
        H = np.array([[1.1, 0.2, -3.0], [0.0, 1.5, 100.0], [0.001, 0.0, 1.0]])
        result = _make_pipeline_result()
        result.calibration_result.homography = H
        restored = result_from_dict(result_to_dict(result))
        np.testing.assert_array_almost_equal(H, restored.calibration_result.homography, decimal=10)
