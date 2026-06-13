"""Acceptance tests for M5 — PDF report generation."""
from __future__ import annotations

import numpy as np
import pytest

from src.calibration.models import CalibrationResult, ControlPoint
from src.detection.models import Track, TrackPoint
from src.detection.video import VideoMeta
from src.output.models import PipelineResult
from src.output.report import generate_report, collect_report_texts, _build_story
from src.speed.models import SpeedEstimate, SpeedSample, TrackQuality


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_cal(layer="operator", rms=0.15, planarity=False) -> CalibrationResult:
    return CalibrationResult(
        homography=np.eye(3),
        used_point_ids=["p1", "p2", "p3", "p4"],
        excluded_point_ids=[],
        reprojection_rms_m=rms,
        confidence_layer=layer,
        planarity_warning=planarity,
    )


def _make_control_points() -> list[ControlPoint]:
    return [
        ControlPoint(id="p1", pixel=(100.0, 200.0), world_m=(0.0, 0.0), source="operator"),
        ControlPoint(id="p2", pixel=(200.0, 200.0), world_m=(3.5, 0.0), source="operator"),
        ControlPoint(id="p3", pixel=(100.0, 300.0), world_m=(0.0, 5.0), source="operator"),
        ControlPoint(id="p4", pixel=(200.0, 300.0), world_m=(3.5, 5.0), source="operator"),
    ]


def _make_estimate(track_id: int, speed=60.0, confidence="medium",
                   frames=20, occlusion=False) -> SpeedEstimate:
    samples = [
        SpeedSample(frame=i, t_s=i / 25.0, world_m=(float(i), 0.0),
                    speed_kmh=speed if i > 0 else 0.0)
        for i in range(frames)
    ]
    return SpeedEstimate(
        track_id=track_id,
        value_kmh=speed,
        ci_kmh=3.0,
        confidence_level=confidence,
        speed_series=samples,
        smoothed_series=[(s.t_s, speed) for s in samples],
        track_quality=TrackQuality(
            frame_count=frames, has_occlusion=occlusion, smoothness_residual=2.0),
    )


def _make_track(track_id: int) -> Track:
    tp = TrackPoint(frame=0, t_s=0.0, contact_pixel=(150.0, 200.0),
                    bbox=(100.0, 150.0, 200.0, 200.0))
    return Track(track_id=track_id, vehicle_class="car", points=[tp])


def _make_result(**kwargs) -> PipelineResult:
    defaults = dict(
        video_path="/tmp/test.mp4",
        video_meta=VideoMeta(fps=25.0, frame_count=625, width=1920, height=1080),
        calibration_result=_make_cal(),
        control_points=_make_control_points(),
        speed_estimates=[_make_estimate(1), _make_estimate(2, speed=90.0, confidence="low")],
        tracks=[_make_track(1), _make_track(2)],
        processed_at="2026-06-13T10:00:00+00:00",
    )
    defaults.update(kwargs)
    return PipelineResult(**defaults)


def _story_text(result: PipelineResult) -> str:
    """Story'deki tüm Paragraph metinlerini birleştir."""
    from reportlab.platypus import Paragraph as P
    parts = []
    for item in _build_story(result):
        if isinstance(item, P):
            parts.append(item.text)
        elif hasattr(item, "_cellvalues"):   # Table
            for row in item._cellvalues:
                for cell in row:
                    parts.append(str(cell))
    return " ".join(parts)


# ── Test 5: PDF dosyası oluşur ────────────────────────────────────────────────

