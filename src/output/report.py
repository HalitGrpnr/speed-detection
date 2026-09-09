from __future__ import annotations

import io
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
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

# Bilirkişiye yönelik yüksek seviye yöntem anlatımı (PDF + audit metni ortak kaynak).
# Gövde metni konvansiyonuna uyarak ASCII-Türkçe (font/encoding güvenli).
_METHOD_SUMMARY = [
    "Sistem once videodaki yolu bir referans duzlemi olarak kalibre eder: operator, "
    "goruntude gercek dunya mesafesi bilinen noktalari (serit genisligi ~3.5 m, plaka "
    "520x110 mm gibi) isaretler. Bu eslesmelerden, goruntudeki pikseller ile yoldaki "
    "gercek metreler arasinda matematiksel bir donusum (homografi) kurulur; boylece "
    "ekrandaki her noktanin yolda kac metreye karsilik geldigi bilinir.",
    "Arac, kareler boyunca otomatik takip edilir; olcum icin aracin tekerlek-zemin temas "
    "noktasi kullanilir (kutle merkezi degil, cunku kamera acisi nedeniyle paralaks hatasi "
    "uretir). Bu nokta her karede gercek dunya koordinatina cevrilir; iki kare arasinda kat "
    "edilen metre, videonun kare hizi (FPS) ile birlestirilerek hiza cevrilir ve km/h "
    "cinsinden verilir.",
    "Hicbir hiz ciplak tek sayi olarak sunulmaz: her sonuc bir guven araligi "
    "(orn. 52 +/- 3 km/h) ve guven seviyesi tasir. Kalibrasyon kalitesi (hata payi) olculur "
    "ve operator onayindan gecer; tum adimlar ile dosya butunlugu (SHA-256) loglanir, boylece "
    "sonuc bagimsiz olarak dogrulanabilir.",
]

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
    point_count = len(cal.used_point_ids)
    texts = [
        "Araç Hız Tespit Raporu",
        "Yontem Ozeti — Hiz Nasil Hesaplanir",
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


def _build_story(result: PipelineResult, axle_checks: list[dict] | None = None) -> list:
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
    if result.video_sha256:
        meta_rows.append(["Video SHA-256", result.video_sha256])
    t = Table(meta_rows, colWidths=[5 * cm, 11 * cm])
    t.setStyle(_kv_table_style())
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # 1b. Yöntem Özeti (bilirkişi için yüksek seviye anlatım)
    story.append(Paragraph("Yontem Ozeti — Hiz Nasil Hesaplanir", S["SectionTitle"]))
    for para in _METHOD_SUMMARY:
        story.append(Paragraph(para, S["Normal"]))
        story.append(Spacer(1, 0.15 * cm))
    story.append(Spacer(1, 0.35 * cm))

    # 2. Kalibrasyon
    story.append(Paragraph("Kalibrasyon", S["SectionTitle"]))

    rms_m = cal.reprojection_rms_m
    if cal.planarity_warning:
        planarity_str = "UYARI - yuzey egimi/duzlemsellik sorunu tespit edildi"
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
        "Yeterli (>= 6 nokta)"
        if redundancy_ok
        else f"UYARI — yalnizca {point_count} nokta. 4-nokta cozumunde RMS ≈ 0 anlamsizdir."
    )

    cal_rows = [
        ["Guven Katmani", _LAYER_TR.get(cal.confidence_layer, cal.confidence_layer)],
        ["Re-projeksiyon RMS", f"{rms_m * 100:.1f} cm  ({rms_m:.4f} m)"],
        ["LOO Capraz Dogrulama RMS", loo_str],
        ["Kalibrasyon Redundancy", redundancy_str],
        ["Duzlemsellik Uyarisi", planarity_str],
        ["Kullanilan Nokta Sayisi", str(point_count)],
    ]
    t2 = Table(cal_rows, colWidths=[5 * cm, 11 * cm])
    t2.setStyle(_kv_table_style())
    story.append(t2)

    if cal.holdout_rows:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Held-out Dogrulama Noktalari", S["Heading3"]))
        ho_header = ["Nokta ID", "Olculen (m)", "Tahmin (m)", "Hata (m)"]
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

    # 2c. Kus Bakisi Gorunum (DTP karsilastirmasi §5) — ikincil, ureilemezse atlanir.
    if result.plan_view_png:
        story.append(Paragraph("Kus Bakisi Gorunum (Plan View)", S["SectionTitle"]))
        story.append(Paragraph(
            "Asagidaki gorsel, kalibre edilen yol duzleminin tepeden bir projeksiyonudur "
            "— gercek bir havadan fotograf degildir. Yalnizca kontrol noktalarinin kapsadigi "
            "bolge guvenilir olcek tasir; ince gri cizgiler 1 metre araliklidir.",
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
        [
            "Yuksek", "Saha Olcumu",
            f"< {int(_HIGH_RMS_M * 100)} cm",
            f">= {_HIGH_FRAME}",
            f"< %{int(_REL_CI_HIGH * 100)}",
            f"< %{int(_REL_SMOOTH_LOW * 100)}",
        ],
        [
            "Orta", "Operator/Saha",
            f"< {int(_MEDIUM_RMS_M * 100)} cm",
            f">= {_MEDIUM_FRAME}",
            f"< %{int(_REL_CI_LOW * 100)}",
            "-",
        ],
        [
            "Dusuk", "Diger/Std.",
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
        f"CI/Hiz: guven araliginin hiz tahminine orani. Smooth/Hiz: duzlestirilmis "
        f"kalinti orani (yalnizca Yuksek seviyeyi engeller). "
        f"Duzlemsellik uyarisi varliginda guven seviyesi bir kademe dusurulur "
        f"(Yuksek -> Orta, Orta -> Dusuk). "
        f"Esikler: RMS_H={int(_HIGH_RMS_M*100)}cm / RMS_M={int(_MEDIUM_RMS_M*100)}cm, "
        f"CI_H={int(_REL_CI_HIGH*100)}% / CI_L={int(_REL_CI_LOW*100)}%.",
        S["Note"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    # 4b. Aks Genişliği Doğrulama (isteğe bağlı — rapor regenerate edilince eklenir)
    if axle_checks:
        story.append(Paragraph("Aks Genisligi Capraz Dogrulama", S["SectionTitle"]))
        story.append(Paragraph(
            "Asagidaki sonuclar operatorun isgaret ettigi tekerlek piksel noktalarindan "
            "hesaplanmis aks genisliginin bilinen referans degeriyle karsilastirilmasidir. "
            "Bu deger guven seviyesi hesabina dahil edilmez; yalnizca destekleyici kanit "
            "olarak sunulur.",
            S["Normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))
        axle_header = ["Track ID", "Olculen (m)", "Bilinen (m)", "Fark (%)", "Hesaplama Tarihi"]
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
    axle_checks: list[dict] | None = None,
) -> None:
    """Adli raporu PDF olarak yaz (ReportLab).

    axle_checks: aks genişliği doğrulama sonuçları listesi (her eleman bir track'e ait dict).
    Verilirse rapora ayrı bir bölüm olarak eklenir.
    """
    out_path = Path(out_path)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=_MARGIN, rightMargin=_MARGIN,
        topMargin=_MARGIN, bottomMargin=_MARGIN,
        title="Arac Hiz Tespit Raporu",
    )
    doc.build(_build_story(result, axle_checks=axle_checks))
