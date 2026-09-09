from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .lane import detect_lane_edges, fit_lane_line, sample_line_at_depths
from .markers import detect_dashed_markers, estimate_depth_scale
from .models import ProposedPoint

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_COLOR_LEFT = (255, 180, 0)     # BGR: mavi-turuncu → sol
_COLOR_RIGHT = (0, 180, 255)    # BGR: sarı-turuncu → sağ
_DEPTH_LABELS = {0: "near", 1: "mid", 2: "far"}


def _vanishing_point_y(
    m_l: float, b_l: float, m_r: float, b_r: float
) -> float | None:
    """İki şerit doğrusunun piksel-uzayındaki kesişim noktasının Y koordinatı.

    Kaçış noktası (vanishing point) perspektif derinlik tahmini için gereklidir.
    Çizgiler yakın paralel ise None döner.
    """
    if abs(m_l - m_r) < 1e-9:
        return None
    x_vp = (b_r - b_l) / (m_l - m_r)
    return float(m_l * x_vp + b_l)


def _y_world_perspective(
    y_px: float, y_near_px: float, y_vp: float, d_near_m: float
) -> float:
    """Kaçış noktasına dayalı perspektif derinlik formülü.

    Düzlem yüzey varsayımıyla: D(y) = D_near * (y_near - y_vp) / (y - y_vp)
    Y_world = D(y) - D_near
    """
    denom = y_px - y_vp
    if abs(denom) < 1.0:
        return 0.0
    ratio = (y_near_px - y_vp) / denom
    return float(d_near_m * (ratio - 1.0))


class AutoProposer:
    """Video karesi üzerinden kalibrasyon kontrol noktası öneren sınıf."""

    def __init__(
        self,
        lane_width_m: float = 3.5,
        dash_length_m: float = 3.0,
        n_sample_depths: int = 3,
        roi_top_ratio: float = 0.45,
        d_near_m: float = 5.0,
    ) -> None:
        self.lane_width_m = lane_width_m
        self.dash_length_m = dash_length_m
        self.n_sample_depths = n_sample_depths
        self.roi_top_ratio = roi_top_ratio
        self.d_near_m = d_near_m  # kamera altındaki yakın noktanın tahmini mesafesi (m)

    def propose(self, frame: np.ndarray) -> list[ProposedPoint]:
        """Şerit + marker tespiti → öneri kontrol noktaları listesi."""
        h, w = frame.shape[:2]
        roi_top = int(h * self.roi_top_ratio)

        left_pts, right_pts = detect_lane_edges(
            frame, roi_top_ratio=self.roi_top_ratio
        )
        if left_pts is None and right_pts is None:
            return []

        markers = detect_dashed_markers(frame, roi_top_ratio=self.roi_top_ratio)
        px_per_m = estimate_depth_scale(markers, self.dash_length_m)

        line_left = fit_lane_line(left_pts) if left_pts is not None else None
        line_right = fit_lane_line(right_pts) if right_pts is not None else None

        # Y örnekleme: tabandan (yakın) ROI üstüne (uzak)
        y_near = float(h - 1)
        y_far = float(roi_top + int((h - roi_top) * 0.1))
        y_samples = np.linspace(y_near, y_far, self.n_sample_depths).tolist()

        # Kaçış noktası (her iki şerit varsa) + yatay ölçek (fallback)
        y_vp: float | None = None
        px_per_m_lateral: float | None = None
        if line_left is not None and line_right is not None:
            m_l, b_l = line_left
            m_r, b_r = line_right
            # Kaçış noktası — perspektif derinlik için
            vp_candidate = _vanishing_point_y(m_l, b_l, m_r, b_r)
            if vp_candidate is not None and vp_candidate < y_near - 10:
                y_vp = vp_candidate
            # Yatay ölçek — fallback
            if abs(m_l) > 1e-9 and abs(m_r) > 1e-9:
                x_left_near = (y_near - b_l) / m_l
                x_right_near = (y_near - b_r) / m_r
                lane_px = abs(x_right_near - x_left_near)
                if lane_px > 5:
                    px_per_m_lateral = lane_px / self.lane_width_m

        proposals: list[ProposedPoint] = []

        for side, line_params, x_world_val in [
            ("left",  line_left,  0.0),
            ("right", line_right, self.lane_width_m),
        ]:
            if line_params is None:
                continue
            m, b = line_params
            samples = sample_line_at_depths(m, b, y_samples)

            for i, (x_px, y_px) in enumerate(samples):
                # Seçenek B (T5): görüntü sınırı dışına çıkan önerileri bastır.
                # Sığ polyfit + uzağa ekstrapolasyon gerçek görüntülerde sınır-dışı
                # x koordinatları üretebilir; operatörü yanıltmamak için atlanır.
                if not (0 <= x_px < w and 0 <= y_px < h):
                    continue
                y_world = self._y_world(y_px, y_near, px_per_m, px_per_m_lateral, i, y_vp)
                depth_tag = _DEPTH_LABELS.get(i, f"d{i}")
                conf = round(max(0.3, 0.90 - i * 0.12), 2)
                # Y kaynağını description'a ekle — operatör ne kadar güvenmeli bilsin
                y_src = "marker" if px_per_m else ("vp" if y_vp else "lateral")
                proposals.append(ProposedPoint(
                    pixel=(float(x_px), float(y_px)),
                    world_m=(float(x_world_val), float(y_world)),
                    detection_confidence=conf,
                    description=f"{side}_lane_{depth_tag} [y:{y_src}]",
                ))

        return proposals

    def _y_world(
        self,
        y_px: float,
        y_near_px: float,
        px_per_m: float | None,
        px_per_m_lateral: float | None,
        sample_idx: int,
        y_vp: float | None = None,
    ) -> float:
        if px_per_m is not None:
            # Kesik çizgi ölçeği — en güvenilir
            return (y_near_px - y_px) / px_per_m
        if y_vp is not None:
            # Perspektif formülü (kaçış noktası) — lateral ölçekten çok daha doğru
            return _y_world_perspective(y_px, y_near_px, y_vp, self.d_near_m)
        if px_per_m_lateral is not None:
            # Yatay ölçek fallback — perspektif bozukluğu nedeniyle hatalı olabilir
            return (y_near_px - y_px) / px_per_m_lateral
        # Son çare: sabit ızgara
        return float(sample_idx * self.d_near_m)

    def draw_proposals(
        self,
        frame: np.ndarray,
        proposals: list[ProposedPoint],
    ) -> np.ndarray:
        """Önerileri kare üzerine çiz — daire + etiket."""
        out = frame.copy()
        for i, p in enumerate(proposals):
            color = _COLOR_LEFT if "left" in p.description else _COLOR_RIGHT
            cx, cy = int(p.pixel[0]), int(p.pixel[1])
            cv2.circle(out, (cx, cy), 8, color, -1)
            cv2.circle(out, (cx, cy), 10, (255, 255, 255), 1)
            label = f"p{i} ({p.world_m[0]:.1f},{p.world_m[1]:.1f})m"
            cv2.putText(out, label, (cx + 12, cy + 4),
                        _FONT, 0.45, color, 1, cv2.LINE_AA)
        return out