def test_generate_report_creates_pdf(tmp_path):
    result = _make_result()
    out = tmp_path / "report.pdf"
    generate_report(result, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_generate_report_is_pdf_format(tmp_path):
    result = _make_result()
    out = tmp_path / "report.pdf"
    generate_report(result, out)
    header = out.read_bytes()[:4]
    assert header == b"%PDF", f"PDF sihirli sayi bekleniyor, alinan: {header!r}"


# ── Test 6: PDF zorunlu bölümleri içerir ─────────────────────────────────────

def test_report_contains_kalibrasyon_section():
    result = _make_result()
    texts = collect_report_texts(result)
    combined = " ".join(texts)
    assert "Kalibrasyon" in combined, "Rapor 'Kalibrasyon' bölümünü içermeli"


def test_report_contains_hiz_section():
    result = _make_result()
    text = _story_text(result)
    assert "Hiz" in text or "hiz" in text.lower(), "Rapor hız bölümünü içermeli"


def test_report_contains_varsayimlar_section():
    result = _make_result()
    text = _story_text(result)
    assert "Varsayim" in text, "Rapor 'Varsayımlar' bölümünü içermeli"


# ── Test 7: Planarity uyarısı raporlanır ──────────────────────────────────────

def test_report_shows_planarity_warning():
    result = _make_result(calibration_result=_make_cal(planarity=True))
    texts = collect_report_texts(result)
    combined = " ".join(texts)
    assert "UYARI" in combined, "Planarity uyarısı raporda yer almalı"


def test_report_no_planarity_warning_when_absent():
    result = _make_result(calibration_result=_make_cal(planarity=False))
    texts = collect_report_texts(result)
    combined = " ".join(texts)
    assert "UYARI" not in combined, "Uyarı yoksa 'UYARI' metni olmamalı"


# ── Test 8: Düşük kare uyarısı ───────────────────────────────────────────────

def test_report_flags_low_frame_count():
    """Kare sayısı < 5 olan track için uyarı notu olmalı."""
    result = _make_result(
        speed_estimates=[_make_estimate(1, frames=3)],
        tracks=[_make_track(1)],
    )
    texts = collect_report_texts(result)
    combined = " ".join(texts)
    assert "yetersiz" in combined.lower(), "Az karelı track için uyarı olmalı"


def test_report_no_low_frame_warning_for_normal_tracks():
    result = _make_result()  # varsayılan frames=20 — uyarı olmamalı
    texts = collect_report_texts(result)
    combined = " ".join(texts)
    assert "yetersiz" not in combined.lower()


# ── Test 9: Pipeline uçtan uca (mock tracker) ─────────────────────────────────

def test_run_pipeline_returns_result(tmp_path, monkeypatch):
    """Gerçek YOLO olmadan pipeline PipelineResult döndürür."""
    import cv2
    from src.output import pipeline as pipe_mod

    video_path = tmp_path / "v.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(str(video_path), fourcc, 25.0, (320, 240))
    for _ in range(5):
        w.write(np.zeros((240, 320, 3), dtype=np.uint8))
    w.release()

    import json
    cal_path = tmp_path / "cal.json"
    cal_path.write_text(json.dumps({
        "calibration_id": "test",
        "video_id": "test",
        "fps": 25.0,
        "fps_source": "container",
        "control_points": [
            {"id": f"p{i}", "pixel": [float(i * 50), float(i * 50)],
             "world_m": [float(i), float(i)], "source": "operator", "held_out": False}
            for i in range(4)
        ],
        "homography": np.eye(3).tolist(),
        "metrics": {"reprojection_rms_m": 0.05, "holdout_validation": [],
                    "planarity_warning": False},
        "confidence_layer": "operator",
    }))

    class _FakeTracker:
        def __init__(self, **kw): pass
        def process_video(self, vp, frame_step=1, progress=False):
            return [], VideoMeta(fps=25.0, frame_count=5, width=320, height=240)

    monkeypatch.setattr(pipe_mod, "VehicleTracker", _FakeTracker)

    from src.output.pipeline import run_pipeline
    result = run_pipeline(video_path, cal_path, progress=False)

    assert result is not None
    assert result.video_meta.fps == pytest.approx(25.0)
    assert isinstance(result.speed_estimates, list)
