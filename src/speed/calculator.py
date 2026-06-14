from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import numpy as np

from src.calibration.homography import pixel_to_world
from src.calibration.models import CalibrationResult
from src.detection.models import Track
from src.reliability.confidence import ConfidenceSignals, compute_confidence_level
from .models import SpeedSample, SpeedEstimate, TrackQuality
from .smoother import sliding_window_smooth


def track_to_world(
    track: Track,
    H: np.ndarray,
    fps: float,
) -> list[SpeedSample]:
    """Her temas noktasını H ile metrik konuma çevir; ardışık çiftler arası anlık hız hesapla.

    Δt = Δframe / fps  (1/fps DEĞİL — frame_step ve oklüzyon boşluğu için kritik).
    İlk nokta için speed_kmh = 0.0.
    """
    samples: list[SpeedSample] = []
    prev_world: tuple[float, float] | None = None
    prev_frame: int | None = None

    for tp in track.points:
        world = pixel_to_world(H, tp.contact_pixel)

        if prev_world is None:
            speed_kmh = 0.0
        else:
            delta_d = float(np.hypot(world[0] - prev_world[0], world[1] - prev_world[1]))
            delta_t = (tp.frame - prev_frame) / fps
            speed_kmh = (delta_d / delta_t * 3.6) if delta_t > 0 else 0.0

        samples.append(SpeedSample(
            frame=tp.frame,
            t_s=tp.t_s,
            world_m=world,
            speed_kmh=speed_kmh,
        ))
        prev_world = world
        prev_frame = tp.frame

    return samples


def estimate_speed(
    track: Track,
    H: np.ndarray,
    fps: float,
    calibration_result: CalibrationResult,
    window_s: float = 0.4,
    method: Literal["median", "mean", "regression"] = "median",
) -> SpeedEstimate:
    """Tam pipeline: track → metrik → ham seri → yumuşatma → SpeedEstimate."""
    samples = track_to_world(track, H, fps)
    # 3 km/h altı tespit jitter'ı — durmuş araçta 0 göster
    smoothed = sliding_window_smooth(samples, window_s, method, min_detectable_kmh=3.0)

    smoothed_values = np.array([v for _, v in smoothed])

    # Nokta tahmini: ilk sample speed=0 olduğundan onu hariç tut
    est_values = smoothed_values[1:] if len(smoothed_values) > 1 else smoothed_values
    value_kmh = float(np.median(est_values)) if len(est_values) > 0 else 0.0

    # CI: IQR/2
    if len(est_values) >= 2:
        q75, q25 = np.percentile(est_values, [75, 25])
        ci_kmh = float((q75 - q25) / 2.0)
    else:
        ci_kmh = 0.0

    # Smoothness residual (ilk sample atlanır)
    if len(samples) > 1:
        raw = np.array([s.speed_kmh for s in samples[1:]])
        sm = smoothed_values[1:]
        residuals = raw - sm
        smoothness_residual = float(np.sqrt(np.mean(residuals ** 2)))
    else:
        smoothness_residual = 0.0

    quality = TrackQuality(
        frame_count=len(track.points),
        has_occlusion=len(track.occlusion_gaps) > 0,
        smoothness_residual=smoothness_residual,
    )

    signals = ConfidenceSignals(
        calibration_layer=calibration_result.confidence_layer,
        reprojection_rms_m=calibration_result.reprojection_rms_m,
        track_frame_count=quality.frame_count,
        has_occlusion=quality.has_occlusion,
        smoothness_residual_kmh=quality.smoothness_residual,
        planarity_warning=calibration_result.planarity_warning,
    )
    confidence_level = compute_confidence_level(signals)

    return SpeedEstimate(
        track_id=track.track_id,
        value_kmh=value_kmh,
        ci_kmh=ci_kmh,
        confidence_level=confidence_level,
        speed_series=samples,
        smoothed_series=smoothed,
        track_quality=quality,
    )


def _main(video_path: str, calibration_path: str, frame_step: int = 1) -> None:
    import time
    from src.calibration.io import load_calibration
    from src.detection.tracker import VehicleTracker
    from src.detection.video import read_video_meta

    print("Kalibrasyon yükleniyor...")
    cal_result, _, (cal_fps, _cal_fps_src) = load_calibration(calibration_path)
    H = cal_result.homography

    print("Model yükleniyor...")
    tracker = VehicleTracker()

    meta = read_video_meta(video_path)
    dur_s = meta.frame_count / meta.fps
    sampled = (meta.frame_count + frame_step - 1) // frame_step
    print(
        f"Video: {meta.width}x{meta.height} @ {meta.fps:.1f} fps  "
        f"{meta.frame_count} kare ({dur_s:.1f} sn)"
    )
    print(f"İşlenecek kare: {sampled} (adım={frame_step})  Cihaz: {tracker._device}")
    print("İşleniyor...")

    t0 = time.monotonic()
    tracks, _ = tracker.process_video(video_path, frame_step=frame_step, progress=True)
    elapsed = time.monotonic() - t0
    print(f"Takip tamamlandı: {elapsed:.1f} sn — {len(tracks)} track")
    print()

    for t in sorted(tracks, key=lambda x: x.track_id):
        if len(t.points) < 2:
            continue
        est = estimate_speed(t, H, meta.fps, calibration_result=cal_result)
        gap_str = f"oklüzyon {'var' if est.track_quality.has_occlusion else 'yok'}"
        print(
            f"Track #{t.track_id} — {t.vehicle_class}\n"
            f"  Ham seri: {len(est.speed_series)} örnek, "
            f"ort. {np.mean([s.speed_kmh for s in est.speed_series[1:]]):.1f} km/h\n"
            f"  Yumuşatılmış: {est.value_kmh:.1f} km/h  CI ±{est.ci_kmh:.1f} km/h\n"
            f"  Güven: {est.confidence_level} (M4 sonrası güncellenecek)\n"
            f"  Track kalitesi: {est.track_quality.frame_count} kare, "
            f"{gap_str}, residual {est.track_quality.smoothness_residual:.1f} km/h"
        )
        print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hız hesabı demo")
    parser.add_argument("video", help="Video dosyası")
    parser.add_argument("calibration", help="Kalibrasyon JSON dosyası")
    parser.add_argument("--step", type=int, default=1,
                        help="Kare örnekleme adımı (varsayılan: 1)")
    args = parser.parse_args()
    _main(args.video, args.calibration, frame_step=args.step)
