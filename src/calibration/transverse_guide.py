from __future__ import annotations

import math


def compute_transverse_direction(
    road_p1: tuple[float, float],
    road_p2: tuple[float, float],
) -> tuple[float, float]:
    """Compute the approximate transverse (cross-road) direction from two road-direction pixels.

    Rotates the road direction vector 90° CCW (perpendicular in image space).
    Valid for overhead/high-angle CCTV cameras where elevation is sufficient.
    For low-angle cameras the error grows — operator can override via manual
    VP_transverse selection (Seçenek C fallback).

    Returns:
        Normalized (dx, dy) transverse direction vector.
    """
    dx_road = road_p2[0] - road_p1[0]
    dy_road = road_p2[1] - road_p1[1]
    # 90° CCW rotation: (dx, dy) → (-dy, dx)
    perp_x = -dy_road
    perp_y = dx_road
    length = math.hypot(perp_x, perp_y)
    if length < 1e-9:
        return (1.0, 0.0)
    return (perp_x / length, perp_y / length)


def guide_line_endpoints(
    wheel_px: tuple[float, float],
    transverse_dir: tuple[float, float],
    canvas_w: int,
    canvas_h: int,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Compute the two endpoints of the transverse guide line through wheel_px, clipped to canvas.

    Returns:
        ((x1, y1), (x2, y2)) — endpoints of the guide line segment.
    """
    dx, dy = transverse_dir
    t_min, t_max = -1e6, 1e6

    if abs(dx) > 1e-9:
        t_lo = -wheel_px[0] / dx
        t_hi = (canvas_w - wheel_px[0]) / dx
        t_min = max(t_min, min(t_lo, t_hi))
        t_max = min(t_max, max(t_lo, t_hi))
    if abs(dy) > 1e-9:
        t_lo = -wheel_px[1] / dy
        t_hi = (canvas_h - wheel_px[1]) / dy
        t_min = max(t_min, min(t_lo, t_hi))
        t_max = min(t_max, max(t_lo, t_hi))

    p1 = (wheel_px[0] + t_min * dx, wheel_px[1] + t_min * dy)
    p2 = (wheel_px[0] + t_max * dx, wheel_px[1] + t_max * dy)
    return p1, p2
