from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from .models import PipelineResult

_MARGIN = 2 * cm

_CONFIDENCE_TR = {"high": "Yüksek", "medium": "Orta", "low": "Düşük"}
_LAYER_TR = {
    "standard_assumption": "Standart Varsayım",
    "operator": "Operatör (Elle Kalibrasyon)",
    "site_measurement": "Saha Ölçümü",
}


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(
        "SectionTitle", parent=s["Heading2"],
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a1a6e"),
    ))
    s.add(ParagraphStyle(
        "Note", parent=s["Normal"],
        fontSize=8, textColor=colors.gray, spaceAfter=4,
    ))
    return s


def _kv_table_style() -> TableStyle:
    return TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
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
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
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


def collect_report_texts(result: PipelineResult) -> list[str]:
    """Raporda yer alacak tüm metin bloklarını döndür (test ve audit için)."""
    meta = result.video_meta
    cal = result.calibration_result
    texts = [
        "Araç Hız Tespit Raporu",
        "Kalibrasyon",
        "Hız Sonuçları",
        "Varsayımlar ve Sınırlamalar",
        _LAYER_TR.get(cal.confidence_layer, cal.confidence_layer),
        f"{cal.reprojection_rms_m * 100:.1f} cm",
        "UYARI" if cal.planarity_warning else "Yok",
    ]
    for est in result.speed_estimates:
        texts.append(f"{est.value_kmh:.1f}")
        texts.append(f"±{est.ci_kmh:.1f}")
        texts.append(_CONFIDENCE_TR[est.confidence_level])
        if est.track_quality.frame_count < 5:
            texts.append("yetersiz")
    return texts


