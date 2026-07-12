from __future__ import annotations

import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from src.calibration.io import load_calibration
from src.calibration.planview import compute_plan_view
from src.detection.tracker import VehicleTracker
from src.detection.video import iter_video_frames, read_video_meta
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
    on_progress: Callable[[float], None] | None = None,
    fps: float | None = None,
    fps_source: str | None = None,
    video_sha256: str = "",
) -> PipelineResult:
    """M1→M5 uçtan uca pipeline.

    Kalibrasyon yükle → araç takibi → hız hesabı → overlay video + PDF rapor.

    fps/fps_source: operator override değerleri. Verilmezse kalibrasyon JSON'u,
    sonra konteyner FPS'i denenir. Hız hesabı fps_used'u kullanır — Δt doğruluğu için kritik.
    """
    video_path = Path(video_path)
    calibration_path = Path(calibration_path)
    t_start = time.monotonic()

    # 1. Kalibrasyon
    if progress:
        print("Kalibrasyon yükleniyor...", flush=True)
    cal_result, control_points, (cal_fps, cal_fps_source) = load_calibration(calibration_path)
    H = cal_result.homography
    if progress:
        rms_cm = cal_result.reprojection_rms_m * 100
        print(f"  RMS: {rms_cm:.1f} cm  [{cal_result.confidence_layer}]", flush=True)

    # Kuş bakışı projeksiyon (DTP karşılaştırması §5) — ikincil bir sunum görseli;
    # üretilemezse pipeline asla çökmez, rapor o bölümü atlar (bkz. DECISIONS.md).
    plan_view_png: bytes | None = None
    try:
        _, frame0 = next(iter_video_frames(video_path, frame_step=1))
        plan_img = compute_plan_view(frame0, H, control_points)
        ok, buf = cv2.imencode(".png", plan_img)
        if ok:
            plan_view_png = buf.tobytes()
    except Exception as exc:  # noqa: BLE001 — ikincil görsel, ana pipeline'ı bozmamalı
        if progress:
            print(f"  Uyarı: kuş bakışı görsel üretilemedi ({exc})", flush=True)

    # 2. Takip
    if progress:
        print("Model yükleniyor...", flush=True)
    tracker = VehicleTracker(model_name=model_name)
    meta = read_video_meta(video_path)

    # FPS öncelik sırası: explicit param → kalibrasyon JSON → konteyner
    if fps is not None:
        fps_used = fps
        fps_source_used = fps_source or "operator_override"
    elif cal_fps is not None:
        fps_used = cal_fps
        fps_source_used = cal_fps_source
    else:
        fps_used = meta.fps
        fps_source_used = "container"
    meta.fps = fps_used
    meta.fps_source = fps_source_used  # type: ignore[assignment]

    dur_s = meta.frame_count / fps_used if fps_used > 0 else 0.0
    if progress:
        print(
            f"Video: {meta.width}×{meta.height} @ {fps_used:.1f} fps [{fps_source_used}]  "
            f"{meta.frame_count} kare ({dur_s:.1f} sn)",
            flush=True,
        )
        print("İşleniyor...", flush=True)
    def _track_cb(done: int, total: int) -> None:
        if on_progress is not None:
            on_progress(15.0 + done / total * 70.0)

    tracks, _ = tracker.process_video(
        video_path, frame_step=frame_step, progress=progress, on_progress=_track_cb
    )
    if progress:
        print(f"Takip: {len(tracks)} track", flush=True)
    if on_progress:
        on_progress(87.0)

    # 3. Hız hesabı
    speed_estimates = []
    for track in tracks:
        if len(track.points) < min_track_points:
            continue
        est = estimate_speed(track, H, fps_used, calibration_result=cal_result)
        speed_estimates.append(est)

    if progress:
        print(f"Hız hesabı: {len(speed_estimates)} aktif track", flush=True)
    if on_progress:
        on_progress(90.0)

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
        video_sha256=video_sha256,
        plan_view_png=plan_view_png,
    )

    # 4. Çıktılar
    if out_video is not None:
        if progress:
            print(f"Overlay video yazılıyor → {out_video}", flush=True)
        write_overlay_video(result, out_video)
        if on_progress:
            on_progress(97.0)

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
