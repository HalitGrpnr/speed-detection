#!/usr/bin/env python3
"""
pick_points.py — Video üzerinde nokta tıkla → kalibrasyon JSON üret

Kullanım:
  python scripts/pick_points.py --video <video.mp4> --out calibration.json

Kontroller:
  Sol tık      → nokta seç (koordinat terminale basılır, dünya koordinatı istenir)
  Sağ ok / d   → 1 kare ileri
  Sol ok / a   → 1 kare geri
  Shift + sağ  → 50 kare ileri
  Shift + sol  → 50 kare geri
  f            → belirli kareye atla
  z            → son noktayı sil
  Enter / q    → bitti, kalibrasyon hesapla ve kaydet
  Esc          → çık (kaydetme)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np

from src.calibration.models import ControlPoint
from src.calibration.homography import compute_homography, CalibrationError
from src.calibration.io import save_calibration


# Ekrana sığdırmak için max genişlik
DISPLAY_MAX_W = 1280


class PointPicker:
    def __init__(self, video_path: str, out_path: str, fps_override: float | None = None):
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError(f"Video açılamadı: {video_path}")

        self.total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = fps_override or self.cap.get(cv2.CAP_PROP_FPS)
        self.w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.out_path = out_path

        # Display scale
        self.scale = min(1.0, DISPLAY_MAX_W / self.w)
        self.dw = int(self.w * self.scale)
        self.dh = int(self.h * self.scale)

        self.frame_idx = 0
        self.frame: np.ndarray | None = None
        self.points: list[ControlPoint] = []
        self.hover: tuple[int, int] = (0, 0)

    def _read_frame(self, idx: int) -> np.ndarray:
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            return np.zeros((self.h, self.w, 3), dtype=np.uint8)
        return frame

    def _draw(self, frame: np.ndarray) -> np.ndarray:
        disp = cv2.resize(frame, (self.dw, self.dh))

        # Mevcut noktaları çiz
        for i, cp in enumerate(self.points):
            du = int(cp.pixel[0] * self.scale)
            dv = int(cp.pixel[1] * self.scale)
            cv2.circle(disp, (du, dv), 6, (0, 255, 0), -1)
            cv2.circle(disp, (du, dv), 6, (0, 0, 0), 1)
            label = f"{i+1}: ({cp.world_m[0]:.1f},{cp.world_m[1]:.1f})m"
            cv2.putText(disp, label, (du + 8, dv - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)

        # Hover koordinatı
        hu, hv = self.hover
        real_u = int(hu / self.scale)
        real_v = int(hv / self.scale)
        coord_txt = f"piksel: ({real_u}, {real_v})"
        cv2.putText(disp, coord_txt, (10, self.dh - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)

        # Üst bilgi
        info = (f"Kare {self.frame_idx}/{self.total-1}  "
                f"| Nokta: {len(self.points)}  "
                f"| Sol tık=seç  d/a=kare  z=geri al  Enter=bitti  Esc=çık")
        cv2.putText(disp, info, (10, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

        return disp

    def _mouse(self, event, x, y, flags, param):
        self.hover = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            real_u = x / self.scale
            real_v = y / self.scale
            self._on_click(real_u, real_v)

    def _on_click(self, u: float, v: float) -> None:
        n = len(self.points) + 1
        print(f"\n[Nokta {n}] Piksel: ({u:.0f}, {v:.0f})")
        print("  Dünya koordinatı X Y metre (örnek: 0.0 3.5)")
        print("  İptal için boş bırak.")
        raw = input("  > ").strip()
        if not raw:
            print("  Atlandı.")
            return
        try:
            parts = raw.replace(",", " ").split()
            if len(parts) != 2:
                raise ValueError
            world = (float(parts[0]), float(parts[1]))
        except ValueError:
            print("  ! İki sayı gerekli (örnek: 0 3.5). Atlandı.")
            return

        src_raw = input("  Kaynak [1=operator / 2=site_measurement] [1]: ").strip()
        source = "site_measurement" if src_raw == "2" else "operator"

        cp = ControlPoint(id=f"cp{n}", pixel=(u, v), world_m=world, source=source)
        self.points.append(cp)
        print(f"  ✓ Nokta {n} eklendi.")

        if len(self.points) >= 4:
            print(f"  [{len(self.points)} nokta var] Bitirmek için: 'bitti' yaz veya video penceresinde Enter/q bas.")
            ans = input("  Devam mı, bitti mi? [Enter=devam / 'bitti'=kaydet]: ").strip().lower()
            if ans in ("bitti", "b", "q", "done", "exit"):
                cv2.destroyAllWindows()
                self._finish()
                raise SystemExit(0)

    def _finish(self) -> bool:
        if len(self.points) < 4:
            print(f"\n! En az 4 nokta gerekli ({len(self.points)} girildi). Devam et.")
            return False

        print(f"\n{len(self.points)} nokta ile homografi hesaplanıyor...")
        try:
            result = compute_homography(self.points)
        except CalibrationError as e:
            print(f"Hata: {e}")
            return False

        rms_cm = result.reprojection_rms_m * 100
        print(f"  Re-projeksiyon RMS : {rms_cm:.2f} cm")
        print(f"  Güven katmanı      : {result.confidence_layer}")
        print(f"  Kullanılan         : {len(result.used_point_ids)} / {len(self.points)}")
        if result.excluded_point_ids:
            print(f"  RANSAC dışı        : {result.excluded_point_ids}")

        if rms_cm > 30:
            print("  ⚠  RMS > 30 cm — nokta eşleşmelerini kontrol et.")
        elif rms_cm > 10:
            print("  ⚠  RMS > 10 cm — daha fazla nokta eklenebilir.")
        else:
            print("  ✓ İyi kalibrasyon.")

        save_calibration(self.out_path, result, self.points, fps=self.fps)
        print(f"\nKaydedildi: {Path(self.out_path).resolve()}")
        print(f"\nHız hesabı demosu:")
        print(f'  .venv/bin/python -m src.speed.calculator "<video>" {self.out_path} --step 3')
        return True

    def run(self) -> None:
        win = "pick_points — Sol tık: nokta seç | Enter: bitti | Esc: çık"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, self.dw, self.dh)
        cv2.setMouseCallback(win, self._mouse)

        print("\nPencere açıldı.")
        print("Videonun bir karesini seç, yol üzerindeki bilinen noktalara tıkla.")
        print("d=ileri  a=geri  Shift+d=50 ileri  f=kareye atla  z=son noktayı sil\n")

        self.frame = self._read_frame(0)

        while True:
            disp = self._draw(self.frame)
            cv2.imshow(win, disp)
            key = cv2.waitKey(50) & 0xFF

            # Kare navigasyonu
            step = 1
            if key in (ord('d'), 83):   # sağ ok veya d
                self.frame_idx = min(self.frame_idx + step, self.total - 1)
                self.frame = self._read_frame(self.frame_idx)
            elif key in (ord('a'), 81): # sol ok veya a
                self.frame_idx = max(self.frame_idx - step, 0)
                self.frame = self._read_frame(self.frame_idx)
            elif key == ord('D'):       # Shift+d
                self.frame_idx = min(self.frame_idx + 50, self.total - 1)
                self.frame = self._read_frame(self.frame_idx)
            elif key == ord('A'):       # Shift+a
                self.frame_idx = max(self.frame_idx - 50, 0)
                self.frame = self._read_frame(self.frame_idx)
            elif key == ord('f'):
                cv2.destroyAllWindows()
                raw = input(f"Kare numarası gir (0–{self.total-1}): ").strip()
                try:
                    self.frame_idx = max(0, min(int(raw), self.total - 1))
                    self.frame = self._read_frame(self.frame_idx)
                except ValueError:
                    pass
                cv2.namedWindow(win, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(win, self.dw, self.dh)
                cv2.setMouseCallback(win, self._mouse)
            elif key == ord('z'):       # son noktayı sil
                if self.points:
                    removed = self.points.pop()
                    print(f"Nokta {removed.id} silindi.")
                else:
                    print("Silinecek nokta yok.")
            elif key in (13, ord('q')): # Enter veya q
                cv2.destroyAllWindows()
                self._finish()
                break
            elif key == 27:             # Esc
                print("\nİptal edildi, kaydedilmedi.")
                break

            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                cv2.destroyAllWindows()
                self._finish()
                break

        self.cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="Video üzerinde nokta seç → kalibrasyon JSON")
    parser.add_argument("--video", "-v", required=True, help="Video dosyası")
    parser.add_argument("--out", "-o", default="calibration.json", help="Çıktı JSON")
    parser.add_argument("--fps", type=float, help="FPS override (otomatik okunamazsa)")
    args = parser.parse_args()

    picker = PointPicker(args.video, args.out, fps_override=args.fps)
    print(f"Video: {picker.w}×{picker.h} @ {picker.fps:.2f} fps, {picker.total} kare")
    print(f"Görüntü {int(picker.scale*100)}% ölçekte gösterilecek "
          f"({picker.dw}×{picker.dh} px)")
    picker.run()


if __name__ == "__main__":
    main()
