"""R1 kabul testleri — FPS pipeline wiring.

Doğrulananlar:
- fps=30 vs fps=60 ile hız tam 2× değişir (K1 regresyon testi)
- Override verilmezse davranış değişmez
- Kalibrasyon JSON'daki fps de devreye girer (operator_override)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.calibration.models import CalibrationResult, ControlPoint
from src.calibration.io import save_calibration, load_calibration
from src.detection.models import Track, TrackPoint
from src.speed.calculator import estimate_speed


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _identity_H() -> np.ndarray:
    """1 piksel = 1 metre birim homografi (düz yol)."""
    return np.eye(3, dtype=np.float64)


def _straight_track(track_id: int = 1, frames: int = 30, dx_per_frame: float = 1.0) -> Track:
    """Yatay, sabit hızlı sentetik track.

    Her kare contact_pixel x ekseninde dx_per_frame kadar ilerler.
    fps=30 → hız = dx_per_frame * 30 * 3.6 km/h
    """
    points = [
        TrackPoint(
            frame=i,
            t_s=float(i),
            contact_pixel=(float(i * dx_per_frame), 20.0),
            bbox=(float(i * dx_per_frame), 10.0, float(i * dx_per_frame + 20), 30.0),
        )
        for i in range(frames)
    ]
    return Track(track_id=track_id, vehicle_class="car", points=points)


def _make_cal_result() -> CalibrationResult:
    return CalibrationResult(
        homography=_identity_H(),
        used_point_ids=["p1", "p2", "p3", "p4"],
        excluded_point_ids=[],
        reprojection_rms_m=0.01,
        confidence_layer="operator",
        planarity_warning=False,
    )


def _make_control_points() -> list[ControlPoint]:
    return [
        ControlPoint(id="p1", pixel=(0.0, 0.0), world_m=(0.0, 0.0), source="operator"),
        ControlPoint(id="p2", pixel=(5.0, 0.0), world_m=(5.0, 0.0), source="operator"),
        ControlPoint(id="p3", pixel=(5.0, 5.0), world_m=(5.0, 5.0), source="operator"),
        ControlPoint(id="p4", pixel=(0.0, 5.0), world_m=(0.0, 5.0), source="operator"),
    ]


# ── Test 1: FPS değişince hız orantılı değişir ───────────────────────────────

def test_fps_doubles_speed_doubles():
    """fps=60 → hız, fps=30 ile kıyasla yaklaşık 2× olmalı (aynı track)."""
    track = _straight_track(frames=60, dx_per_frame=1.0)
    H = _identity_H()
    cal = _make_cal_result()

    est_30 = estimate_speed(track, H, fps=30.0, calibration_result=cal)
    est_60 = estimate_speed(track, H, fps=60.0, calibration_result=cal)

    # fps=30: dt=1/30 s, v = 1m / (1/30)s * 3.6 = 108 km/h
    # fps=60: dt=1/60 s, v = 1m / (1/60)s * 3.6 = 216 km/h
    ratio = est_60.value_kmh / est_30.value_kmh
    assert abs(ratio - 2.0) < 0.05, f"Oran {ratio:.3f}, beklenen 2.0"


def test_fps_halves_speed_halves():
    """fps=15 → hız, fps=30'un yarısı olmalı."""
    track = _straight_track(frames=30, dx_per_frame=1.0)
    H = _identity_H()
    cal = _make_cal_result()

    est_30 = estimate_speed(track, H, fps=30.0, calibration_result=cal)
    est_15 = estimate_speed(track, H, fps=15.0, calibration_result=cal)

    ratio = est_15.value_kmh / est_30.value_kmh
    assert abs(ratio - 0.5) < 0.05, f"Oran {ratio:.3f}, beklenen 0.5"


# ── Test 2: run_pipeline fps parametresi wiring ───────────────────────────────

def _write_calibration_json(tmp_dir: Path, fps: float | None = None,
                             fps_source: str = "container") -> Path:
    cal = _make_cal_result()
    points = _make_control_points()
    path = tmp_dir / "cal.json"
    save_calibration(path, cal, points, fps=fps, fps_source=fps_source)
    return path


