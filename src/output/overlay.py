from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np

from src.detection.models import Track
from src.detection.video import iter_video_frames
from src.speed.models import SpeedEstimate
from src.speed.wheel_contact import WheelSpeedProfile
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
    speed_overrides: dict[int, float] | None = None,
) -> np.ndarray:
    """Tek kareye overlay çiz — bbox, track ID, anlık hız, güven rengi.

    speed_overrides: {track_id: km/h} — belirtilen track'ler için anlık hız
    yerine sabit override değeri gösterilir (tekerlek hızı overlay'i için).
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

        if speed_overrides and est.track_id in speed_overrides:
            speed_now = speed_overrides[est.track_id]
            label = f"#{est.track_id} {speed_now:.0f} km/h*"   # * = tekerlek hızı
        else:
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


def _open_writer(
    out_path: Path,
    fps: float,
    width: int,
    height: int,
) -> cv2.VideoWriter:
    for fourcc_str in ("avc1", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        w = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
        if w.isOpened():
            return w
        w.release()
    raise IOError(f"VideoWriter açılamadı: {out_path}")


def write_overlay_video(
    result: PipelineResult,
    out_path: str | Path,
    speed_overrides: dict[int, float] | None = None,
) -> None:
    """Giriş videosunun her karesine overlay çizerek yeni video yaz.

    speed_overrides: {track_id: km/h} — T25 tekerlek hızı overlay'i için.
    """
    out_path = Path(out_path)
    meta = result.video_meta

    writer = _open_writer(out_path, meta.fps, meta.width, meta.height)

    try:
        for frame_idx, frame in iter_video_frames(result.video_path):
            out_frame = draw_frame(
                frame, frame_idx,
                result.speed_estimates, result.tracks,
                result.frame_step,
                speed_overrides=speed_overrides,
            )
            writer.write(out_frame)
    finally:
        writer.release()  # type: ignore[union-attr]


# ── T19 — Tekerlek profili overlay ────────────────────────────────────────────

_PROFILE_COLOR_MARK = (0, 200, 80)    # yeşil — doğrudan işaretli kare
_PROFILE_COLOR_INTERP = (200, 200, 0)  # sarı — interpolasyon karesi


def _interp_pixel(
    frame_f: float,
    marks: list[dict],
) -> tuple[int, int] | None:
    """İşaret listesinden verilen kare için piksel konumu interpolasyonu."""
    for i in range(len(marks) - 1):
        f0 = float(marks[i]["frame"])
        f1 = float(marks[i + 1]["frame"])
        if f0 <= frame_f <= f1:
            df = f1 - f0
            if df == 0:
                px, py = marks[i]["pixel"]
                return (int(px), int(py))
            t = (frame_f - f0) / df
            px0, py0 = marks[i]["pixel"]
            px1, py1 = marks[i + 1]["pixel"]
            return (int(px0 + t * (px1 - px0)), int(py0 + t * (py1 - py0)))
    return None


def _interp_profile_speed(
    frame_f: float,
    fps: float,
    profile: WheelSpeedProfile,
) -> float | None:
    """Profil noktalarından verilen kare için hız interpolasyonu."""
    pts = profile.points
    if not pts:
        return None
    profile_frames = [pt.t_s * fps for pt in pts]
    if frame_f <= profile_frames[0]:
        return pts[0].speed_kmh
    if frame_f >= profile_frames[-1]:
        return pts[-1].speed_kmh
    for i in range(len(profile_frames) - 1):
        f0, f1 = profile_frames[i], profile_frames[i + 1]
        if f0 <= frame_f <= f1:
            if f1 == f0:
                return pts[i].speed_kmh
            t = (frame_f - f0) / (f1 - f0)
            return pts[i].speed_kmh + t * (pts[i + 1].speed_kmh - pts[i].speed_kmh)
    return pts[-1].speed_kmh


def _draw_profile_label(
    img: np.ndarray,
    pixel: tuple[int, int],
    speed_kmh: float,
    is_mark: bool,
) -> None:
    """Frame üzerine profil hız etiketi çiz.

    İşaretli karelerde dolu kutucuk (yeşil), interpolasyon karelerinde
    yalnızca kenarlı kutucuk (sarı) — görsel ayrım.
    """
    x, y = pixel
    label = f"{speed_kmh:.0f} km/h"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    thick = 1
    color = _PROFILE_COLOR_MARK if is_mark else _PROFILE_COLOR_INTERP
    (tw, th), bl = cv2.getTextSize(label, font, scale, thick)
    pad = 3
    x1 = max(0, x - pad)
    y1 = max(0, y - th - bl - 2 * pad)
    x2 = x1 + tw + 2 * pad
    y2 = y
    if is_mark:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
        cv2.putText(img, label, (x1 + pad, y2 - bl - pad),
                    font, scale, (0, 0, 0), thick, cv2.LINE_AA)
        cv2.circle(img, (x, y), 5, color, -1)
    else:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)
        cv2.putText(img, label, (x1 + pad, y2 - bl - pad),
                    font, scale, color, thick, cv2.LINE_AA)
        cv2.circle(img, (x, y), 3, color, 1)


def write_wheel_profile_overlay(
    video_path: str | Path,
    out_path: str | Path,
    marks: list[dict],
    profile: WheelSpeedProfile,
    fps: float,
    width: int,
    height: int,
) -> None:
    """T19 — Tekerlek hız profili overlay videosu.

    marks: [{"frame": float, "pixel": [x, y]}] sıralı olmalı.
    Kare aralığı [first_mark, last_mark] içinde interpolasyon hız etiketi.
    İşaretli kareler yeşil dolu, ara kareler sarı kenarlı etiket.
    """
    out_path = Path(out_path)
    marks_sorted = sorted(marks, key=lambda m: float(m["frame"]))
    if len(marks_sorted) < 2:
        raise ValueError("Overlay için en az 2 işaret gereklidir.")

    first_frame = float(marks_sorted[0]["frame"])
    last_frame = float(marks_sorted[-1]["frame"])
    mark_frame_set = {float(m["frame"]) for m in marks_sorted}

    writer = _open_writer(out_path, fps, width, height)
    try:
        for frame_idx, frame in iter_video_frames(video_path):
            out_frame = frame.copy()
            f = float(frame_idx)
            if first_frame <= f <= last_frame:
                pixel = _interp_pixel(f, marks_sorted)
                speed = _interp_profile_speed(f, fps, profile)
                if pixel is not None and speed is not None:
                    is_mark = f in mark_frame_set
                    _draw_profile_label(out_frame, pixel, speed, is_mark)
            writer.write(out_frame)
    finally:
        writer.release()


def profile_chart_png(
    profile: WheelSpeedProfile,
    width: int = 520,
    height: int = 200,
) -> bytes:
    """T19 — Profil hız-zaman grafiğini PNG bayt olarak döndür (rapor + UI önizleme).

    Matplotlib gerektirmez; saf NumPy + OpenCV.
    """
    pts = profile.points
    if not pts:
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        _, buf = cv2.imencode(".png", img)
        return buf.tobytes()

    times = [pt.t_s for pt in pts]
    speeds = [pt.speed_kmh for pt in pts]
    cis = [pt.ci_kmh for pt in pts]

    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    ML, MR, MT, MB = 48, 20, 20, 36  # sol, sağ, üst, alt margin (piksel)
    cw = width - ML - MR
    ch = height - MT - MB

    t_min, t_max = min(times), max(times)
    v_lo = max(0.0, min(speeds) - max(10.0, max(cis) * 1.5))
    v_hi = max(speeds) + max(10.0, max(cis) * 1.5)

    def tx(t: float) -> int:
        return ML + int(cw * (t - t_min) / max(t_max - t_min, 1e-9))

    def ty(v: float) -> int:
        return MT + ch - int(ch * (v - v_lo) / max(v_hi - v_lo, 1e-9))

    # Arka plan ızgara (10 km/h aralıklı yatay çizgi)
    v_start = int(v_lo / 10) * 10
    for v in range(v_start, int(v_hi) + 10, 10):
        y = ty(float(v))
        if MT <= y <= MT + ch:
            cv2.line(img, (ML, y), (ML + cw, y), (210, 210, 210), 1)
            cv2.putText(img, str(v), (2, y + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (130, 130, 130), 1)

    # CI bant
    upper_pts = [(tx(times[i]), ty(speeds[i] + cis[i])) for i in range(len(pts))]
    lower_pts = [(tx(times[i]), ty(speeds[i] - cis[i])) for i in range(len(pts))]
    if len(upper_pts) > 1:
        band_color = (200, 210, 230)
        for i in range(len(upper_pts) - 1):
            poly = np.array([
                upper_pts[i], upper_pts[i + 1],
                lower_pts[i + 1], lower_pts[i],
            ], dtype=np.int32)
            cv2.fillPoly(img, [poly], band_color)

    # Hız çizgisi
    line_pts = [(tx(times[i]), ty(speeds[i])) for i in range(len(pts))]
    for i in range(len(line_pts) - 1):
        cv2.line(img, line_pts[i], line_pts[i + 1], (26, 26, 110), 2)

    # Nokta işaretler
    for p in line_pts:
        cv2.circle(img, p, 4, (26, 26, 110), -1)
        cv2.circle(img, p, 4, (255, 255, 255), 1)

    # Eksenler
    cv2.rectangle(img, (ML, MT), (ML + cw, MT + ch), (150, 150, 150), 1)

    # X ekseni etiketleri (zaman)
    n_ticks = min(5, len(times))
    for i in range(n_ticks):
        t_val = t_min + i * (t_max - t_min) / max(n_ticks - 1, 1)
        x = tx(t_val)
        cv2.line(img, (x, MT + ch), (x, MT + ch + 4), (150, 150, 150), 1)
        label = f"{t_val:.1f}s"
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)
        cv2.putText(img, label, (x - tw // 2, height - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (100, 100, 100), 1)

    # Y ekseni başlığı
    cv2.putText(img, "km/h", (2, MT + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (80, 80, 80), 1)

    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()
