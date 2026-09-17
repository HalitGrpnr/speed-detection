from __future__ import annotations

import io
import os
from pathlib import Path

import cv2
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)

from src.reliability.confidence import (
    _HIGH_RMS_M, _HIGH_FRAME,
    _MEDIUM_RMS_M, _MEDIUM_FRAME,
    _REL_CI_LOW, _REL_CI_HIGH, _REL_SMOOTH_LOW,
)
from .models import PipelineResult

_MARGIN = 2 * cm
_FONTS_DIR = Path(__file__).parent / "fonts"

# ReportLab standart fontları Türkçe karakterleri desteklemez.
# DejaVuSans TTF kayıt edilir; tüm paragraflar bu fontu kullanır.
_FONT_NORMAL = "DejaVuSans"
_FONT_BOLD = "DejaVuSans-Bold"

def _register_fonts() -> None:
    global _FONT_NORMAL, _FONT_BOLD  # noqa: PLW0603
    regular = _FONTS_DIR / "DejaVuSans.ttf"
    bold = _FONTS_DIR / "DejaVuSans-Bold.ttf"
    if regular.exists():
        pdfmetrics.registerFont(TTFont(_FONT_NORMAL, str(regular)))
        if bold.exists():
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(bold)))
        else:
            _FONT_BOLD = _FONT_NORMAL
    else:
        # Geliştirme ortamında matplotlib üzerinden bul
        try:
            import matplotlib
            ml_dir = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
            pdfmetrics.registerFont(TTFont(_FONT_NORMAL, str(ml_dir / "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(ml_dir / "DejaVuSans-Bold.ttf")))
            return
        except Exception:
            pass
        # Son çare: sistem fontuna geri dön (Türkçe karakterler kırık olabilir)
        _FONT_NORMAL = "Helvetica"
        _FONT_BOLD = "Helvetica-Bold"

_register_fonts()

_CONFIDENCE_TR = {"high": "Yüksek", "medium": "Orta", "low": "Düşük"}
_LAYER_TR = {
    "standard_assumption": "Standart Varsayım",
    "operator": "Operatör (Elle Kalibrasyon)",
    "site_measurement": "Saha Ölçümü",
}

# Durma mesafesi sabitleri (kuru asfalt, standart araç)
_REACTION_TIME_S = 1.0     # saniye
_DECELERATION_MS2 = 7.5    # m/s²


def _stopping_distance_m(speed_kmh: float) -> float:
    """v km/h'de toplam durma mesafesi (m): tepki yolu + frenleme yolu."""
    v = speed_kmh / 3.6  # m/s
    d_reaction = v * _REACTION_TIME_S
    d_brake = v**2 / (2 * _DECELERATION_MS2)
    return d_reaction + d_brake


def _styles():
    s = getSampleStyleSheet()

    def _add(name, parent_name, **kwargs):
        parent = s[parent_name]
        # fontName gelen kwargs'da yoksa default _FONT_NORMAL ekle
        kwargs.setdefault("fontName", _FONT_NORMAL)
        s.add(ParagraphStyle(name, parent=parent, **kwargs))

    # Mevcut stilleri fontName ile override et
    for style_name in ("Normal", "BodyText", "Italic", "Heading1", "Heading2",
                       "Heading3", "Title", "Bullet"):
        if style_name in s:
            s[style_name].fontName = _FONT_NORMAL

    _add("SectionTitle", "Heading2",
         spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a1a6e"),
         fontName=_FONT_BOLD)
    _add("Note", "Normal",
         fontSize=8, textColor=colors.gray, spaceAfter=4)
    _add("Bold", "Normal",
         fontName=_FONT_BOLD)
    return s


def _kv_table_style() -> TableStyle:
    return TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME",  (1, 0), (1, -1), _FONT_NORMAL),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("GRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _header_table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a6e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTNAME",   (0, 1), (-1, -1), _FONT_NORMAL),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("FONTSIZE",   (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f8")]),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#aaaacc")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _class_for_track(track_id: int, result: PipelineResult) -> str:
    for t in result.tracks:
        if t.track_id == track_id:
            return t.vehicle_class
    return "—"