def test_run_pipeline_fps_override_wires_to_speed(tmp_path):
    """run_pipeline fps=60 ile çağrılınca hız, fps=30'a göre ~2× olmalı."""
    from src.output.pipeline import run_pipeline

    cal_path = _write_calibration_json(tmp_path, fps=None, fps_source="container")

    track_30 = _straight_track(frames=60, dx_per_frame=1.0)
    track_60 = _straight_track(frames=60, dx_per_frame=1.0)

    fake_meta_30 = MagicMock()
    fake_meta_30.fps = 30.0
    fake_meta_30.frame_count = 60
    fake_meta_30.width = 320
    fake_meta_30.height = 240
    fake_meta_30.fps_source = "container"

    fake_meta_60 = MagicMock()
    fake_meta_60.fps = 30.0  # konteyner 30 der — ama override 60 verilecek
    fake_meta_60.frame_count = 60
    fake_meta_60.width = 320
    fake_meta_60.height = 240
    fake_meta_60.fps_source = "container"

    def _run(track, meta_mock, fps_override):
        with (
            patch("src.output.pipeline.read_video_meta", return_value=meta_mock),
            patch("src.output.pipeline.VehicleTracker") as MockTracker,
            patch("src.output.pipeline.write_overlay_video"),
            patch("src.output.pipeline.generate_report"),
        ):
            tracker_inst = MockTracker.return_value
            tracker_inst.process_video.return_value = ([track], {})
            result = run_pipeline(
                video_path=tmp_path / "fake.mp4",
                calibration_path=cal_path,
                fps=fps_override,
                fps_source="operator_override" if fps_override else None,
                progress=False,
            )
        return result

    res_30 = _run(track_30, fake_meta_30, fps_override=None)   # konteyner fps=30
    res_60 = _run(track_60, fake_meta_60, fps_override=60.0)   # override fps=60

    speed_30 = res_30.speed_estimates[0].value_kmh if res_30.speed_estimates else 0.0
    speed_60 = res_60.speed_estimates[0].value_kmh if res_60.speed_estimates else 0.0

    assert speed_30 > 0, "30 fps senaryosu hız üretmeli"
    assert speed_60 > 0, "60 fps senaryosu hız üretmeli"
    ratio = speed_60 / speed_30
    assert abs(ratio - 2.0) < 0.15, f"fps 2× farkı hız 2× vermedi: {speed_30:.1f} vs {speed_60:.1f} (oran {ratio:.3f})"


def test_run_pipeline_no_override_uses_container_fps(tmp_path):
    """fps override verilmezse konteyner fps'i kullanır — davranış değişmez."""
    from src.output.pipeline import run_pipeline

    cal_path = _write_calibration_json(tmp_path, fps=None)

    track = _straight_track(frames=30, dx_per_frame=1.0)
    fake_meta = MagicMock()
    fake_meta.fps = 25.0
    fake_meta.frame_count = 30
    fake_meta.width = 320
    fake_meta.height = 240
    fake_meta.fps_source = "container"

    with (
        patch("src.output.pipeline.read_video_meta", return_value=fake_meta),
        patch("src.output.pipeline.VehicleTracker") as MockTracker,
        patch("src.output.pipeline.write_overlay_video"),
        patch("src.output.pipeline.generate_report"),
    ):
        MockTracker.return_value.process_video.return_value = ([track], {})
        result = run_pipeline(
            video_path=tmp_path / "fake.mp4",
            calibration_path=cal_path,
            progress=False,
        )

    assert result.video_meta.fps == 25.0
    assert result.video_meta.fps_source == "container"


# ── Test 3: Kalibrasyon JSON'daki fps override devreye girer ─────────────────