def _load_frame(path: str, frame_idx: int = 0) -> np.ndarray:
    """Dosyadan kare yükle: görüntü dosyası veya video."""
    p = Path(path)
    suffix = p.suffix.lower()
    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

    if suffix in image_exts:
        frame = cv2.imread(str(p))
        if frame is None:
            raise IOError(f"Görüntü açılamadı: {p}")
        return frame

    # Video
    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        raise IOError(f"Video açılamadı: {p}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise IOError(f"Kare {frame_idx} okunamadı: {p}")
    return frame


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Otomatik kalibrasyon noktası önerici")
    parser.add_argument("input", help="Görüntü veya video dosyası")
    parser.add_argument("--frame", type=int, default=0, help="Video karesi (varsayılan: 0)")
    parser.add_argument("--lane-width", type=float, default=3.5, help="Şerit genişliği (m)")
    parser.add_argument("--dash-length", type=float, default=3.0,
                        help="Kesik çizgi boyu (m, varsayılan 3.0)")
    parser.add_argument("--n-depths", type=int, default=3,
                        help="Her şeritte örneklenecek derinlik sayısı")
    parser.add_argument("--out", default="proposer_output.png",
                        help="Overlay çıktı dosyası")
    args = parser.parse_args()

    print(f"Kare {args.frame} analiz ediliyor: {args.input}")
    frame = _load_frame(args.input, args.frame)

    proposer = AutoProposer(
        lane_width_m=args.lane_width,
        dash_length_m=args.dash_length,
        n_sample_depths=args.n_depths,
    )

    # İç durumu raporlamak için ayrı çağrılar
    left_pts, right_pts = detect_lane_edges(frame)
    markers = detect_dashed_markers(frame)
    px_per_m = estimate_depth_scale(markers, args.dash_length)

    left_status = f"sol {'✓' if left_pts is not None else '✗'}"
    right_status = f"sag {'✓' if right_pts is not None else '✗'}"
    marker_info = f"{len(markers)} segment"
    if px_per_m:
        marker_info += f" — olcek: {px_per_m:.1f} px/m"
    print(f"Serit kenarlari: {left_status}, {right_status}")
    print(f"Kesik cizgi: {marker_info}")
    print()

    proposals = proposer.propose(frame)

    if not proposals:
        print("Hicbir oneri uretilmedi (serit tespit edilemedi).")
        sys.exit(0)

    header = f"{'ID':<14} | {'Piksel (u,v)':<16} | {'Dunya (X,Y) m':<18} | {'Guven':<6} | Aciklama"
    print("Onerilen kontrol noktalari (operator onayindan gecirilmeli):")
    print(header)
    print("-" * len(header))
    for i, p in enumerate(proposals):
        pid = f"cp_auto_{i}"
        pix = f"({p.pixel[0]:.0f}, {p.pixel[1]:.0f})"
        world = f"({p.world_m[0]:.1f}, {p.world_m[1]:.1f})"
        print(f"  {pid:<12} | {pix:<16} | {world:<18} | {p.detection_confidence:<6.2f} | {p.description}")

    if px_per_m:
        print()
        print("UYARI: Y koordinatlari kesik cizgi olcegiyle tahmin edilmistir.")
        print("       Dunya koordinatlarini operator dogrulamalidir.")
    else:
        print()
        print("UYARI: Kesik cizgi tespit edilemedi — Y koordinatlari serit")
        print("       genisliginden (yatay olcek) tahmin edilmistir, yaklasiktir.")

    overlay = proposer.draw_proposals(frame, proposals)
    cv2.imwrite(args.out, overlay)
    print(f"\nOverlay kaydedildi: {args.out}")
