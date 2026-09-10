"""Dingil adımlama hız tahmini.

Araç bir karede ön + arka teker temas noktası işaretlenirse, arka teker eski ön tekerin
dünya konumuna geldiğinde araç tam 1 dingil mesafesi (wheelbase_m) ilerlemiştir.
Bu gözlem homografi ile zemin düzleminde perspektif bozulmasından bağımsız olarak doğrudur.

Kamera/kalibrasyon hatasından bağımsız bağımsız çapraz doğrulama üretir.
Sistemin confidence_level hesabına dahil edilmez; yalnızca destekleyici kanıt.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.calibration.homography import pixel_to_world


@dataclass
class AxleStep:
    frame: float         # kesirli kare numarası (alt-kare enterpolasyon)
    distance_m: float    # kümülatif mesafe (n × wheelbase_m)


@dataclass
class AxleStepResult:
    speed_kmh: float | None
    ci_kmh: float | None
    step_count: int
    steps: list[AxleStep]
    interrupted: bool
    interrupt_reason: str | None
    initial_distance_m: float    # ön–arka teker arası ölçülen dünya mesafesi (doğrulama)


class AxleStepper:
    """Dingil adımlama: track contact_pixel'lerini dünya uzayında eşik geçişlerine göre izler.

    Kullanım:
        stepper = AxleStepper(H, front_pixel, rear_pixel, wheelbase_m=2.65, fps=25.0)
        for tp in track.points:
            stepper.feed(tp.frame, tp.contact_pixel)
        speed, ci = stepper.estimate_speed()
    """

    def __init__(
        self,
        H: np.ndarray,
        front_pixel: tuple[float, float],
        rear_pixel: tuple[float, float],
        wheelbase_m: float,
        fps: float,
        max_gap_frames: int = 10,
    ) -> None:
        w_front = np.array(pixel_to_world(H, front_pixel), dtype=np.float64)
        w_rear = np.array(pixel_to_world(H, rear_pixel), dtype=np.float64)

        diff = w_front - w_rear
        dist = float(np.linalg.norm(diff))
        if dist < 0.01:
            raise ValueError(
                "Ön ve arka teker konumları dünya uzayında çok yakın "
                f"(ölçülen mesafe: {dist:.4f} m). Farklı noktalar seçin."
            )

        self._dir: np.ndarray = diff / dist
        self._H = H
        self._wheelbase_m = wheelbase_m
        self._fps = fps
        self._max_gap = max_gap_frames
        self.initial_distance_m: float = dist

        self._steps: list[AxleStep] = []
        self._next_target: float = wheelbase_m

        # Referans: ilk feed() çağrısında kurulur
        self._w_ref: np.ndarray | None = None

        self._prev_disp: float | None = None
        self._prev_frame: int | None = None

        self.interrupted: bool = False
        self.interrupt_reason: str | None = None

    # ── internals ────────────────────────────────────────────────────────────

    def _proj(self, pixel: tuple[float, float]) -> float:
        """Pixel → dünya → referanstan projeksiyon (seyahat yönünde, metre)."""
        w = np.array(pixel_to_world(self._H, pixel), dtype=np.float64)
        if self._w_ref is None:
            self._w_ref = w
            return 0.0
        return float(np.dot(w - self._w_ref, self._dir))

    # ── public API ───────────────────────────────────────────────────────────

    def feed(self, frame_n: int, pixel: tuple[float, float]) -> list[AxleStep]:
        """Bir kareyi işle. Tamamlanan yeni adımları döndürür."""
        if self.interrupted:
            return []

        if self._prev_frame is not None:
            gap = frame_n - self._prev_frame
            if gap > self._max_gap:
                self.interrupted = True
                self.interrupt_reason = (
                    f"Track kesintisi: kare {self._prev_frame}→{frame_n} "
                    f"({gap} kare boşluk, eşik: {self._max_gap})."
                )
                return []

        disp = self._proj(pixel)
        new_steps: list[AxleStep] = []

        if self._prev_disp is not None and self._prev_frame is not None:
            d0, d1 = self._prev_disp, disp
            f0, f1 = self._prev_frame, frame_n

            # Aynı feed çağrısında birden fazla eşik geçilebilir (çok hızlı araç + büyük Δt)
            while d1 >= self._next_target > d0:
                if d1 != d0:
                    frac = (self._next_target - d0) / (d1 - d0)
                else:
                    frac = 0.0
                f_star = f0 + frac * (f1 - f0)
                step = AxleStep(frame=f_star, distance_m=self._next_target)
                self._steps.append(step)
                new_steps.append(step)
                self._next_target += self._wheelbase_m

        self._prev_disp = disp
        self._prev_frame = frame_n
        return new_steps

    def estimate_speed(self) -> tuple[float | None, float | None]:
        """(speed_kmh, ci_kmh) döndürür. < 2 adım varsa (None, None)."""
        if len(self._steps) < 2:
            return None, None

        speeds: list[float] = []
        for i in range(1, len(self._steps)):
            df = self._steps[i].frame - self._steps[i - 1].frame
            if df > 0:
                dt = df / self._fps
                speeds.append(self._wheelbase_m / dt * 3.6)

        if not speeds:
            return None, None

        v = np.array(speeds, dtype=np.float64)
        speed_kmh = float(np.median(v))
        if len(v) >= 2:
            ci_kmh = float((np.percentile(v, 75) - np.percentile(v, 25)) / 2.0)
        else:
            ci_kmh = float(abs(v[0] - speed_kmh))

        return speed_kmh, ci_kmh

    def result(self) -> AxleStepResult:
        speed_kmh, ci_kmh = self.estimate_speed()
        return AxleStepResult(
            speed_kmh=speed_kmh,
            ci_kmh=ci_kmh,
            step_count=len(self._steps),
            steps=list(self._steps),
            interrupted=self.interrupted,
            interrupt_reason=self.interrupt_reason,
            initial_distance_m=self.initial_distance_m,
        )
