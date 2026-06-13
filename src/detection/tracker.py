from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from .models import (
    Track, TrackPoint, VEHICLE_CLASSES, VEHICLE_CLASS_IDS,
    contact_point, compute_occlusion_gaps,
)
from .video import VideoMeta, read_video_meta, iter_video_frames


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


class VehicleTracker:
    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        device: str = "auto",
        conf_threshold: float = 0.25,
        tracker_config: str = "bytetrack.yaml",
    ) -> None:
        from ultralytics import YOLO
        self._device = _resolve_device(device)
        self._conf = conf_threshold
        self._tracker_config = tracker_config
        self._model = YOLO(model_name)

    def process_video(
        self,
        video_path: str | Path,
        frame_step: int = 1,
    ) -> tuple[list[Track], VideoMeta]:
        """Process video and return (tracks, video_meta)."""
        meta = read_video_meta(video_path)

        # track_id → {"cls": str, "points": list of raw tuples}
        raw: dict[int, dict] = defaultdict(lambda: {"cls": "", "raw_points": []})

        for frame_idx, frame in iter_video_frames(video_path, frame_step):
            results = self._model.track(
                frame,
                persist=True,
                tracker=self._tracker_config,
                device=self._device,
                conf=self._conf,
                classes=list(VEHICLE_CLASS_IDS),
                verbose=False,
            )
            for r in results:
                boxes = r.boxes
                if boxes is None or boxes.id is None:
                    continue
                ids = boxes.id.int().tolist()
                xyxys = boxes.xyxy.tolist()
                clss = boxes.cls.int().tolist()
                confs = boxes.conf.tolist()

                for tid, xyxy, cls_id, conf in zip(ids, xyxys, clss, confs):
                    cls_name = r.names.get(cls_id, "")
                    if cls_name not in VEHICLE_CLASSES:
                        continue
                    x1, y1, x2, y2 = xyxy
                    bbox = (x1, y1, x2, y2)
                    t_s = frame_idx / meta.fps
                    raw[tid]["cls"] = cls_name
                    raw[tid]["raw_points"].append((frame_idx, t_s, bbox))

        tracks: list[Track] = []
        for tid, data in raw.items():
            points = [
                TrackPoint(
                    frame=f,
                    t_s=t,
                    contact_pixel=contact_point(bbox),
                    bbox=bbox,
                )
                for f, t, bbox in data["raw_points"]
            ]
            frames = [p.frame for p in points]
            gaps = compute_occlusion_gaps(frames)
            tracks.append(Track(
                track_id=tid,
                vehicle_class=data["cls"],
                points=points,
                occlusion_gaps=gaps,
            ))

        return tracks, meta


def _main(video_path: str) -> None:
    tracker = VehicleTracker()
    tracks, meta = tracker.process_video(video_path)
    print(f"Video: {meta.width}x{meta.height} @ {meta.fps:.1f} fps, {meta.frame_count} kare")
    print(f"Bulunan track sayısı: {len(tracks)}")
    for t in sorted(tracks, key=lambda x: x.track_id):
        gap_str = f"{len(t.occlusion_gaps)} boşluk"
        if t.occlusion_gaps:
            gaps_fmt = ", ".join(f"kare {a}-{b}" for a, b in t.occlusion_gaps)
            gap_str += f" [{gaps_fmt}]"
        print(f"  Track #{t.track_id} — {t.vehicle_class} — {len(t.points)} nokta, {gap_str}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python -m src.detection.tracker <video.mp4>")
        sys.exit(1)
    _main(sys.argv[1])
