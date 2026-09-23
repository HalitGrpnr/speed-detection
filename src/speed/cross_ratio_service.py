"""T28 Faz 3 — Cross-ratio ölçüm servisi: VP seçimi + belirsizlik yayılımı + kalite kapıları.

Çekirdek (`cross_ratio.py`) ve VP kaynakları (`vp_sources.py`) saf matematiktir; bu modül onları
tek bir adli ölçüme bağlar ve operatöre "ne oldu, neden, ne yapmalı" diyen kapılar üretir.
FastAPI'ye bağımlı değildir (endpoint ince bir sarmalayıcıdır) → doğrudan test edilir.

Güven aralığı (~%95) bileşenlerin karesel toplamıdır:
  - fit     : konum–zaman doğrusunun eğim belirsizliği (işaretleme gürültüsü + düzlük)
  - vp      : VP kovaryansından sabit tohumlu Monte Carlo (tekrarlanabilir) → hız dağılımı
  - length  : bilinen uzunluğun belirsizliği (oransal)
  - vp_disagreement : iki bağımsız VP kaynağı istatistiksel olarak ayrışırsa, alternatif VP ile
              hesaplanan hızla fark (sistematik; model varsayımı — ör. lens bükülmesi, şeridin
              araç yoluna paralel olmaması — ihlal edildiğinde CI'nin gerçeği kaçırmaması için)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

import numpy as np

from src.calibration.vp_sources import VanishingAgreement, VanishingEstimate, compare_vanishing
from src.speed.cross_ratio import CrossRatioSpeedResult, cross_ratio_speed, line_scale_from_vp

Severity = Literal["info", "warn", "error"]

# Eşikler (T10 GPS doğrulama setine kadar geçici — DECISIONS.md)
FAR_SENSITIVITY_M_PER_PX = 0.20   # 1 px işaret hatası > 20 cm → kare "uzak"
OFFSET_WARN_PX = 4.0              # ölçüm doğrusundan dik sapma
VP_MC_INVALID_WARN = 0.05         # VP örneklerinin > %5'i geçersiz → VP güvenilmez
VP_REL_SIGMA_WARN = 0.25          # VP 1σ belirsizliği / VP–iz uzaklığı
VP_DISAGREE_LOW = 0.10            # ayrışan iki VP'nin hızları > %10 farklı → düşük güven
HIGH_REL_CI = 0.05
MEDIUM_REL_CI = 0.15
STANDARD_FPS = (23.976, 24.0, 25.0, 29.97, 30.0, 48.0, 50.0, 59.94, 60.0, 120.0)
DEFAULT_LENGTH_SIGMA_M = {"wheelbase": 0.05, "scene": 0.02}


@dataclass(frozen=True)
class KnownLength:
    kind: Literal["wheelbase", "scene"]
    length_m: float
    point_a: tuple[float, float]     # dingil: arka tekerlek teması · olay yeri: 1. işaret
    point_b: tuple[float, float]     # dingil: ön tekerlek teması  · olay yeri: 2. işaret
    sigma_m: float | None = None     # None → tür varsayılanı
    frame: int | None = None         # dingil işaretlendiği kare (audit)

    @property
    def sigma_used(self) -> float:
        return DEFAULT_LENGTH_SIGMA_M[self.kind] if self.sigma_m is None else self.sigma_m


@dataclass(frozen=True)
class ContactMark:
    frame: float
    pixel: tuple[float, float]
    source: str = "manual"           # "manual" | "operator-confirmed" | "auto"


@dataclass(frozen=True)
class QualityGate:
    code: str
    severity: Severity
    message: str                     # ne oldu + neden önemli
    action: str = ""                 # operatör ne yapmalı


@dataclass
class CrossRatioMeasurement:
    speed_kmh: float
    ci_kmh: float
    confidence_level: str
    ci_components_kmh: dict[str, float]
    core: CrossRatioSpeedResult
    vp_used: VanishingEstimate
    vp_alternative: VanishingEstimate | None
    agreement: VanishingAgreement | None
    speed_alternative_kmh: float | None  # alternatif VP ile hız (şeffaflık / çapraz kontrol)
    vp_mc_samples: int
    vp_mc_invalid_fraction: float
    known_length: KnownLength
    length_sigma_m: float
    fps: float
    fps_source: str
    marks: list[ContactMark]
    mark_sensitivity_m_per_px: list[float]
    gates: list[QualityGate] = field(default_factory=list)


def select_vp(
    lane: VanishingEstimate | None,
    trajectory: VanishingEstimate | None,
    prefer: Literal["lane", "trajectory"] = "lane",
) -> tuple[VanishingEstimate, VanishingEstimate | None]:
    """(kullanılacak VP, çapraz kontrol için diğeri)."""
    if lane is None and trajectory is None:
        raise ValueError("Perspektif referansı yok — şerit çizgisi işaretleyin veya araç izini kullanın.")
    if lane is None:
        return trajectory, None  # type: ignore[return-value]
    if trajectory is None:
        return lane, None
    return (lane, trajectory) if prefer == "lane" else (trajectory, lane)


def _fps_gate(fps: float, fps_source: str) -> QualityGate | None:
    if fps_source == "operator_override":
        return QualityGate(
            "fps_override", "info",
            f"FPS operatör tarafından {fps:g} olarak girildi (video başlığı yerine).",
        )
    nearest = min(STANDARD_FPS, key=lambda f: abs(f - fps))
    if abs(nearest - fps) / nearest > 0.005:
        return QualityGate(
            "fps_suspicious", "warn",
            f"Video başlığındaki FPS ({fps:.3f}) standart değerlerin hiçbirine uymuyor — değişken kare "
            "hızı veya hatalı başlık olabilir. Hız doğrudan FPS ile orantılıdır.",
            "Kaynak kaydediciden gerçek kare hızını doğrulayın; gerekirse FPS'i elle girin.",
        )
    return None


def _vp_mc(
    vp: VanishingEstimate,
    kl: KnownLength,
    frames: np.ndarray,
    pts: np.ndarray,
    fps: float,
    pixel_sigma: float,
    n: int,
    seed: int,
) -> tuple[np.ndarray, int]:
    """VP'yi kovaryansından örnekleyip hızı yeniden hesapla. (geçerli hızlar, geçersiz sayısı)."""
    if vp.point is None or vp.covariance is None or n <= 0:
        return np.array([]), 0
    rng = np.random.default_rng(seed)
    samples = rng.multivariate_normal(np.asarray(vp.point), np.asarray(vp.covariance), size=n)
    speeds, invalid = [], 0
    for s in samples:
        try:
            sc = line_scale_from_vp(tuple(s), kl.point_a, kl.point_b, kl.length_m, line_points=pts)
            speeds.append(cross_ratio_speed(sc, frames, pts, fps, pixel_sigma=pixel_sigma).speed_kmh)
        except ValueError:
            invalid += 1
    return np.asarray(speeds), invalid