def test_calibration_json_fps_used_when_no_explicit_param(tmp_path):
    """JSON'da fps=50 varsa ve run_pipeline'a fps param verilmezse JSON fps'i kullanılır."""
    from src.output.pipeline import run_pipeline

    cal_path = _write_calibration_json(tmp_path, fps=50.0, fps_source="operator_override")

    track = _straight_track(frames=30, dx_per_frame=1.0)
    fake_meta = MagicMock()
    fake_meta.fps = 25.0  # konteyner 25 der
    fake_meta.frame_count = 30
    fake_meta.width = 320
    fake_meta.height = 240
    fake_meta.fps_source = "container"

    with (
        patch("src.output.pipeline.read_video_meta", return_value=fake_meta),
        patch("src.output.pipeline.VehicleTracker") as MockTracker,
        patch("src.output.pipeline.write_overlay_video"),
        patch("src.output.pipeline.generate_report"),
    ):
        MockTracker.return_value.process_video.return_value = ([track], {})
        result = run_pipeline(
            video_path=tmp_path / "fake.mp4",
            calibration_path=cal_path,
            progress=False,
        )

    assert result.video_meta.fps == 50.0
    assert result.video_meta.fps_source == "operator_override"


# ── Test 4: load_calibration fps döndürüyor ──────────────────────────────────

def test_load_calibration_returns_fps(tmp_path):
    """load_calibration 3-tuple döndürür; fps/fps_source JSON'dan okunur."""
    cal = _make_cal_result()
    points = _make_control_points()
    path = tmp_path / "cal.json"
    save_calibration(path, cal, points, fps=29.97, fps_source="operator_override")

    _, _, (fps_out, fps_src_out) = load_calibration(path)
    assert abs(fps_out - 29.97) < 1e-6
    assert fps_src_out == "operator_override"


def test_load_calibration_returns_none_fps_when_absent(tmp_path):
    """fps kaydedilmemişse (None), load_calibration (None, 'container') döndürür."""
    cal = _make_cal_result()
    points = _make_control_points()
    path = tmp_path / "cal.json"
    save_calibration(path, cal, points, fps=None, fps_source="container")

    _, _, (fps_out, fps_src_out) = load_calibration(path)
    assert fps_out is None
    assert fps_src_out == "container"


# ── R6: Entegrasyon test katmanı ─────────────────────────────────────────────

def test_frame_step_forwarded_to_tracker(tmp_path):
    """frame_step=3 → VehicleTracker.process_video, frame_step=3 keyword arg ile çağrılır."""
    from src.output.pipeline import run_pipeline

    cal_path = _write_calibration_json(tmp_path)
    track = _straight_track(frames=30, dx_per_frame=1.0)
    fake_meta = MagicMock()
    fake_meta.fps = 25.0
    fake_meta.frame_count = 30
    fake_meta.width = 320
    fake_meta.height = 240
    fake_meta.fps_source = "container"

    with (
        patch("src.output.pipeline.read_video_meta", return_value=fake_meta),
        patch("src.output.pipeline.VehicleTracker") as MockTracker,
        patch("src.output.pipeline.write_overlay_video"),
        patch("src.output.pipeline.generate_report"),
    ):
        MockTracker.return_value.process_video.return_value = ([track], {})
        run_pipeline(
            video_path=tmp_path / "fake.mp4",
            calibration_path=cal_path,
            frame_step=3,
            progress=False,
        )

    actual_step = MockTracker.return_value.process_video.call_args.kwargs.get("frame_step")
    assert actual_step == 3, f"frame_step=3 bekleniyordu, gelen: {actual_step}"


