#!/usr/bin/env python3
"""
make_calibration.py — İnteraktif kalibrasyon noktası girişi

Kullanım:
  python scripts/make_calibration.py --video <video.mp4> --out calibration.json

Koordinat sistemi:
  Piksel  → videonun sol üst köşesi (0,0), sağa u, aşağı v
  Dünya   → kendin seçtiğin bir orijin, metre cinsinden
            örnek: en yakın şerit çizgisi köşesi = (0, 0)
            X: sağa (şerit genişliği yönü)
            Y: uzağa (araç gidiş yönü)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Proje kökünü Python path'ine ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.calibration.models import ControlPoint
from src.calibration.homography import compute_homography, CalibrationError
from src.calibration.io import save_calibration


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nİptal edildi.")
        sys.exit(0)


def _parse_pair(text: str) -> tuple[float, float]:
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError("İki sayı girin (örnek: 320 240 veya 320,240)")
    return float(parts[0]), float(parts[1])


def _get_fps_and_meta(video_path: str | None) -> tuple[float, int | None, int | None, int | None]:
    if not video_path:
        fps_str = _ask("Video FPS [25]: ")
        fps = float(fps_str) if fps_str else 25.0
        return fps, None, None, None
    try:
        from src.detection.video import read_video_meta
        meta = read_video_meta(video_path)
        print(f"  Video: {meta.width}×{meta.height} @ {meta.fps:.2f} fps, {meta.frame_count} kare")
        override = _ask(f"  FPS doğru mu? Enter=evet veya yeni değer gir: ")
        fps = float(override) if override else meta.fps
        return fps, meta.frame_count, meta.width, meta.height
    except Exception as e:
        print(f"  Uyarı: video okunamadı ({e})")
        fps_str = _ask("  FPS manuel gir [25]: ")
        return float(fps_str) if fps_str else 25.0, None, None, None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="İnteraktif kalibrasyon noktası girişi → JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--video", "-v", help="Video dosyası (FPS/boyut otomatik okunur)")
    parser.add_argument("--out", "-o", default="calibration.json",
                        help="Çıktı JSON dosyası (varsayılan: calibration.json)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Kalibrasyon Noktası Girişi")
    print("=" * 60)
    print()
    print("Koordinat sistemi:")
    print("  Piksel  → videonun sol üst köşesi (0,0), sağa u↑, aşağı v↓")
    print("  Dünya   → metre, kendin seçtiğin orijin")
    print("            X: sağa/şerit genişliği yönü")
    print("            Y: uzağa/araç gidiş yönü")
    print()
    print("İpucu: Videonun bir karesini görüntüleyicide aç,")
    print("       imleci bilinen noktalara götür ve piksel koordinatını oku.")
    print()

    # Video metadata
    if args.video:
        print(f"Video: {args.video}")
    fps, frame_count, width, height = _get_fps_and_meta(args.video)
    print()

    # Nokta girişi
    print("En az 4 nokta gerekli, ≥6 önerilir.")
    print("Bitirmek için boş satır bırak (4+ nokta girdikten sonra).")
    print("-" * 60)

    points: list[ControlPoint] = []
    while True:
        n = len(points) + 1
        suffix = " (zorunlu)" if n <= 4 else " [Enter=bitti]"
        print(f"\nNokta {n}{suffix}")

        pix_raw = _ask("  Piksel  u v  (örnek: 874 612): ")
        if not pix_raw:
            if len(points) < 4:
                print(f"  ! En az 4 nokta gerekli ({len(points)} girildi).")
                continue
            break

        try:
            pix = _parse_pair(pix_raw)
        except ValueError as e:
            print(f"  ! Hata: {e}")
            continue

        world_raw = _ask("  Dünya   X Y  metre (örnek: 0.0 3.5): ")
        if not world_raw:
            print("  ! Dünya koordinatı boş bırakılamaz.")
            continue

        try:
            world = _parse_pair(world_raw)
        except ValueError as e:
            print(f"  ! Hata: {e}")
            continue

        src_choice = _ask("  Kaynak  [1=operator / 2=site_measurement] [1]: ")
        source = "site_measurement" if src_choice.strip() == "2" else "operator"

        cp = ControlPoint(
            id=f"cp{n}",
            pixel=pix,
            world_m=world,
            source=source,
        )
        points.append(cp)
        print(f"  ✓ Nokta {n} eklendi: piksel={pix} → dünya={world} ({source})")

    print()
    print("-" * 60)
    print(f"Toplam {len(points)} nokta girildi. Homografi hesaplanıyor...")

    try:
        result = compute_homography(points)
    except CalibrationError as e:
        print(f"\nHata: {e}")
        sys.exit(1)

    print(f"\nHomografi başarıyla hesaplandı.")
    print(f"  Re-projeksiyon RMS : {result.reprojection_rms_m * 100:.2f} cm")
    print(f"  Güven katmanı      : {result.confidence_layer}")
    print(f"  Kullanılan nokta   : {len(result.used_point_ids)} / {len(points)}")
    if result.excluded_point_ids:
        print(f"  RANSAC dışı (outlier): {result.excluded_point_ids}")

    # RMS uyarısı
    if result.reprojection_rms_m > 0.3:
        print()
        print("  ⚠  RMS > 30 cm — kalibrasyon zayıf olabilir.")
        print("     Kontrol et: dünya koordinatları doğru mu? Nokta eşleşmeleri hatalı mı?")
    elif result.reprojection_rms_m > 0.1:
        print("  ⚠  RMS > 10 cm — kabul edilebilir, ama mümkünse daha fazla nokta ekle.")
    else:
        print("  ✓ RMS < 10 cm — iyi kalibrasyon.")

    # JSON kaydet
    out_path = Path(args.out)
    save_calibration(
        out_path,
        result,
        points,
        fps=fps,
        fps_source="container" if args.video else "operator_override",
    )
    print()
    print(f"Kaydedildi: {out_path.resolve()}")
    print()
    print("Sonraki adım — hız hesabı demosu:")
    video_arg = f'"{args.video}"' if args.video else "<video.mp4>"
    print(f"  .venv/bin/python -m src.speed.calculator {video_arg} {out_path} --step 3")


if __name__ == "__main__":
    main()
