from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.calibration.io import load_calibration
from src.detection.tracker import VehicleTracker
from src.detection.video import read_video_meta
from src.speed.calculator import estimate_speed
from .models import PipelineResult
from .overlay import write_overlay_video
from .report import generate_report


def run_pipeline(
    video_path: str | Path,
    calibration_path: str | Path,
    out_video: str | Path | None = None,
    out_report: str | Path | None = None,
    frame_step: int = 1,
    model_name: str = "yolo11n.pt",
    min_track_points: int = 2,
    progress: bool = True,
) -> PipelineResult:
    """M1→M5 uçtan uca pipeline.

    Kalibrasyon yükle → araç takibi → hız hesabı → overlay video + PDF rapor.
    """
    video_path = Path(video_path)
    calibration_path = Path(calibration_path)
    t_start = time.monotonic()

    # 1. Kalibrasyon
    if progress:
        print("Kalibrasyon yükleniyor...", flush=True)
    cal_result, control_points = load_calibration(calibration_path)
    H = cal_result.homography
    if progress:
        rms_cm = cal_result.reprojection_rms_m * 100
        print(f"  RMS: {rms_cm:.1f} cm  [{cal_result.confidence_layer}]", flush=True)

    # 2. Takip
    if progress:
        print("Model yükleniyor...", flush=True)
    tracker = VehicleTracker(model_name=model_name)
    meta = read_video_meta(video_path)
    dur_s = meta.frame_count / meta.fps if meta.fps > 0 else 0.0
    if progress:
        print(
            f"Video: {meta.width}×{meta.height} @ {meta.fps:.1f} fps  "
            f"{meta.frame_count} kare ({dur_s:.1f} sn)",
            flush=True,
        )
        print("İşleniyor...", flush=True)
    tracks, _ = tracker.process_video(video_path, frame_step=frame_step, progress=progress)
    if progress:
        print(f"Takip: {len(tracks)} track", flush=True)

    # 3. Hız hesabı
    speed_estimates = []
    for track in tracks:
        if len(track.points) < min_track_points:
            continue
        est = estimate_speed(track, H, meta.fps, calibration_result=cal_result)
        speed_estimates.append(est)

    if progress:
        print(f"Hız hesabı: {len(speed_estimates)} aktif track", flush=True)

    result = PipelineResult(
        video_path=str(video_path),
        video_meta=meta,
        calibration_result=cal_result,
        control_points=control_points,
        speed_estimates=speed_estimates,
        tracks=tracks,
        processed_at=datetime.now(timezone.utc).isoformat(),
        frame_step=frame_step,
        model_name=model_name,
    )

    # 4. Çıktılar
    if out_video is not None:
        if progress:
            print(f"Overlay video yazılıyor → {out_video}", flush=True)
        write_overlay_video(result, out_video)

    if out_report is not None:
        if progress:
            print(f"Rapor yazılıyor → {out_report}", flush=True)
        generate_report(result, out_report)

    elapsed = time.monotonic() - t_start
    if progress:
        print(f"Tamamlandı: {elapsed:.1f} sn", flush=True)

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Araç hız tespit pipeline'ı (M1→M5)")
    parser.add_argument("video", help="Giriş video dosyası")
    parser.add_argument("calibration", help="Kalibrasyon JSON dosyası")
    parser.add_argument("--out-video", default=None, help="Overlay video çıktı yolu (.mp4)")
    parser.add_argument("--out-report", default=None, help="Rapor çıktı yolu (.pdf)")
    parser.add_argument("--step", type=int, default=1, help="Kare örnekleme adımı")
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO model ağırlığı")
    args = parser.parse_args()

    out_video = args.out_video
    out_report = args.out_report
    if out_video is None and out_report is None:
        # Varsayılan çıktı adları
        stem = Path(args.video).stem
        out_video = f"{stem}_overlay.mp4"
        out_report = f"{stem}_report.pdf"
        print(f"Çıktılar: {out_video}, {out_report}")

    run_pipeline(
        video_path=args.video,
        calibration_path=args.calibration,
        out_video=out_video,
        out_report=out_report,
        frame_step=args.step,
        model_name=args.model,
    )