def test_sha256_propagated_to_pipeline_result(tmp_path):
    """run_pipeline(..., video_sha256=X) → PipelineResult.video_sha256 == X."""
    from src.output.pipeline import run_pipeline

    cal_path = _write_calibration_json(tmp_path)
    track = _straight_track(frames=30, dx_per_frame=1.0)
    fake_meta = MagicMock()
    fake_meta.fps = 25.0
    fake_meta.frame_count = 30
    fake_meta.width = 320
    fake_meta.height = 240
    fake_meta.fps_source = "container"

    expected_sha = "a" * 64

    with (
        patch("src.output.pipeline.read_video_meta", return_value=fake_meta),
        patch("src.output.pipeline.VehicleTracker") as MockTracker,
        patch("src.output.pipeline.write_overlay_video"),
        patch("src.output.pipeline.generate_report"),
    ):
        MockTracker.return_value.process_video.return_value = ([track], {})
        result = run_pipeline(
            video_path=tmp_path / "fake.mp4",
            calibration_path=cal_path,
            video_sha256=expected_sha,
            progress=False,
        )

    assert result.video_sha256 == expected_sha


def test_e2e_run_pipeline_real_video(tmp_path):
    """Gerçek mp4 dosyası + kalibrasyon JSON → run_pipeline tam zincir (YOLO mock'lu).

    Doğrulanır: fps override, frame_step, sha256, hız hesabı hepsi uçtan uca çalışır.
    """
    import cv2
    from src.output.pipeline import run_pipeline

    # Sentetik video dosyası yaz
    video_path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, 25.0, (320, 240))
    rng = np.random.default_rng(42)
    for _ in range(30):
        frame = (rng.random((240, 320, 3)) * 255).astype(np.uint8)
        writer.write(frame)
    writer.release()

    # Kalibrasyon JSON yaz (fps yok → override=30 kullanılacak)
    cal_path = tmp_path / "cal.json"
    save_calibration(cal_path, _make_cal_result(), _make_control_points(),
                     fps=None, fps_source="container")

    # 0.5 m/frame × 30 fps × 3.6 = 54 km/h beklenir (kimlik H ile)
    track = _straight_track(frames=25, dx_per_frame=0.5)
    sha_val = "b" * 64

    with (
        patch("src.output.pipeline.VehicleTracker") as MockTracker,
        patch("src.output.pipeline.write_overlay_video"),
        patch("src.output.pipeline.generate_report"),
    ):
        MockTracker.return_value.process_video.return_value = ([track], {})
        result = run_pipeline(
            video_path=video_path,
            calibration_path=cal_path,
            fps=30.0,
            fps_source="operator_override",
            video_sha256=sha_val,
            frame_step=2,
            progress=False,
        )

    assert len(result.speed_estimates) >= 1
    assert abs(result.speed_estimates[0].value_kmh - 54.0) < 5.0, (
        f"Beklenen ~54 km/h, gelen: {result.speed_estimates[0].value_kmh:.1f}"
    )
    assert result.video_sha256 == sha_val
    assert result.video_meta.fps == 30.0
    assert result.video_meta.fps_source == "operator_override"
    assert result.frame_step == 2
    assert result.plan_view_png is not None
    assert result.plan_view_png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG dosya imzası


def test_plan_view_failure_does_not_crash_pipeline(tmp_path):
    """compute_plan_view hata verirse pipeline yine tamamlanmalı, plan_view_png=None kalmalı."""
    import cv2
    from src.output.pipeline import run_pipeline

    video_path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, 25.0, (320, 240))
    rng = np.random.default_rng(7)
    for _ in range(10):
        writer.write((rng.random((240, 320, 3)) * 255).astype(np.uint8))
    writer.release()

    cal_path = tmp_path / "cal.json"
    save_calibration(cal_path, _make_cal_result(), _make_control_points(),
                     fps=None, fps_source="container")
    track = _straight_track(frames=8, dx_per_frame=0.5)

    with (
        patch("src.output.pipeline.VehicleTracker") as MockTracker,
        patch("src.output.pipeline.write_overlay_video"),
        patch("src.output.pipeline.generate_report"),
        patch("src.output.pipeline.compute_plan_view", side_effect=RuntimeError("boom")),
    ):
        MockTracker.return_value.process_video.return_value = ([track], {})
        result = run_pipeline(
            video_path=video_path,
            calibration_path=cal_path,
            fps=30.0,
            progress=False,
        )

    assert result.plan_view_png is None
    assert len(result.speed_estimates) >= 1
