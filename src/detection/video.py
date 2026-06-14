from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

import cv2
import numpy as np


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    width: int
    height: int
    fps_source: Literal["container", "operator_override"] = "container"


def read_video_meta(video_path: str | Path) -> VideoMeta:
    """Read FPS, resolution and frame count from video container."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()

    if fps <= 0:
        raise IOError(f"Could not read valid FPS from video: {video_path}")

    return VideoMeta(fps=fps, frame_count=frame_count, width=width, height=height)


def iter_video_frames(
    video_path: str | Path,
    frame_step: int = 1,
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_idx, bgr_frame) for each sampled frame."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_step == 0:
                yield frame_idx, frame
            frame_idx += 1
    finally:
        cap.release()
