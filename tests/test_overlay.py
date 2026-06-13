"""Acceptance tests for M5 — overlay video."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.detection.models import Track, TrackPoint
from src.speed.models import SpeedEstimate, SpeedSample, TrackQuality
from src.output.overlay import CONFIDENCE_COLORS, draw_frame, _instant_speed


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_track(track_id: int, frame: int = 10,
                bbox=(100, 100, 200, 200)) -> Track:
    tp = TrackPoint(
        frame=frame,
        t_s=frame / 25.0,
        contact_pixel=((bbox[0] + bbox[2]) / 2, bbox[3]),
        bbox=bbox,
    )
    return Track(track_id=track_id, vehicle_class="car", points=[tp])


def _make_estimate(
    track_id: int,
    confidence: str,
    speed_kmh: float = 60.0,
    frame: int = 10,
) -> SpeedEstimate:
    sample = SpeedSample(frame=frame, t_s=frame / 25.0,
                         world_m=(0.0, 0.0), speed_kmh=speed_kmh)
    return SpeedEstimate(
        track_id=track_id,
        value_kmh=speed_kmh,
        ci_kmh=2.0,
        confidence_level=confidence,
        speed_series=[sample],
        smoothed_series=[(frame / 25.0, speed_kmh)],
        track_quality=TrackQuality(
            frame_count=1, has_occlusion=False, smoothness_residual=1.0),
    )


def _black_frame(w=640, h=480) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


# ── Test 1: Renk doğruluğu ───────────────────────────────────────────────────

def test_draw_frame_high_confidence_uses_green():
    frame = _black_frame()
    track = _make_track(1, frame=10, bbox=(50, 50, 150, 150))
    est = _make_estimate(1, "high", frame=10)

    out = draw_frame(frame, 10, [est], [track], frame_step=1)

    # Bbox etrafında yeşil piksel olmalı (renk: 0,200,0 BGR)
    expected_bgr = CONFIDENCE_COLORS["high"]
    # Üst kenar boyunca piksel kontrol et
    row = out[50, 50:150]
    green_pixels = np.sum(np.all(row == expected_bgr, axis=1))
    assert green_pixels > 0, "Yüksek güven için yeşil bbox bekleniyor"


def test_draw_frame_low_confidence_uses_red():
    frame = _black_frame()
    track = _make_track(2, frame=5, bbox=(200, 200, 350, 300))
    est = _make_estimate(2, "low", frame=5)

    out = draw_frame(frame, 5, [est], [track], frame_step=1)

    expected_bgr = CONFIDENCE_COLORS["low"]
    row = out[200, 200:350]
    red_pixels = np.sum(np.all(row == expected_bgr, axis=1))
    assert red_pixels > 0, "Düşük güven için kırmızı bbox bekleniyor"


def test_draw_frame_medium_confidence_uses_orange():
    frame = _black_frame()
    track = _make_track(3, frame=7, bbox=(10, 10, 80, 80))
    est = _make_estimate(3, "medium", frame=7)

    out = draw_frame(frame, 7, [est], [track], frame_step=1)

    expected_bgr = CONFIDENCE_COLORS["medium"]
    row = out[10, 10:80]
    orange_pixels = np.sum(np.all(row == expected_bgr, axis=1))
    assert orange_pixels > 0, "Orta güven için turuncu bbox bekleniyor"


# ── Test 2: Hız metni çiziliyor ──────────────────────────────────────────────

def test_draw_frame_modifies_blank_frame():
    frame = _black_frame()
    track = _make_track(1, frame=0, bbox=(100, 100, 300, 250))
    est = _make_estimate(1, "high", frame=0)

    out = draw_frame(frame, 0, [est], [track], frame_step=1)

    assert not np.array_equal(frame, out), "Overlay frame orijinalle aynı olmamalı"


# ── Test 3: Aktif track tespiti ───────────────────────────────────────────────

def test_active_track_within_frame_step_is_drawn():
    """Son noktası tam frame_step öncesindeyse track aktif sayılır."""
    frame = _black_frame()
    track = _make_track(1, frame=9, bbox=(50, 50, 150, 150))   # son nokta: 9
    est = _make_estimate(1, "high", frame=9)

    out = draw_frame(frame, 10, [est], [track], frame_step=1)  # frame_idx=10, step=1

    # frame_idx(10) - last_frame(9) = 1 == frame_step(1) → aktif → çizilmeli
    expected_bgr = CONFIDENCE_COLORS["high"]
    row = out[50, 50:150]
    green_pixels = np.sum(np.all(row == expected_bgr, axis=1))
    assert green_pixels > 0, "frame_step sınırındaki track çizilmeli"


def test_stale_track_beyond_frame_step_not_drawn():
    """Son noktası frame_step'ten önce olan track çizilmez."""
    frame = _black_frame()
    track = _make_track(1, frame=5, bbox=(50, 50, 150, 150))   # son nokta: 5
    est = _make_estimate(1, "high", frame=5)

    out = draw_frame(frame, 10, [est], [track], frame_step=1)  # fark=5 > step=1

    # Çizim olmamalı → orijinal siyah frame ile aynı
    assert np.array_equal(frame, out), "Eski track çizilmemeli"


def test_large_frame_step_keeps_track_active():
    """frame_step=3'te son nokta 2 kare öncesindeyse track hâlâ aktif."""
    frame = _black_frame()
    track = _make_track(1, frame=8, bbox=(50, 50, 150, 150))
    est = _make_estimate(1, "high", frame=8)

    out = draw_frame(frame, 10, [est], [track], frame_step=3)  # fark=2 ≤ 3

    expected_bgr = CONFIDENCE_COLORS["high"]
    row = out[50, 50:150]
    green_pixels = np.sum(np.all(row == expected_bgr, axis=1))
    assert green_pixels > 0


