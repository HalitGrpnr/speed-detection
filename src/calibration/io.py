from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from .models import CalibrationResult, ControlPoint


def _result_to_dict(
    result: CalibrationResult,
    points: list[ControlPoint],
    calibration_id: str | None = None,
    video_id: str | None = None,
    fps: float | None = None,
    fps_source: str = "container",
    holdout_rows: list[dict] | None = None,
) -> dict[str, Any]:
    """Serialize CalibrationResult to the §8 schema dict."""
    return {
        "calibration_id": calibration_id or str(uuid.uuid4()),
        "video_id": video_id or str(uuid.uuid4()),
        "fps": fps,
        "fps_source": fps_source,
        "control_points": [
            {
                "id": p.id,
                "pixel": list(p.pixel),
                "world_m": list(p.world_m),
                "source": p.source,
                "held_out": p.held_out,
            }
            for p in points
        ],
        "homography": result.homography.tolist(),
        "metrics": {
            "reprojection_rms_m": result.reprojection_rms_m,
            "holdout_validation": holdout_rows or [],
            "planarity_warning": result.planarity_warning,
        },
        "confidence_layer": result.confidence_layer,
    }


def save_calibration(
    path: str | Path,
    result: CalibrationResult,
    points: list[ControlPoint],
    **kwargs: Any,
) -> None:
    """Write calibration to JSON file."""
    data = _result_to_dict(result, points, **kwargs)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_calibration(
    path: str | Path,
) -> tuple[CalibrationResult, list[ControlPoint], tuple[float | None, str]]:
    """Load CalibrationResult, ControlPoints, and fps info from JSON file.

    Returns (result, points, (fps, fps_source)).
    fps is None when the JSON was written without an fps override.
    """
    data = json.loads(Path(path).read_text())

    points = [
        ControlPoint(
            id=cp["id"],
            pixel=tuple(cp["pixel"]),
            world_m=tuple(cp["world_m"]),
            source=cp["source"],
            held_out=cp.get("held_out", False),
        )
        for cp in data["control_points"]
    ]

    result = CalibrationResult(
        homography=np.array(data["homography"], dtype=np.float64),
        used_point_ids=[
            cp["id"] for cp in data["control_points"] if not cp.get("held_out", False)
        ],
        excluded_point_ids=[],
        reprojection_rms_m=data["metrics"]["reprojection_rms_m"],
        confidence_layer=data["confidence_layer"],
        planarity_warning=data["metrics"].get("planarity_warning", False),
    )

    fps_in_json: float | None = data.get("fps")
    fps_source_in_json: str = data.get("fps_source", "container")

    return result, points, (fps_in_json, fps_source_in_json)
