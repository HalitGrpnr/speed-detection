from __future__ import annotations


def interpolate_calibration_point(
    frame_n_px: tuple[float, float],
    frame_n1_px: tuple[float, float],
    target_px: tuple[float, float],
) -> tuple[tuple[float, float], float]:
    """Sub-frame interpolation for calibration bracket mode.

    Given the wheel position in two consecutive frames (N and N+1) that bracket
    the target longitudinal position, compute the sub-pixel position where the
    wheel would have aligned exactly with the target.

    The interpolation axis is chosen as the one with the greatest displacement
    between frames (primary movement axis). The result keeps the target value
    on that axis and interpolates the other axis.

    Returns:
        (interpolated_pixel, t) where t ∈ [0, 1] is the fractional frame offset.

    Raises:
        ValueError: if frame_n and frame_n1 are the same pixel (no movement).
    """
    dx = frame_n1_px[0] - frame_n_px[0]
    dy = frame_n1_px[1] - frame_n_px[1]

    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        raise ValueError("frame_n and frame_n1 are the same pixel — cannot interpolate.")

    if abs(dy) >= abs(dx):
        if abs(dy) < 1e-9:
            t = 0.0
        else:
            t = (target_px[1] - frame_n_px[1]) / dy
        interp_x = frame_n_px[0] + t * dx
        return (interp_x, target_px[1]), t
    else:
        if abs(dx) < 1e-9:
            t = 0.0
        else:
            t = (target_px[0] - frame_n_px[0]) / dx
        interp_y = frame_n_px[1] + t * dy
        return (target_px[0], interp_y), t