def test_no_estimates_leaves_frame_unchanged():
    frame = _black_frame()
    out = draw_frame(frame, 10, [], [], frame_step=1)
    assert np.array_equal(frame, out)


# ── Test 4: write_overlay_video dosya oluşturur ───────────────────────────────

def test_write_overlay_video_creates_file(tmp_path):
    """Sentetik tek-kare video ile write_overlay_video çalışır."""
    import cv2
    from src.output.models import PipelineResult
    from src.output.overlay import write_overlay_video
    from src.detection.video import VideoMeta

    # Tek karede video yaz
    video_path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w = cv2.VideoWriter(str(video_path), fourcc, 25.0, (320, 240))
    w.write(np.zeros((240, 320, 3), dtype=np.uint8))
    w.release()

    from src.calibration.models import CalibrationResult
    cal = CalibrationResult(
        homography=np.eye(3),
        used_point_ids=[],
        excluded_point_ids=[],
        reprojection_rms_m=0.05,
        confidence_layer="operator",
        planarity_warning=False,
    )

    result = PipelineResult(
        video_path=str(video_path),
        video_meta=VideoMeta(fps=25.0, frame_count=1, width=320, height=240),
        calibration_result=cal,
        control_points=[],
        speed_estimates=[],
        tracks=[],
        processed_at="2026-01-01T00:00:00+00:00",
    )

    out_video = tmp_path / "overlay.mp4"
    write_overlay_video(result, out_video)

    assert out_video.exists()
    assert out_video.stat().st_size > 0


# ── Test 5: _instant_speed anlık hız seçimi ──────────────────────────────────

def _make_multi_sample_estimate(track_id: int) -> SpeedEstimate:
    """Farklı fremlerde farklı hızlar — value_kmh != anlık hız."""
    frames = [0, 5, 10, 15, 20]
    speeds = [0.0, 20.0, 50.0, 70.0, 30.0]  # value_kmh (median) = 30
    samples = [
        SpeedSample(frame=f, t_s=f / 25.0, world_m=(0.0, 0.0), speed_kmh=s)
        for f, s in zip(frames, speeds)
    ]
    smoothed = [(f / 25.0, s) for f, s in zip(frames, speeds)]
    return SpeedEstimate(
        track_id=track_id,
        value_kmh=30.0,   # Tüm track medyanı — anlık hızdan farklı
        ci_kmh=5.0,
        confidence_level="high",
        speed_series=samples,
        smoothed_series=smoothed,
        track_quality=TrackQuality(frame_count=5, has_occlusion=False,
                                   smoothness_residual=1.0),
    )


def test_instant_speed_returns_per_frame_value_not_track_median():
    """_instant_speed, value_kmh (sabit medyan) DEĞİL anlık hızı döndürmeli."""
    est = _make_multi_sample_estimate(1)
    # value_kmh = 30 — eğer hatalı kod varsa tüm frameler 30 döndürür

    assert _instant_speed(est, 0)  == 0.0   # frame 0: hız=0
    assert _instant_speed(est, 3)  == 0.0   # frame 3 < 5: frame 0'ın hızı
    assert _instant_speed(est, 5)  == 20.0  # frame 5: hız=20
    assert _instant_speed(est, 10) == 50.0  # frame 10: hız=50
    assert _instant_speed(est, 12) == 50.0  # frame 12 < 15: frame 10'un hızı
    assert _instant_speed(est, 20) == 30.0  # frame 20 (son): hız=30
    assert _instant_speed(est, 99) == 30.0  # frame 99 > son: son hız tutulur


def test_instant_speed_fallback_when_no_sample_yet():
    """Henüz hiç örnek gelmemişse (ilk kare öncesi) value_kmh döner."""
    est = _make_multi_sample_estimate(1)
    # Tüm samples frame >= 0 olduğundan frame -1 gibi bir durum olamaz,
    # ama speed_series boş ise value_kmh dönmeli.
    est_empty = SpeedEstimate(
        track_id=99,
        value_kmh=55.0,
        ci_kmh=2.0,
        confidence_level="medium",
        speed_series=[],
        smoothed_series=[],
        track_quality=TrackQuality(frame_count=0, has_occlusion=False,
                                   smoothness_residual=0.0),
    )
    assert _instant_speed(est_empty, 10) == 55.0


def test_draw_frame_label_shows_instant_not_median():
    """draw_frame etiketinde value_kmh=30 değil anlık hız görünmeli."""
    est = _make_multi_sample_estimate(1)
    # Frame 10'da hız=50, value_kmh=30
    tp = TrackPoint(frame=10, t_s=0.4,
                    contact_pixel=(100.0, 200.0), bbox=(50, 100, 150, 200))
    track = Track(track_id=1, vehicle_class="car", points=[tp])

    frame = _black_frame()
    out = draw_frame(frame, 10, [est], [track], frame_step=1)

    # Overlay değişmiş olmalı
    assert not np.array_equal(frame, out)
    # ve value_kmh=30 yerine 50 göstermeli — piksel düzeyinde kontrol zor,
    # _instant_speed dönüşü ile doğrudan test edelim
    assert _instant_speed(est, 10) == 50.0, "Frame 10'da 50 km/h bekleniyor, 30 (median) değil"
