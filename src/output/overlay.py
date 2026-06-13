from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.detection.models import Track
from src.detection.video import iter_video_frames
from src.speed.models import SpeedEstimate
from .models import PipelineResult

CONFIDENCE_COLORS: dict[str, tuple[int, int, int]] = {
    "high":   (0, 200, 0),
    "medium": (0, 165, 255),
    "low":    (0, 0, 220),
}

_CONFIDENCE_TAG = {"high": "H", "medium": "M", "low": "L"}
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.55
_THICK = 2
_THIN = 1


def _instant_speed(est: SpeedEstimate, frame_idx: int) -> float:
    """O karedeki anlık yumuşatılmış hız.

    speed_series ve smoothed_series bire-bir eşleşir (aynı uzunluk, aynı sıra).
    frame_idx'e eşit veya daha önce olan en son örneğin değerini döndürür.
    Hiç örnek yoksa track özet değerine düşer.
    """
    best = est.value_kmh
    for i, sample in enumerate(est.speed_series):
        if sample.frame > frame_idx:
            break
        if i < len(est.smoothed_series):
            best = est.smoothed_series[i][1]
    return best


def draw_frame(
    frame: np.ndarray,
    frame_idx: int,
    speed_estimates: list[SpeedEstimate],
    tracks: list[Track],
    frame_step: int = 1,
) -> np.ndarray:
    """Tek kareye overlay çiz — bbox, track ID, anlık hız, güven rengi.

    Her SpeedEstimate için eşleşen Track bulunur; son noktası frame_step
    içindeyse aktif kabul edilir ve bbox çizilir.
    """
    out = frame.copy()
    track_map = {t.track_id: t for t in tracks}

    for est in speed_estimates:
        track = track_map.get(est.track_id)
        if track is None or not track.points:
            continue

        best = None
        for tp in reversed(track.points):
            if tp.frame <= frame_idx:
                best = tp
                break

        if best is None or (frame_idx - best.frame) > frame_step:
            continue

        color = CONFIDENCE_COLORS[est.confidence_level]
        x1, y1, x2, y2 = (int(v) for v in best.bbox)

        cv2.rectangle(out, (x1, y1), (x2, y2), color, _THICK)

        speed_now = _instant_speed(est, frame_idx)
        label = f"#{est.track_id} {speed_now:.0f} km/h"
        (tw, th), bl = cv2.getTextSize(label, _FONT, _FONT_SCALE, _THIN)
        bg_y1 = max(0, y1 - th - bl - 4)
        cv2.rectangle(out, (x1, bg_y1), (x1 + tw + 4, y1), color, -1)
        cv2.putText(out, label, (x1 + 2, y1 - bl - 2),
                    _FONT, _FONT_SCALE, (0, 0, 0), _THIN, cv2.LINE_AA)

        tag = _CONFIDENCE_TAG[est.confidence_level]
        (cw, ch), _ = cv2.getTextSize(tag, _FONT, 0.45, _THIN)
        cv2.rectangle(out, (x2 - cw - 4, y1), (x2, y1 + ch + 4), color, -1)
        cv2.putText(out, tag, (x2 - cw - 2, y1 + ch + 1),
                    _FONT, 0.45, (0, 0, 0), _THIN, cv2.LINE_AA)

    return out


def write_overlay_video(
    result: PipelineResult,
    out_path: str | Path,
) -> None:
    """Giriş videosunun her karesine overlay çizerek yeni video yaz."""
    out_path = Path(out_path)
    meta = result.video_meta

    # avc1 (H.264) tarayıcı uyumlu; açılamazsa mp4v'ye düş
    writer: cv2.VideoWriter | None = None
    for fourcc_str in ("avc1", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        w = cv2.VideoWriter(str(out_path), fourcc, meta.fps,
                            (meta.width, meta.height))
        if w.isOpened():
            writer = w
            break
        w.release()
    if writer is None:
        raise IOError(f"VideoWriter açılamadı: {out_path}")

    try:
        for frame_idx, frame in iter_video_frames(result.video_path):
            out_frame = draw_frame(
                frame, frame_idx,
                result.speed_estimates, result.tracks,
                result.frame_step,
            )
            writer.write(out_frame)
    finally:
        writer.release()  # type: ignore[union-attr]