def _capture_annotated_frame(video_path: str, control_points: list) -> bytes | None:
    """Video'dan bir kare al, kontrol noktalarını üzerine çiz, PNG bytes döndür."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return None

        h, w = frame.shape[:2]

        # Kontrol noktalarını üzerine çiz
        colors_bgr = [
            (0, 200, 0),    # yeşil
            (0, 100, 255),  # turuncu
            (255, 0, 0),    # mavi
            (0, 0, 220),    # kırmızı
            (200, 200, 0),  # cyan
            (255, 0, 255),  # mor
            (0, 165, 255),  # turuncu-2
            (0, 255, 255),  # sarı
        ]
        for i, cp in enumerate(control_points):
            px, py = int(cp.pixel[0]), int(cp.pixel[1])
            if 0 <= px < w and 0 <= py < h:
                c = colors_bgr[i % len(colors_bgr)]
                cv2.circle(frame, (px, py), 8, c, -1)
                cv2.circle(frame, (px, py), 10, (255, 255, 255), 2)
                label = f"{cp.id}"
                cv2.putText(frame, label, (px + 13, py + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, label, (px + 13, py + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, c, 1, cv2.LINE_AA)

        ok2, buf = cv2.imencode(".png", frame)
        if ok2:
            return bytes(buf)
        return None
    except Exception:
        return None


def collect_report_texts(result: PipelineResult) -> list[str]:
    """Raporda yer alacak tüm metin bloklarını döndür (test ve audit için)."""
    meta = result.video_meta
    cal = result.calibration_result
    point_count = len(cal.used_point_ids)
    texts = [
        "Araç Hız Tespit Raporu",
        "Yöntem Özeti",
        "Kalibrasyon",
        "Hız Sonuçları",
        "Varsayımlar ve Sınırlamalar",
        _LAYER_TR.get(cal.confidence_layer, cal.confidence_layer),
        f"{cal.reprojection_rms_m * 100:.1f} cm",
        "UYARI" if cal.planarity_warning else "Yok",
        "redundancy_uyari" if point_count < 6 else "redundancy_ok",
    ]
    if result.video_sha256:
        texts.append(result.video_sha256)
    if cal.loo_rms_m is not None:
        texts.append(f"loo_rms:{cal.loo_rms_m * 100:.1f}cm")
    for est in result.speed_estimates:
        texts.append(f"{est.value_kmh:.1f}")
        texts.append(f"±{est.ci_kmh:.1f}")
        texts.append(_CONFIDENCE_TR[est.confidence_level])
        if est.track_quality.frame_count < 5:
            texts.append("yetersiz")
    return texts


def _build_story(
    result: PipelineResult,
    axle_checks: list[dict] | None = None,
    wheel_speeds: list[dict] | None = None,
    wheel_speed_profiles: list[dict] | None = None,
    speed_limit_kmh: float | None = None,
) -> list:
    S = _styles()
    meta = result.video_meta
    cal = result.calibration_result
    video_name = os.path.basename(result.video_path)
    dur_s = meta.frame_count / meta.fps if meta.fps > 0 else 0.0
    story = []

    # ── 1. Başlık ve Meta ──────────────────────────────────────────────────────
    story.append(Paragraph("Araç Hız Tespit Raporu", S["Title"]))
    story.append(Spacer(1, 0.3 * cm))

    meta_rows = [
        ["Rapor Tarihi", result.processed_at],
        ["Video Dosyası", video_name],
        ["Çözünürlük", f"{meta.width} x {meta.height} piksel"],
        ["FPS", f"{meta.fps:.3f} ({meta.fps_source})"],
        ["Toplam Kare", str(meta.frame_count)],
        ["Video Süresi", f"{dur_s:.2f} sn"],
        ["İşleme Adımı", f"frame_step = {result.frame_step}"],
        ["Model", result.model_name],
    ]
    if result.video_sha256:
        meta_rows.append(["Video SHA-256", result.video_sha256])
    t = Table(meta_rows, colWidths=[5 * cm, 11 * cm])
    t.setStyle(_kv_table_style())
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # ── 1b. Video Karesi + Kontrol Noktaları ──────────────────────────────────
    frame_png = _capture_annotated_frame(result.video_path, result.control_points)
    if frame_png:
        story.append(Paragraph("Video — Kalibrasyon Kontrol Noktaları", S["SectionTitle"]))
        story.append(Paragraph(
            "Aşağıdaki görsel videonun ilk karesini göstermektedir. Renkli noktalar, "
            "operatörün görüntü koordinatı ile gerçek dünya mesafesini eşleştirdiği "
            "kalibrasyon kontrol noktalarını temsil etmektedir.",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))
        img_reader = ImageReader(io.BytesIO(frame_png))
        iw, ih = img_reader.getSize()
        max_w = A4[0] - 2 * _MARGIN
        max_h = 8 * cm
        scale = min(max_w / iw, max_h / ih, 1.0)
        story.append(Image(io.BytesIO(frame_png), width=iw * scale, height=ih * scale))
        story.append(Spacer(1, 0.4 * cm))

    # ── 1c. Yöntem Özeti ──────────────────────────────────────────────────────
    story.append(Paragraph("Yöntem Özeti — Hız Nasıl Hesaplanır?", S["SectionTitle"]))

    method_paragraphs = [
        (
            "Kalibrasyonda operatör, videodaki yolu bir referans düzlemi olarak tanımlar. "
            "Gerçek dünya mesafesi bilinen noktalar (şerit genişliği ~3,5 m; araç plakası "
            "520 × 110 mm gibi) görüntü üzerinde işaretlenerek görüntü piksel koordinatları "
            "ile yol üzerindeki gerçek metrik koordinatlar arasında bir homografi matrisi (H) "
            "kurulur. H sayesinde görüntüdeki herhangi bir noktanın yolda kaç metreye karşılık "
            "geldiği bilinir."
        ),
        (
            "Araç tespiti ve takibi YOLO + ByteTrack algoritması ile gerçekleştirilir. "
            "Hız hesabında aracın kütlemerkezi değil, tekerlek-zemin temas noktası kullanılır; "
            "çünkü kamera açısından kaynaklanan paralaks hatası kütlemerkezini yanlı kılar. "
            "Temas noktası her karede H matrisi ile gerçek dünya koordinatına dönüştürülür; "
            "iki ardışık kare arasında kat edilen mesafe (m), videonun kare hızı (FPS) ile "
            "birleştirilerek km/h cinsinden hız elde edilir."
        ),
        (
            "Ölçüm kalitesi: Her hız tahmini bir güven aralığı (örn. 52 ± 3 km/h) ve güven "
            "seviyesi (Yüksek / Orta / Düşük) taşır. Kalibrasyon hatası re-projeksiyon RMS "
            "(cm cinsinden) ve bırak-bir-çıkar (LOO) çapraz doğrulama ile ölçülür. "
            "Tüm adımlar, operatör kararları ve dosya bütünlüğü (SHA-256) kayıt altına alınır; "
            "sonuç bağımsız olarak doğrulanabilir."
        ),
    ]
    for para in method_paragraphs:
        story.append(Paragraph(para, S["Normal"]))
        story.append(Spacer(1, 0.15 * cm))
    story.append(Spacer(1, 0.35 * cm))

    # ── 2. Kalibrasyon ────────────────────────────────────────────────────────
    story.append(Paragraph("Kalibrasyon", S["SectionTitle"]))

    rms_m = cal.reprojection_rms_m
    if cal.planarity_warning:
        planarity_str = "UYARI — yüzey eğimi / düzlemsellik sorunu tespit edildi"
    elif not cal.planarity_evaluated:
        planarity_str = "Değerlendirilemedi (yetersiz nokta veya derinlik çeşitliliği yok)"
    else:
        planarity_str = "Yok"

    point_count = len(cal.used_point_ids)
    redundancy_ok = point_count >= 6

    loo_str = (
        f"{cal.loo_rms_m * 100:.1f} cm  ({cal.loo_rms_m:.4f} m)"
        if cal.loo_rms_m is not None
        else ("Yetersiz nokta (< 5)" if not redundancy_ok else "—")
    )
    redundancy_str = (
        "Yeterli (≥ 6 nokta)"
        if redundancy_ok
        else f"UYARI — yalnızca {point_count} nokta. 4-nokta çözümünde RMS ≈ 0 anlamsızdır."
    )

    # Referans mesafeleri: kontrol noktalarının dünya koordinat aralığı
    world_xs = [cp.world_m[0] for cp in result.control_points]
    world_ys = [cp.world_m[1] for cp in result.control_points]
    calib_range_x = max(world_xs) - min(world_xs) if world_xs else 0.0
    calib_range_y = max(world_ys) - min(world_ys) if world_ys else 0.0

    cal_rows = [
        ["Güven Katmanı", _LAYER_TR.get(cal.confidence_layer, cal.confidence_layer)],
        ["Re-projeksiyon RMS (ölçüm hata payı)", f"{rms_m * 100:.1f} cm  ({rms_m:.4f} m)"],
        ["LOO Çapraz Doğrulama RMS", loo_str],
        ["Kalibrasyon Redundancy", redundancy_str],
        ["Düzlemsellik Uyarısı", planarity_str],
        ["Kullanılan Nokta Sayısı", str(point_count)],
        ["Kalibrasyon Alanı (enine)", f"{calib_range_x:.2f} m"],
        ["Kalibrasyon Alanı (boyuna)", f"{calib_range_y:.2f} m"],
    ]
    t2 = Table(cal_rows, colWidths=[6 * cm, 10 * cm])
    t2.setStyle(_kv_table_style())
    story.append(t2)

    if cal.holdout_rows:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Held-out Doğrulama Noktaları", S["Heading3"]))
        ho_header = ["Nokta ID", "Ölçülen (m)", "Tahmin (m)", "Hata (m)"]
        ho_rows = [ho_header]
        for row in cal.holdout_rows:
            meas = row.get("measured_m", (0, 0))
            pred = row.get("predicted_m", (0, 0))
            ho_rows.append([
                row.get("id", "?"),
                f"({meas[0]:.3f}, {meas[1]:.3f})",
                f"({pred[0]:.3f}, {pred[1]:.3f})",
                f"{row.get('error_m', 0.0):.4f} m",
            ])
        t_ho = Table(ho_rows, colWidths=[3 * cm, 4 * cm, 4 * cm, 5 * cm])
        t_ho.setStyle(_header_table_style())
        story.append(t_ho)

    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Kontrol Noktaları", S["Heading3"]))
    cp_header = ["ID", "Piksel (u, v)", "Dünya (X m, Y m)", "Kaynak", "Hold-out"]
    cp_rows = [cp_header]
    for cp in result.control_points:
        cp_rows.append([
            cp.id,
            f"({cp.pixel[0]:.0f}, {cp.pixel[1]:.0f})",
            f"({cp.world_m[0]:.3f}, {cp.world_m[1]:.3f})",
            cp.source,
            "Evet" if cp.held_out else "-",
        ])
    t3 = Table(cp_rows, colWidths=[2 * cm, 3.5 * cm, 3.5 * cm, 4 * cm, 3 * cm])
    t3.setStyle(_header_table_style())
    story.append(t3)
    story.append(Spacer(1, 0.5 * cm))

    # ── 2c. Kuş Bakışı Plan Görünüm ───────────────────────────────────────────
    if result.plan_view_png:
        story.append(Paragraph("Kuş Bakışı Görünüm (Plan View)", S["SectionTitle"]))
        story.append(Paragraph(
            "Aşağıdaki görsel, kalibre edilen yol düzleminin tepeden bir projeksiyonudur — "
            "gerçek bir havadan fotoğraf değildir. Yalnızca kontrol noktalarının kapsadığı "
            "bölge güvenilir ölçek taşır; ince gri çizgiler 1 metre aralıklıdır.",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))
        img_reader = ImageReader(io.BytesIO(result.plan_view_png))
        iw, ih = img_reader.getSize()
        max_w = A4[0] - 2 * _MARGIN
        max_h = 10 * cm
        scale = min(max_w / iw, max_h / ih, 1.0)
        story.append(Image(io.BytesIO(result.plan_view_png), width=iw * scale, height=ih * scale))
        story.append(Spacer(1, 0.5 * cm))

    # ── 3. Hız Sonuçları ──────────────────────────────────────────────────────
    story.append(Paragraph("Hız Sonuçları", S["SectionTitle"]))

    speed_header = [
        "Track ID", "Araç Tipi", "Hız (km/h)", "CI ± (km/h)",
        "Güven", "Kare Sayısı", "Oklüzyon",
    ]
    speed_rows = [speed_header]
    low_frame_ids = []

    for est in sorted(result.speed_estimates, key=lambda e: e.track_id):
        frames = est.track_quality.frame_count
        row = [
            f"#{est.track_id}",
            _class_for_track(est.track_id, result),
            f"{est.value_kmh:.1f}",
            f"± {est.ci_kmh:.1f}",
            _CONFIDENCE_TR[est.confidence_level],
            str(frames),
            "Var" if est.track_quality.has_occlusion else "-",
        ]
        speed_rows.append(row)
        if frames < 5:
            low_frame_ids.append(est.track_id)

    t4 = Table(
        speed_rows,
        colWidths=[1.8 * cm, 2.8 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.4 * cm],
    )
    t4.setStyle(_header_table_style())
    story.append(t4)

    if low_frame_ids:
        ids_str = ", ".join(f"#{i}" for i in low_frame_ids)
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"Not: Track(ler) {ids_str} yetersiz kare sayısına sahip (< 5). "
            "Bu sonuçlar güvenilmez olabilir.",
            S["Note"],
        ))

    # T21: Tekerlek hız doğrulaması durumu (forensic şeffaflık)
    wheel_done = bool(wheel_speeds or wheel_speed_profiles)
    if wheel_done:
        wheel_status = (
            "YAPILDI — Tekerlek temas noktası ölçümü tamamlandı. "
            "Birincil hız aşağıdaki 'Operatör-Tekerlek Hız Ölçümü' bölümündedir."
        )
    else:
        wheel_status = (
            "YAPILMADI — Bu tablodaki değerler homografi tabanlı ön tahminlerdir (bbox). "
            "Paralaks hatası nedeniyle sistematik olarak düşük olabilir (~%8). "
            "Bilirkişi raporunda birincil hız için tekerlek temas noktası "
            "doğrulaması yapılması önem taşır."
        )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"Tekerlek hız doğrulaması: {wheel_status}", S["Note"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── 3b. Hız Limiti Karşılaştırması ───────────────────────────────────────
    if speed_limit_kmh is not None and speed_limit_kmh > 0:
        story.append(Paragraph("Hız Limiti Karşılaştırması ve Durma Mesafesi", S["SectionTitle"]))
        story.append(Paragraph(
            "Aşağıdaki tablo, tespit edilen hızı mahallin hız limitiyle karşılaştırmaktadır. "
            "Durma mesafesi hesabı standart trafik mühendisliği formülüne göre yapılmıştır: "
            f"d = v·t_r + v²/(2·a) — tepki süresi t_r = {_REACTION_TIME_S:.1f} sn, "
            f"yavaşlama a = {_DECELERATION_MS2:.1f} m/s² (kuru asfalt, standart araç).",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))

        # Birincil hızı belirle: tekerlek hızı varsa onu, yoksa bbox hızını kullan
        primary_speeds: list[tuple[str, float, float]] = []  # (label, speed_kmh, ci_kmh)
        if wheel_speeds:
            for ws in sorted(wheel_speeds, key=lambda w: w.get("track_id", 0)):
                label = f"Track #{ws.get('track_id', '?')} (tekerlek)"
                primary_speeds.append((label, ws.get("value_kmh", 0.0), ws.get("ci_kmh", 0.0)))
        elif wheel_speed_profiles:
            for prof in sorted(wheel_speed_profiles, key=lambda p: p.get("track_id", 0)):
                label = f"Track #{prof.get('track_id', '?')} (profil)"
                primary_speeds.append((
                    label,
                    prof.get("summary_value_kmh", 0.0),
                    prof.get("summary_ci_kmh", 0.0),
                ))
        else:
            for est in sorted(result.speed_estimates, key=lambda e: e.track_id):
                label = f"Track #{est.track_id} (bbox)"
                primary_speeds.append((label, est.value_kmh, est.ci_kmh))

        limit_d = _stopping_distance_m(speed_limit_kmh)

        limit_row_header = ["Ölçüm", "Tespit (km/h)", "Limit (km/h)", "Aşım (km/h)",
                            "Durma — Tespit (m)", "Durma — Limit (m)", "Fark (m)"]
        limit_rows = [limit_row_header]
        for label, spd, ci in primary_speeds:
            spd_d = _stopping_distance_m(spd)
            excess = spd - speed_limit_kmh
            excess_str = f"+ {excess:.1f}" if excess > 0 else f"{excess:.1f}"
            limit_rows.append([
                label,
                f"{spd:.1f} ± {ci:.1f}",
                f"{speed_limit_kmh:.0f}",
                excess_str,
                f"{spd_d:.1f}",
                f"{limit_d:.1f}",
                f"+ {spd_d - limit_d:.1f}" if spd_d > limit_d else f"{spd_d - limit_d:.1f}",
            ])

        t_lim = Table(
            limit_rows,
            colWidths=[3.5 * cm, 2.2 * cm, 2.0 * cm, 2.0 * cm, 2.5 * cm, 2.5 * cm, 2.3 * cm],
        )
        t_lim.setStyle(_header_table_style())
        story.append(t_lim)
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            "Not: Durma mesafesi hesabı istatistiksel bir kıyaslama amacı taşır ve "
            "sürücünün gerçek tepki süresi ile yol koşullarına bağlı olarak değişebilir. "
            "Bu değer bilirkişi raporunda yardımcı bağlam olarak kullanılmalıdır.",
            S["Note"],
        ))
        story.append(Spacer(1, 0.5 * cm))

    # ── 4. Güven Seviyesi Kriterleri ──────────────────────────────────────────
    story.append(Paragraph("Güven Seviyesi Kriterleri", S["SectionTitle"]))

    crit_rows = [
        ["Seviye", "Kalibrasyon", "RMS", "Min. Kare", "CI/Hız", "Smooth/Hız"],
        [
            "Yüksek", "Saha Ölçümü",
            f"< {int(_HIGH_RMS_M * 100)} cm",
            f">= {_HIGH_FRAME}",
            f"< %{int(_REL_CI_HIGH * 100)}",
            f"< %{int(_REL_SMOOTH_LOW * 100)}",
        ],
        [
            "Orta", "Operatör/Saha",
            f"< {int(_MEDIUM_RMS_M * 100)} cm",
            f">= {_MEDIUM_FRAME}",
            f"< %{int(_REL_CI_LOW * 100)}",
            "-",
        ],
        [
            "Düşük", "Diğer/Std.",
            f">= {int(_MEDIUM_RMS_M * 100)} cm",
            f"< {_MEDIUM_FRAME}",
            f">= %{int(_REL_CI_LOW * 100)}",
            "-",
        ],
    ]
    t5 = Table(crit_rows, colWidths=[2.5 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 3 * cm])
    t5.setStyle(_header_table_style())
    story.append(t5)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"CI/Hız: güven aralığının hız tahminine oranı. Smooth/Hız: düzleştirilmiş "
        f"kalıntı oranı (yalnızca Yüksek seviyeyi engeller). "
        f"Düzlemsellik uyarısı varlığında güven seviyesi bir kademe düşürülür "
        f"(Yüksek → Orta, Orta → Düşük). "
        f"Eşikler: RMS_H={int(_HIGH_RMS_M*100)} cm / RMS_M={int(_MEDIUM_RMS_M*100)} cm, "
        f"CI_H={int(_REL_CI_HIGH*100)}% / CI_L={int(_REL_CI_LOW*100)}%.",
        S["Note"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    # ── 4b. Aks Genişliği Doğrulama ───────────────────────────────────────────
    if axle_checks:
        story.append(Paragraph("Aks Genişliği Çapraz Doğrulama", S["SectionTitle"]))
        story.append(Paragraph(
            "Aşağıdaki sonuçlar operatörün işaretlediği tekerlek piksel noktalarından "
            "hesaplanmış aks genişliğinin bilinen referans değeriyle karşılaştırılmasıdır. "
            "Bu değer güven seviyesi hesabına dahil edilmez; yalnızca destekleyici kanıt "
            "olarak sunulur.",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))
        axle_header = ["Track ID", "Ölçülen (m)", "Bilinen (m)", "Fark (%)", "Hesaplama Tarihi"]
        axle_rows = [axle_header]
        for ac in axle_checks:
            axle_rows.append([
                f"#{ac.get('track_id', '?')}",
                f"{ac.get('measured_m', 0):.3f}",
                f"{ac.get('known_m', 0):.3f}",
                f"%{ac.get('error_pct', 0):.1f}",
                ac.get("computed_at", "")[:19].replace("T", " "),
            ])
        t_axle = Table(
            axle_rows,
            colWidths=[2 * cm, 3 * cm, 3 * cm, 3 * cm, 5 * cm],
        )
        t_axle.setStyle(_header_table_style())
        story.append(t_axle)
        story.append(Spacer(1, 0.5 * cm))

    # ── 4c. Operatör-Tekerlek Hız Ölçümü ─────────────────────────────────────
    if wheel_speeds:
        story.append(Paragraph("Operatör-Tekerlek Hız Ölçümü (Birincil)", S["SectionTitle"]))
        story.append(Paragraph(
            "Aşağıdaki sonuçlar operatörün işaretlediği tekerlek-zemin temas noktalarından "
            "hesaplanmıştır. Her track için operatör en az 2 farklı karede aynı tekerin "
            "yere değdiği yeri işaretlemiştir; bu pikseller H ile dünya koordinatına "
            "çevrilerek doğrusal regresyon ile hız elde edilmiştir. "
            "Bu yöntem YOLO bbox paralaks hatasından bağımsızdır ve forensic birincil "
            "hız olarak kullanılmalıdır.",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))
        ws_header = [
            "Track ID", "Hız (km/h)", "CI ± (km/h)", "Güven", "İşaret Sayısı",
            "Residual (km/h)", "Hesaplama Tarihi",
        ]
        ws_rows = [ws_header]
        for ws in sorted(wheel_speeds, key=lambda w: w.get("track_id", 0)):
            ws_rows.append([
                f"#{ws.get('track_id', '?')}",
                f"{ws.get('value_kmh', 0):.1f}",
                f"± {ws.get('ci_kmh', 0):.1f}",
                _CONFIDENCE_TR.get(ws.get("confidence_level", ""), ws.get("confidence_level", "—")),
                str(ws.get("mark_count", "?")),
                f"{ws.get('residual_kmh', 0):.1f}",
                ws.get("computed_at", "")[:19].replace("T", " "),
            ])
        t_ws = Table(
            ws_rows,
            colWidths=[2 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 3.5 * cm],
        )
        t_ws.setStyle(_header_table_style())
        story.append(t_ws)
        if any(ws.get("warnings") for ws in wheel_speeds):
            for ws in wheel_speeds:
                for w in ws.get("warnings", []):
                    story.append(Spacer(1, 0.1 * cm))
                    story.append(Paragraph(
                        f"Track #{ws.get('track_id', '?')} uyarı: {w}", S["Note"]
                    ))
        story.append(Spacer(1, 0.5 * cm))

    # ── 4d. Tekerlek Hız Profili / Fren Analizi ───────────────────────────────
    if wheel_speed_profiles:
        story.append(Paragraph("Hız Profili — Fren / İvme Analizi", S["SectionTitle"]))
        story.append(Paragraph(
            "Aşağıdaki profil operatörün işaretlediği birden fazla tekerlek temas "
            "noktasından türetilmiştir. Kayan pencere yumuşatma ile her segment için "
            "hız ve güven aralığı hesaplanmış; merkezi sonlu fark ile ivme tahmini yapılmıştır. "
            "Ham ardışık çift hızları audit için korunmaktadır. "
            "Özet (birincil) hız T16 tek-değer yöntemiyle hesaplanır ve profil hızlarına "
            "göre önceliklidir.",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))

        for prof in sorted(wheel_speed_profiles, key=lambda p: p.get("track_id", 0)):
            track_label = f"Track #{prof.get('track_id', '?')}"
            story.append(Paragraph(track_label, S["Heading3"] if "Heading3" in S else S["Normal"]))

            summary_rows = [
                ["Özet Hız (km/h)", f"{prof.get('summary_value_kmh', 0):.1f}"],
                ["Güven Aralığı (km/h)", f"± {prof.get('summary_ci_kmh', 0):.1f}"],
                ["Güven Seviyesi", _CONFIDENCE_TR.get(
                    prof.get("summary_confidence_level", ""),
                    prof.get("summary_confidence_level", "—"),
                )],
                ["İşaret Sayısı", str(prof.get("summary_mark_count", "?"))],
                ["Yumuşatma Penceresi", str(prof.get("smoothing_window", "?"))],
                ["Hesaplama Tarihi", prof.get("computed_at", "")[:19].replace("T", " ")],
            ]
            t_sum = Table(summary_rows, colWidths=[5 * cm, 11 * cm])
            t_sum.setStyle(_kv_table_style())
            story.append(t_sum)
            story.append(Spacer(1, 0.2 * cm))

            pts = prof.get("points", [])
            if pts:
                try:
                    from src.speed.wheel_contact import WheelSpeedProfile, ProfilePoint, WheelSpeedResult
                    from src.output.overlay import profile_chart_png
                    profile_points = [
                        ProfilePoint(
                            t_s=p["t_s"],
                            speed_kmh=p["speed_kmh"],
                            ci_kmh=p["ci_kmh"],
                            accel_ms2=p.get("accel_ms2"),
                        )
                        for p in pts
                    ]
                    mock_summary = WheelSpeedResult(
                        value_kmh=prof.get("summary_value_kmh", 0),
                        ci_kmh=prof.get("summary_ci_kmh", 0),
                        confidence_level=prof.get("summary_confidence_level", "low"),
                        mark_count=prof.get("summary_mark_count", 0),
                        residual_kmh=prof.get("summary_residual_kmh", 0),
                    )
                    mock_profile = WheelSpeedProfile(
                        points=profile_points,
                        raw_pairwise_kmh=prof.get("raw_pairwise_kmh", []),
                        summary=mock_summary,
                        smoothing_window=prof.get("smoothing_window", 3),
                    )
                    png_bytes = profile_chart_png(mock_profile)
                    story.append(Image(io.BytesIO(png_bytes), width=14 * cm, height=5.4 * cm))
                    story.append(Spacer(1, 0.2 * cm))
                except Exception:
                    pass

            if pts:
                pt_header = ["t (s)", "Hız (km/h)", "CI ± (km/h)", "İvme (m/s²)"]
                pt_rows = [pt_header]
                for p in pts:
                    accel_str = f"{p['accel_ms2']:.2f}" if p.get("accel_ms2") is not None else "—"
                    pt_rows.append([
                        f"{p['t_s']:.2f}",
                        f"{p['speed_kmh']:.1f}",
                        f"± {p['ci_kmh']:.1f}",
                        accel_str,
                    ])
                t_pts = Table(pt_rows, colWidths=[3 * cm, 4 * cm, 4 * cm, 5 * cm])
                t_pts.setStyle(_header_table_style())
                story.append(t_pts)
                story.append(Spacer(1, 0.2 * cm))

            for w in prof.get("warnings", []):
                story.append(Paragraph(f"Uyarı: {w}", S["Note"]))

            story.append(Spacer(1, 0.4 * cm))

    # ── 5. Varsayımlar ve Sınırlamalar ────────────────────────────────────────
    story.append(Paragraph("Varsayımlar ve Sınırlamalar", S["SectionTitle"]))

    assumptions = [
        "Yol yüzeyi düzlem kabul edilmiştir (homografi ile perspektif dönüşümü uygulanmıştır).",
        "Kamera kayıt süresince sabit kalmıştır; titreme veya yeniden konumlandırma olmamıştır.",
        "Araç hızı, tekerlek-zemin temas noktası pikselinden hesaplanmıştır. "
        "Kütlemerkezi kullanılamaz (paralaks hatası).",
        f"FPS değeri video konteyner meta verisinden okunmuştur ({meta.fps_source}). "
        "Gerçek kayıt hızıyla uyumsuzluk olursa hız hesabı etkilenir.",
    ]

    if cal.confidence_layer in ("standard_assumption", "operator"):
        assumptions.append(
            "Kalibrasyon referans mesafeleri standart boyutlara dayalıdır "
            "(şerit genişliği ~3,5 m veya araç plakası 520 × 110 mm). "
            "Saha ölçümü yapılmamıştır; gerçek boyutlardan sapmalar hatayı artırabilir."
        )

    if cal.planarity_warning:
        assumptions.append(
            "UYARI — Düzlemsellik: Kalibrasyon artıkları ile derinlik arasında "
            "sistematik korelasyon saptanmıştır. Yol eğimli veya kabartılı olabilir."
        )

    assumptions += [
        "Araç tespiti ve takibi YOLO + ByteTrack algoritması ile gerçekleştirilmiştir. "
        "Kaçırılan veya yanlış eşlenen tespitler sonuçları etkileyebilir.",
        "Raporlanan güven aralıkları (CI) yalnızca hız serisinin istatistiksel "
        "yayılımını yansıtır; kalibrasyon belirsizliğini kapsamamaktadır.",
        "Bu rapor adli (forensic) kullanıma destek amaçlıdır. Sonuçların bağımsız "
        "uzman incelemesinden geçirilmesi önerilir.",
    ]

    for i, text in enumerate(assumptions, 1):
        story.append(Paragraph(f"{i}. {text}", S["Normal"]))
        story.append(Spacer(1, 0.15 * cm))

    return story


def generate_report(
    result: PipelineResult,
    out_path: str | Path,
    axle_checks: list[dict] | None = None,
    wheel_speeds: list[dict] | None = None,
    wheel_speed_profiles: list[dict] | None = None,
    speed_limit_kmh: float | None = None,
) -> None:
    """Adli raporu PDF olarak yaz (ReportLab).

    axle_checks: aks genişliği doğrulama sonuçları listesi.
    wheel_speeds: T16 operatör-tekerlek hız ölçümü sonuçları listesi (birincil).
    wheel_speed_profiles: T19 hız profili (fren/ivme) sonuçları listesi.
    speed_limit_kmh: Mahallin hız limiti (km/h). Verilirse aşım + durma mesafesi karşılaştırması eklenir.
    """
    out_path = Path(out_path)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN,
        topMargin=_MARGIN, bottomMargin=_MARGIN,
        title="Araç Hız Tespit Raporu",
    )
    doc.build(_build_story(
        result,
        axle_checks=axle_checks,
        wheel_speeds=wheel_speeds,
        wheel_speed_profiles=wheel_speed_profiles,
        speed_limit_kmh=speed_limit_kmh,
    ))