def _build_story(result: PipelineResult) -> list:
    S = _styles()
    meta = result.video_meta
    cal = result.calibration_result
    video_name = os.path.basename(result.video_path)
    dur_s = meta.frame_count / meta.fps if meta.fps > 0 else 0.0
    story = []

    # 1. Başlık
    story.append(Paragraph("Araç Hız Tespit Raporu", S["Title"]))
    story.append(Spacer(1, 0.3 * cm))

    meta_rows = [
        ["Rapor Tarihi", result.processed_at],
        ["Video Dosyası", video_name],
        ["Çözünürlük", f"{meta.width} x {meta.height} piksel"],
        ["FPS", f"{meta.fps:.3f} ({meta.fps_source})"],
        ["Toplam Kare", str(meta.frame_count)],
        ["Video Suresi", f"{dur_s:.2f} sn"],
        ["Isleme Adimi", f"frame_step = {result.frame_step}"],
        ["Model", result.model_name],
    ]
    t = Table(meta_rows, colWidths=[5 * cm, 11 * cm])
    t.setStyle(_kv_table_style())
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # 2. Kalibrasyon
    story.append(Paragraph("Kalibrasyon", S["SectionTitle"]))

    rms_m = cal.reprojection_rms_m
    planarity_str = (
        "UYARI - yuzey egimi/duzlemsellik sorunu tespit edildi"
        if cal.planarity_warning else "Yok"
    )

    cal_rows = [
        ["Guven Katmani", _LAYER_TR.get(cal.confidence_layer, cal.confidence_layer)],
        ["Re-projeksiyon RMS", f"{rms_m * 100:.1f} cm  ({rms_m:.4f} m)"],
        ["Duzlemsellik Uyarisi", planarity_str],
        ["Kullanilan Nokta Sayisi", str(len(cal.used_point_ids))],
    ]
    t2 = Table(cal_rows, colWidths=[5 * cm, 11 * cm])
    t2.setStyle(_kv_table_style())
    story.append(t2)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Kontrol Noktalari", S["Heading3"]))
    cp_header = ["ID", "Piksel (u, v)", "Dunya (X m, Y m)", "Kaynak", "Hold-out"]
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

    # 3. Hız Sonuçları
    story.append(Paragraph("Hiz Sonuclari", S["SectionTitle"]))

    speed_header = [
        "Track ID", "Arac Tipi", "Hiz (km/h)", "CI (km/h)",
        "Guven", "Kare Sayisi", "Okluzon",
    ]
    speed_rows = [speed_header]
    low_frame_ids = []

    for est in sorted(result.speed_estimates, key=lambda e: e.track_id):
        frames = est.track_quality.frame_count
        row = [
            f"#{est.track_id}",
            _class_for_track(est.track_id, result),
            f"{est.value_kmh:.1f}",
            f"{est.ci_kmh:.1f}",
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
            f"Not: Track(ler) {ids_str} yetersiz kare sayisina sahip (< 5). "
            "Bu sonuclar guvenilmez olabilir.",
            S["Note"],
        ))
    story.append(Spacer(1, 0.5 * cm))

    # 4. Güven Seviyesi Kriterleri
    story.append(Paragraph("Guven Seviyesi Kriterleri", S["SectionTitle"]))

    crit_rows = [
        ["Seviye", "Kalibrasyon", "RMS", "Min. Kare", "CI/Hiz", "Smooth/Hiz"],
        ["Yuksek", "Saha Olcumu", "< 5 cm", ">= 30", "< %10", "< %40"],
        ["Orta",   "Operator/Saha", "< 20 cm", ">= 15", "< %25", "-"],
        ["Dusuk",  "Diger/Std.", ">= 20 cm", "< 15", ">= %25", "-"],
    ]
    t5 = Table(crit_rows, colWidths=[2.5 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 3 * cm])
    t5.setStyle(_header_table_style())
    story.append(t5)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "CI/Hiz: guven araliginin hiz tahminine orani. Smooth/Hiz: duzlestirilmis "
        "kalinti orani (yalnizca Yuksek seviyeyi engeller). "
        "Duzlemsellik uyarisi varliginda guven seviyesi bir kademe dusuruLur "
        "(Yuksek -> Orta, Orta -> Dusuk).",
        S["Note"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    # 5. Varsayımlar
    story.append(Paragraph("Varsayimlar ve Sinirlamalar", S["SectionTitle"]))

    assumptions = [
        "Yol yuzeyi duzlem kabul edilmistir (homografi ile perspektif donusumu uygulanmistir).",
        "Kamera kaydi suresince sabit kalmistir; titreme veya yeniden konumlandirma olmamistir.",
        "Arac hizi, bounding box alt-orta pikselinden (tekerlek-zemin temasi) hesaplanmistir. "
        "Bbox merkezi kullanilamaz (paralaks hatasi).",
        f"FPS degeri video konteyner meta verisinden okunmustur ({meta.fps_source}). "
        "Gercek kayit hiziyla uyumsuzluk olursa hiz hesabi etkilenir.",
    ]

    if cal.confidence_layer in ("standard_assumption", "operator"):
        assumptions.append(
            "Kalibrasyon referans mesafeleri standart boyutlara dayalidir "
            "(serit genisligi ~3.5 m veya arac plakasi 520x110 mm). "
            "Saha olcumu yapilmamistir; gercek boyutlardan sapmalar hatay1 artirabilir."
        )

    if cal.planarity_warning:
        assumptions.append(
            "UYARI - Duzlemsellik: Kalibrasyon artiklari ile derinlik arasinda "
            "sistematik korelasyon saptanmistir. Yol egimli/kabartili olabilir."
        )

    assumptions += [
        "Arac tespiti ve takibi YOLO + ByteTrack algoritmasi ile gerceklestirilmistir. "
        "Kacirilan veya yanlis eslesen tespitler sonuclari etkileyebilir.",
        "Raporlanan guven araliklari (CI) yalnizca hiz serisinin istatistiksel "
        "yayilimini yansitir; kalibrasyon belirsizligini kapsamamaktadir.",
        "Bu rapor adli (forensic) kullanima destek amaclIdir. Sonuclarin bagimsiz "
        "uzman incelemesinden gecIrilmesi onerilir.",
    ]

    for i, text in enumerate(assumptions, 1):
        story.append(Paragraph(f"{i}. {text}", S["Normal"]))
        story.append(Spacer(1, 0.15 * cm))

    return story


def generate_report(
    result: PipelineResult,
    out_path: str | Path,
) -> None:
    """Adli raporu PDF olarak yaz (ReportLab)."""
    out_path = Path(out_path)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN,
        topMargin=_MARGIN, bottomMargin=_MARGIN,
        title="Arac Hiz Tespit Raporu",
    )
    doc.build(_build_story(result))
