"""PipelineResult ↔ JSON serileştirme.

Amacı: pipeline thread bitince result_data.json olarak diske yazmak ve
gerektiğinde (ör. rapor yeniden üretme) geri okumak.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import numpy as np

from .models import PipelineResult


def result_to_dict(result: PipelineResult) -> dict:
    """PipelineResult → JSON-serileştirilebilir dict."""
    cal = result.calibration_result
    return {
        "video_path": result.video_path,
        "video_meta": {
            "fps": result.video_meta.fps,
            "frame_count": result.video_meta.frame_count,
            "width": result.video_meta.width,
            "height": result.video_meta.height,
            "fps_source": result.video_meta.fps_source,
        },
        "calibration_result": {
            "homography": cal.homography.tolist(),
            "used_point_ids": cal.used_point_ids,
            "excluded_point_ids": cal.excluded_point_ids,
            "reprojection_rms_m": cal.reprojection_rms_m,
            "confidence_layer": cal.confidence_layer,
            "planarity_warning": cal.planarity_warning,
            "planarity_evaluated": cal.planarity_evaluated,
            "holdout_rows": cal.holdout_rows,
            "loo_rms_m": cal.loo_rms_m,
        },
        "control_points": [
            {
                "id": cp.id,
                "pixel": list(cp.pixel),
                "world_m": list(cp.world_m),
                "source": cp.source,
                "held_out": cp.held_out,
            }
            for cp in result.control_points
        ],
        "speed_estimates": [
            {
                "track_id": est.track_id,
                "value_kmh": est.value_kmh,
                "ci_kmh": est.ci_kmh,
                "confidence_level": est.confidence_level,
                "speed_series": [
                    {
                        "frame": s.frame,
                        "t_s": s.t_s,
                        "world_m": list(s.world_m),
                        "speed_kmh": s.speed_kmh,
                    }
                    for s in est.speed_series
                ],
                "smoothed_series": [list(pair) for pair in est.smoothed_series],
                "track_quality": {
                    "frame_count": est.track_quality.frame_count,
                    "has_occlusion": est.track_quality.has_occlusion,
                    "smoothness_residual": est.track_quality.smoothness_residual,
                },
            }
            for est in result.speed_estimates
        ],
        "tracks": [
            {
                "track_id": t.track_id,
                "vehicle_class": t.vehicle_class,
                "points": [
                    {
                        "frame": p.frame,
                        "t_s": p.t_s,
                        "contact_pixel": list(p.contact_pixel),
                        "bbox": list(p.bbox),
                    }
                    for p in t.points
                ],
            }
            for t in result.tracks
        ],
        "processed_at": result.processed_at,
        "frame_step": result.frame_step,
        "model_name": result.model_name,
        "video_sha256": result.video_sha256,
        "plan_view_png": (
            base64.b64encode(result.plan_view_png).decode("ascii")
            if result.plan_view_png is not None
            else None
        ),
    }


def result_from_dict(d: dict) -> PipelineResult:
    """JSON dict → PipelineResult (result_to_dict tersine çevrim)."""
    from src.calibration.models import CalibrationResult, ControlPoint
    from src.detection.models import Track, TrackPoint
    from src.detection.video import VideoMeta
    from src.speed.models import SpeedEstimate, SpeedSample, TrackQuality

    meta_d = d["video_meta"]
    cal_d = d["calibration_result"]

    cal = CalibrationResult(
        homography=np.array(cal_d["homography"], dtype=np.float64),
        used_point_ids=cal_d["used_point_ids"],
        excluded_point_ids=cal_d["excluded_point_ids"],
        reprojection_rms_m=cal_d["reprojection_rms_m"],
        confidence_layer=cal_d["confidence_layer"],
        planarity_warning=cal_d["planarity_warning"],
        planarity_evaluated=cal_d.get("planarity_evaluated", True),
        holdout_rows=cal_d.get("holdout_rows", []),
        loo_rms_m=cal_d.get("loo_rms_m"),
    )

    control_points = [
        ControlPoint(
            id=cp["id"],
            pixel=tuple(cp["pixel"]),
            world_m=tuple(cp["world_m"]),
            source=cp["source"],
            held_out=cp.get("held_out", False),
        )
        for cp in d["control_points"]
    ]

    tracks = [
        Track(
            track_id=t["track_id"],
            vehicle_class=t["vehicle_class"],
            points=[
                TrackPoint(
                    frame=p["frame"],
                    t_s=p["t_s"],
                    contact_pixel=tuple(p["contact_pixel"]),
                    bbox=tuple(p["bbox"]),
                )
                for p in t["points"]
            ],
        )
        for t in d["tracks"]
    ]

    speed_estimates = [
        SpeedEstimate(
            track_id=est["track_id"],
            value_kmh=est["value_kmh"],
            ci_kmh=est["ci_kmh"],
            confidence_level=est["confidence_level"],
            speed_series=[
                SpeedSample(
                    frame=s["frame"],
                    t_s=s["t_s"],
                    world_m=tuple(s["world_m"]),
                    speed_kmh=s["speed_kmh"],
                )
                for s in est["speed_series"]
            ],
            smoothed_series=[tuple(pair) for pair in est["smoothed_series"]],
            track_quality=TrackQuality(
                frame_count=est["track_quality"]["frame_count"],
                has_occlusion=est["track_quality"]["has_occlusion"],
                smoothness_residual=est["track_quality"]["smoothness_residual"],
            ),
        )
        for est in d["speed_estimates"]
    ]

    png_b64 = d.get("plan_view_png")
    plan_view_png = base64.b64decode(png_b64) if png_b64 is not None else None

    return PipelineResult(
        video_path=d["video_path"],
        video_meta=VideoMeta(
            fps=meta_d["fps"],
            frame_count=meta_d["frame_count"],
            width=meta_d["width"],
            height=meta_d["height"],
            fps_source=meta_d.get("fps_source", "container"),
        ),
        calibration_result=cal,
        control_points=control_points,
        speed_estimates=speed_estimates,
        tracks=tracks,
        processed_at=d["processed_at"],
        frame_step=d.get("frame_step", 1),
        model_name=d.get("model_name", "yolo11n.pt"),
        video_sha256=d.get("video_sha256", ""),
        plan_view_png=plan_view_png,
    )


def write_result_data(result: PipelineResult, out_dir: Path) -> Path:
    """result_data.json'ı out_dir'e yazar, dosya yolunu döndürür."""
    path = out_dir / "result_data.json"
    path.write_text(json.dumps(result_to_dict(result), ensure_ascii=False))
    return path


def read_result_data(out_dir: Path) -> PipelineResult:
    """out_dir/result_data.json'dan PipelineResult yükler."""
    path = out_dir / "result_data.json"
    return result_from_dict(json.loads(path.read_text()))
