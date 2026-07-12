from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}

# COCO class indices for vehicle classes
VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # car=2, motorcycle=3, bus=5, truck=7


@dataclass
class Detection:
    frame: int
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    cls: str                                  # "car" | "truck" | "bus" | "motorcycle"
    confidence: float


@dataclass
class TrackPoint:
    frame: int
    t_s: float                               # frame / fps
    contact_pixel: tuple[float, float]       # ((x1+x2)/2, y2)
    bbox: tuple[float, float, float, float]


@dataclass
class Track:
    track_id: int
    vehicle_class: str
    points: list[TrackPoint] = field(default_factory=list)
    occlusion_gaps: list[tuple[int, int]] = field(default_factory=list)


def contact_point(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    """Return wheel-ground contact point: bottom-center of bbox."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, y2)


def save_tracks(path: str | Path, tracks: list[Track]) -> None:
    """Track listesini JSON dosyasına yaz (aks doğrulaması gibi rapor-sonrası
    işlemlerin, pipeline'ı yeniden çalıştırmadan bbox verisine erişmesi için)."""
    data = [
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
        for t in tracks
    ]
    Path(path).write_text(json.dumps(data, ensure_ascii=False))


def load_tracks(path: str | Path) -> list[Track]:
    """save_tracks ile yazılmış bir JSON dosyasından Track listesini oku."""
    data = json.loads(Path(path).read_text())
    return [
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
        for t in data
    ]


def compute_occlusion_gaps(
    frames: list[int],
    expected_step: int = 1,
) -> list[tuple[int, int]]:
    """Find gaps larger than expected_step in a sorted frame list.

    expected_step should match the frame_step used during video processing
    so that normal sampling gaps are not mistaken for occlusions.
    """
    gaps = []
    for i in range(len(frames) - 1):
        if frames[i + 1] - frames[i] > expected_step:
            gaps.append((frames[i] + 1, frames[i + 1] - 1))
    return gaps