def measure_cross_ratio(
    vp_used: VanishingEstimate,
    known_length: KnownLength,
    marks: Sequence[ContactMark],
    fps: float,
    fps_source: str = "container",
    vp_alternative: VanishingEstimate | None = None,
    pixel_sigma: float = 1.0,
    mc_samples: int = 400,
    seed: int = 0,
) -> CrossRatioMeasurement:
    """Tek araç, düz bir doğru boyunca hız — CI bileşenleri ve kalite kapılarıyla."""
    marks = sorted(marks, key=lambda m: m.frame)
    if len(marks) < 2:
        raise ValueError("Hız için en az 2 karede tekerlek teması işaretlenmelidir.")
    frames = np.array([m.frame for m in marks], dtype=np.float64)
    pts = np.array([m.pixel for m in marks], dtype=np.float64)
    kl = known_length
    length_sigma = kl.sigma_used

    scale = line_scale_from_vp(vp_used.point, kl.point_a, kl.point_b, kl.length_m, line_points=pts)
    core = cross_ratio_speed(scale, frames, pts, fps, pixel_sigma=pixel_sigma)  # yalnızca fit CI
    speed = core.speed_kmh

    mc_speeds, mc_invalid = _vp_mc(vp_used, kl, frames, pts, fps, pixel_sigma, mc_samples, seed)
    if len(mc_speeds) >= 10:
        lo, hi = np.percentile(mc_speeds, [2.5, 97.5])
        ci_vp = float((hi - lo) / 2)
    else:
        ci_vp = 0.0
    ci_len = 1.96 * length_sigma / kl.length_m * speed
    ci_fit = core.ci_kmh

    # Alternatif VP ile hız: her zaman raporlanır; ayrışma varsa fark CI'ye sistematik bileşen olur
    agreement = None
    speed_alt = None
    ci_disagree = 0.0
    if vp_alternative is not None:
        agreement = compare_vanishing(vp_used, vp_alternative, at=pts.mean(axis=0))
        try:
            sc_alt = line_scale_from_vp(vp_alternative.point, kl.point_a, kl.point_b, kl.length_m, line_points=pts)
            speed_alt = cross_ratio_speed(sc_alt, frames, pts, fps, pixel_sigma=pixel_sigma).speed_kmh
        except ValueError:
            speed_alt = None
        if agreement.status == "disagree" and speed_alt is not None:
            ci_disagree = abs(speed - speed_alt)

    ci_total = float(np.sqrt(ci_fit**2 + ci_vp**2 + ci_len**2 + ci_disagree**2))
    mc_total = mc_samples if vp_used.point is not None and vp_used.covariance is not None else 0
    invalid_frac = mc_invalid / mc_total if mc_total else 0.0

    sens = scale.position_sensitivity_m_per_px(pts)
    gates: list[QualityGate] = []

    # ── İşaretler ──
    if len(marks) < 3:
        gates.append(QualityGate(
            "too_few_marks", "warn",
            "Yalnızca 2 kare işaretli — ölçümün tutarlılığı kontrol edilemiyor.",
            "Aracın düz gittiği aralıkta en az 4–6 karede tekerlek temasını işaretleyin.",
        ))
    auto = [m for m in marks if m.source == "auto"]
    if auto:
        gates.append(QualityGate(
            "auto_marks_unconfirmed", "warn",
            f"{len(auto)} işaret otomatik öneri ve operatör onayı almamış.",
            "Her öneriyi karede kontrol edip onaylayın veya düzeltin.",
        ))
    if core.max_offset_px > OFFSET_WARN_PX:
        gates.append(QualityGate(
            "not_straight", "warn",
            f"Tekerlek temas noktaları ortak doğrudan {core.max_offset_px:.1f} px sapıyor — araç bu "
            "aralıkta düz gitmiyor olabilir ya da işaretler farklı tekerleklerde.",
            "Aracın düz gittiği daha kısa bir kare aralığı seçin; hep aynı tekerleği işaretleyin.",
        ))
    far = [int(m.frame) for m, s in zip(marks, sens) if s > FAR_SENSITIVITY_M_PER_PX]
    if far:
        gates.append(QualityGate(
            "far_marks", "warn",
            f"{len(far)} karede araç çok uzakta (1 px işaret hatası > "
            f"{FAR_SENSITIVITY_M_PER_PX * 100:.0f} cm): kareler {far[:8]}{'…' if len(far) > 8 else ''}.",
            "Aracın kameraya yakın olduğu kareleri tercih edin; uzak kareler ölçüme az katkı verir.",
        ))

    # ── Bilinen uzunluk ──
    ref_off = max(scale.ref_offsets_px)
    if ref_off > OFFSET_WARN_PX:
        if kl.kind == "scene":
            gates.append(QualityGate(
                "ref_off_line", "warn",
                f"Olay yeri mesafesi işaretleri aracın izinden {ref_off:.1f} px uzakta. Yöntem mesafenin "
                "aracın geçtiği doğru üzerinde olmasını gerektirir; farklı şeritteki bir mesafe ölçeği bozar.",
                "Mesafeyi aracın tekerleklerinin geçtiği çizgi üzerinde işaretleyin.",
            ))
        else:
            gates.append(QualityGate(
                "ref_off_line", "warn",
                f"Dingil işaretleri (ön/arka teker) tekerlek izinden {ref_off:.1f} px uzakta.",
                "Ön ve arka tekerleği aracın AYNI tarafında, zemine değdiği noktada işaretleyin.",
            ))
    if known_length.sigma_m is None:
        gates.append(QualityGate(
            "length_sigma_default", "info",
            f"Bilinen uzunluk belirsizliği varsayılan ±{length_sigma * 100:.0f} cm (1σ) alındı.",
            "Araç modeli biliniyorsa gerçek dingil mesafesini ve toleransını girin.",
        ))

    # ── Perspektif referansı ──
    for w in vp_used.warnings:
        gates.append(QualityGate("vp_note", "info", w))
    if vp_used.point is None:
        gates.append(QualityGate(
            "vp_infinite", "warn",
            "Perspektif referansı sonsuzda (çizgiler görüntüde paralel) — referans belirsizliği güven "
            "aralığına katılamadı.",
            "Mümkünse daha uzun şerit çizgileri işaretleyin veya araç izi ile çapraz kontrol yapın.",
        ))
    else:
        if invalid_frac > VP_MC_INVALID_WARN:
            gates.append(QualityGate(
                "vp_unreliable", "error",
                f"Perspektif referansının belirsizliği çok büyük: örneklerin %{invalid_frac * 100:.0f}'i "
                "geçersiz ölçüm üretti.",
                "Şerit çizgilerini daha uzun ve dikkatli işaretleyin veya daha düz bir aralık seçin.",
            ))
        sig = vp_used.sigma_px
        if sig is not None:
            dist = float(np.min(np.linalg.norm(pts - np.asarray(vp_used.point), axis=1)))
            if sig[0] / dist > VP_REL_SIGMA_WARN:
                gates.append(QualityGate(
                    "vp_uncertain", "warn",
                    f"Perspektif referansı ±{sig[0]:.0f} px belirsiz (araca uzaklığın "
                    f"%{sig[0] / dist * 100:.0f}'i).",
                    "Ek şerit çizgisi işaretleyin veya araç izi ile birlikte kullanın.",
                ))

    if agreement is not None:
        sev: Severity = {"agree": "info", "disagree": "warn", "indeterminate": "info"}[agreement.status]
        gates.append(QualityGate(
            f"vp_{agreement.status}", sev, agreement.message,
            "" if agreement.status != "disagree" else
            "Şerit çizgilerinin aracın gittiği yönle paralel olduğunu ve aracın düz gittiğini kontrol edin.",
        ))
        if agreement.status == "disagree" and speed_alt is not None:
            rel_d = abs(speed - speed_alt) / speed if speed > 0 else np.inf
            gates.append(QualityGate(
                "vp_disagreement_in_ci", "error" if rel_d > VP_DISAGREE_LOW else "warn",
                f"Diğer perspektif referansıyla hız {speed_alt:.1f} km/h (fark %{rel_d * 100:.0f}). Bu fark güven "
                "aralığına sistematik belirsizlik olarak eklendi.",
                "Farkın kaynağını giderin: şerit çizgilerini aracın yakınında ve uzun işaretleyin; görüntü kenarındaki "
                "(lens bükülmesi olabilecek) çizgilerden kaçının; daha düz bir aralık seçin.",
            ))

    fg = _fps_gate(fps, fps_source)
    if fg:
        gates.append(fg)

    # ── Güven seviyesi ──
    rel = ci_total / speed if speed > 0 else np.inf
    if rel <= HIGH_REL_CI and len(marks) >= 4:
        level = "high"
    elif rel <= MEDIUM_REL_CI:
        level = "medium"
    else:
        level = "low"
    severities = {g.severity for g in gates}
    if "error" in severities:
        level = "low"
    elif "warn" in severities and level == "high":
        level = "medium"

    return CrossRatioMeasurement(
        speed_kmh=round(speed, 1),
        ci_kmh=round(ci_total, 1),
        confidence_level=level,
        ci_components_kmh={
            "fit": round(ci_fit, 2), "vp": round(ci_vp, 2), "length": round(ci_len, 2),
            **({"vp_disagreement": round(ci_disagree, 2)} if ci_disagree > 0 else {}),
        },
        core=core,
        vp_used=vp_used,
        vp_alternative=vp_alternative,
        agreement=agreement,
        speed_alternative_kmh=None if speed_alt is None else round(speed_alt, 1),
        vp_mc_samples=mc_total,
        vp_mc_invalid_fraction=round(invalid_frac, 4),
        known_length=kl,
        length_sigma_m=length_sigma,
        fps=fps,
        fps_source=fps_source,
        marks=list(marks),
        mark_sensitivity_m_per_px=[round(float(s), 4) for s in sens],
        gates=gates,
    )
