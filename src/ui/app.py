from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import tempfile
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from src.autoref.proposer import AutoProposer
from src.calibration.homography import compute_homography, pixel_to_world
from src.calibration.io import load_calibration, save_calibration
from src.calibration.metrics import holdout_validation, loo_rms
from src.calibration.models import CalibrationError, CalibrationResult, ControlPoint
from src.calibration.planview import compute_plan_view
from src.detection.models import load_tracks, save_tracks
from src.detection.video import read_video_meta
from src.output.pipeline import run_pipeline
from src.output.serialization import write_result_data, read_result_data
from src.reliability.axle_check import (
    axle_cross_check,
    axle_points_to_control_points,
    suggest_axle_frame,
)

from .job_store import JobState, JobStore
from .schemas import (
    AutoRefRequest,
    AxleCheckRequest,
    AxleCheckResponse,
    AxleSuggestFrameResponse,
    AxleStepRequest,
    AxleStepResponse,
    AxleStepOut,
    CalibrateRequest,
    CalibrateResponse,
    JobResultOut,
    JobStatusOut,
    PipelineRequest,
    PlanViewRequest,
    ProposedPointOut,
    RecalibrateRequest,
    RejectedPointOut,
    SpeedEstimateOut,
    VideoMetaOut,
)

import sys as _sys
if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
    # PyInstaller --onedir: statik dosyalar _MEIPASS altındaki yola yerleştirilir
    _UI_DIR = Path(_sys._MEIPASS) / "src" / "ui"
else:
    _UI_DIR = Path(__file__).parent
# React/Vite SPA build çıktısı (M8). Tek UI budur; eski vanilla UI Step 8'de kaldırıldı.
_WEB_DIR = _UI_DIR / "web"
_MODEL_MAP = {"nano": "yolo11n.pt", "small": "yolo11s.pt", "medium": "yolo11m.pt"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB

_tmp_dir: Path | None = None
_video_store: dict[str, Path] = {}
_job_store = JobStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tmp_dir
    _tmp_dir = Path(tempfile.mkdtemp(prefix="speed_det_"))
    yield
    shutil.rmtree(_tmp_dir, ignore_errors=True)


app = FastAPI(title="Araç Hız Tespit Sistemi", lifespan=lifespan)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_video_path(video_id: str) -> Path:
    path = _video_store.get(video_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Video bulunamadı.")
    return path


def _read_frame(video_path: Path, frame_n: int) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="Video açılamadı.")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_n < 0 or frame_n >= total:
        cap.release()
        raise HTTPException(
            status_code=404, detail=f"Kare {frame_n} bulunamadı (toplam: {total})."
        )
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_n)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise HTTPException(status_code=500, detail="Kare okunamadı.")
    return frame


def _frame_to_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise HTTPException(status_code=500, detail="Kare JPEG'e kodlanamadı.")
    return buf.tobytes()


# ── Video endpoints ───────────────────────────────────────────────────────────

@app.post("/api/video/upload", response_model=VideoMetaOut)
async def upload_video(file: UploadFile = File(...)) -> VideoMetaOut:
    if _tmp_dir is None:
        raise HTTPException(status_code=503, detail="Sunucu hazır değil.")

    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Dosya boyutu 10 GB limitini aşıyor.")

    video_id = str(uuid.uuid4())
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest = _tmp_dir / f"{video_id}{suffix}"
    dest.write_bytes(data)

    try:
        meta = read_video_meta(dest)
    except IOError as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(e))

    sha = _sha256(dest)
    _video_store[video_id] = dest

    return VideoMetaOut(
        video_id=video_id,
        fps=meta.fps,
        fps_source=meta.fps_source,
        width=meta.width,
        height=meta.height,
        frame_count=meta.frame_count,
        sha256=sha,
    )


@app.get("/api/video/{video_id}/meta", response_model=VideoMetaOut)
async def video_meta(video_id: str) -> VideoMetaOut:
    path = _get_video_path(video_id)
    meta = read_video_meta(path)
    sha = _sha256(path)
    return VideoMetaOut(
        video_id=video_id,
        fps=meta.fps,
        fps_source=meta.fps_source,
        width=meta.width,
        height=meta.height,
        frame_count=meta.frame_count,
        sha256=sha,
    )


@app.get("/api/video/{video_id}/frame/{frame_n}")
async def get_frame(video_id: str, frame_n: int) -> Response:
    path = _get_video_path(video_id)
    frame = _read_frame(path, frame_n)
    return Response(content=_frame_to_jpeg(frame), media_type="image/jpeg")


@app.get("/api/video/{video_id}/thumbnail")
async def get_thumbnail(video_id: str) -> Response:
    path = _get_video_path(video_id)
    meta = read_video_meta(path)
    frame = _read_frame(path, meta.frame_count // 2)
    h, w = frame.shape[:2]
    scale = min(320 / w, 180 / h)
    thumb = cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))))
    return Response(content=_frame_to_jpeg(thumb, quality=75), media_type="image/jpeg")


# ── Calibration endpoints ─────────────────────────────────────────────────────

@app.post("/api/calibrate", response_model=CalibrateResponse)
async def calibrate(req: CalibrateRequest) -> CalibrateResponse:
    _get_video_path(req.video_id)

    if len(req.control_points) < 4:
        raise HTTPException(
            status_code=422,
            detail=(
                f"En az 4 kontrol noktası gereklidir "
                f"(gönderilen: {len(req.control_points)})."
            ),
        )

    points = [
        ControlPoint(
            id=cp.id,
            pixel=cp.pixel,
            world_m=cp.world_m,
            source=cp.source,
            held_out=cp.held_out,
        )
        for cp in req.control_points
    ]

    try:
        result = compute_homography(points)
    except CalibrationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Leave-one-out doğrulama (≥5 nokta varsa otomatik)
    loo_rms_val = loo_rms(points)

    # Operatör held-out noktaları varsa holdout doğrulama
    holdout_ids = [p.id for p in points if p.held_out]
    h_rows: list[dict] = []
    if holdout_ids:
        try:
            h_rows = holdout_validation(points, holdout_ids)
        except CalibrationError:
            pass  # eğitim noktaları yetersizse sessizce atla

    # RANSAC_THRESHOLD ile eşleşmesi için homography.py'deki 0.5 m değerini kullan
    _RANSAC_THRESHOLD_M = 0.5
    excl_ids = set(result.excluded_point_ids)
    rejected: list[RejectedPointOut] = []
    for p in points:
        if p.id in excl_ids:
            pred = pixel_to_world(result.homography, p.pixel)
            err_m = float(np.hypot(pred[0] - p.world_m[0], pred[1] - p.world_m[1]))
            rejected.append(RejectedPointOut(
                id=p.id,
                error_cm=round(err_m * 100, 1),
                threshold_cm=round(_RANSAC_THRESHOLD_M * 100, 1),
            ))

    return CalibrateResponse(
        rms_m=result.reprojection_rms_m,
        inlier_count=len(result.used_point_ids),
        confidence_layer=result.confidence_layer,
        homography=result.homography.tolist(),
        planarity_warning=result.planarity_warning,
        point_count=len(points),
        loo_rms_m=loo_rms_val,
        holdout_rows=h_rows,
        rejected_points=rejected,
    )


@app.post("/api/video/{video_id}/plan-view")
async def plan_view(video_id: str, req: PlanViewRequest) -> Response:
    """Kuş bakışı (kalibre edilmiş yol düzleminin projeksiyonu) — Adım 4 canlı önizleme.

    Gerçek bir havadan fotoğraf değildir; yalnızca kontrol noktalarının kapladığı
    dünya bölgesi güvenilirdir (bkz. docs/dtp-expert-karsilastirma.md §5).
    """
    path = _get_video_path(video_id)
    frame = _read_frame(path, req.frame_n)

    if len(req.control_points) < 4:
        raise HTTPException(
            status_code=422,
            detail=f"En az 4 kontrol noktası gereklidir (gönderilen: {len(req.control_points)}).",
        )

    points = [
        ControlPoint(
            id=cp.id, pixel=cp.pixel, world_m=cp.world_m, source=cp.source, held_out=cp.held_out
        )
        for cp in req.control_points
    ]

    # Sunucu-tarafı H yeniden hesaplanır — /api/calibrate ile aynı ilke (R4).
    try:
        cal_result = compute_homography(points)
    except CalibrationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    img = compute_plan_view(frame, cal_result.homography, points)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(status_code=500, detail="Görsel PNG'ye kodlanamadı.")
    return Response(content=buf.tobytes(), media_type="image/png")


# ── AutoRef endpoint ──────────────────────────────────────────────────────────

@app.post("/api/video/{video_id}/autoref", response_model=list[ProposedPointOut])
async def autoref(video_id: str, req: AutoRefRequest) -> list[ProposedPointOut]:
    path = _get_video_path(video_id)
    frame = _read_frame(path, req.frame_n)

    proposer = AutoProposer(
        lane_width_m=req.lane_width_m,
        dash_length_m=req.dash_length_m,
        d_near_m=req.d_near_m,
    )
    proposals = proposer.propose(frame)

    return [
        ProposedPointOut(
            pixel=p.pixel,
            world_m=p.world_m,
            detection_confidence=p.detection_confidence,
            description=p.description,
        )
        for p in proposals
    ]


# ── Pipeline endpoints ────────────────────────────────────────────────────────

def _finalize_job(job: JobState, result, out_video: Path, out_report: Path, out_dir: Path) -> None:
    """PipelineResult'tan JobState'i doldur — pipeline ve recalibrate ortak kapanışı."""
    track_class = {t.track_id: t.vehicle_class for t in result.tracks}

    estimates = [
        {
            "track_id": est.track_id,
            "vehicle_class": track_class.get(est.track_id, "vehicle"),
            "speed_kmh": round(est.value_kmh, 1),
            "ci_kmh": round(est.ci_kmh, 1),
            "confidence_level": est.confidence_level,
            "frame_count": est.track_quality.frame_count,
        }
        for est in result.speed_estimates
    ]

    # Track bbox verisi kalıcı diske yazılır — aks doğrulaması/recalibrate gibi rapor-sonrası
    # işlemler için pipeline'ı yeniden çalıştırmadan erişilebilsin diye.
    save_tracks(out_dir / "tracks.json", result.tracks)

    # Tam PipelineResult kalıcı JSON'a yazılır — rapor yeniden üretimi (T7) için gerekli.
    job.result_data_path = write_result_data(result, out_dir)

    job.overlay_path = out_video if out_video.exists() else None
    job.report_path = out_report if out_report.exists() else None
    job.result_json = {"vehicle_count": len(estimates), "estimates": estimates}
    job.frame_step = result.frame_step
    job.model_name_used = result.model_name
    job.video_path = result.video_path
    job.progress_pct = 100.0
    job.state = "done"


def _run_pipeline_thread(
    job: JobState,
    video_path: Path,
    cal_json_path: Path,
    out_dir: Path,
    frame_step: int,
    model_name: str,
    fps: float | None = None,
    fps_source: str | None = None,
    video_sha256: str = "",
) -> None:
    try:
        job.state = "running"
        job.progress_pct = 5.0

        out_video = out_dir / "overlay.mp4"
        out_report = out_dir / "report.pdf"

        def _progress(pct: float) -> None:
            job.progress_pct = pct

        result = run_pipeline(
            video_path=video_path,
            calibration_path=cal_json_path,
            out_video=out_video,
            out_report=out_report,
            frame_step=frame_step,
            model_name=model_name,
            progress=True,
            on_progress=_progress,
            fps=fps,
            fps_source=fps_source,
            video_sha256=video_sha256,
        )
        _finalize_job(job, result, out_video, out_report, out_dir)

    except Exception as exc:
        import traceback as _tb
        full = _tb.format_exc()
        print(f"\n[PIPELINE HATA] job={job.job_id}\n{full}", flush=True)
        job.state = "error"
        job.error = f"{type(exc).__name__}: {exc}"


def _run_recalibrate_thread(
    job: JobState,
    video_path: Path,
    cal_json_path: Path,
    out_dir: Path,
    tracks: list,
    video_sha256: str,
    original_frame_step: int = 1,
    original_model_name: str = "",
) -> None:
    """Mevcut track'lerle (tespit atlanır) yeni kalibrasyona göre hız + çıktıları yeniden üret."""
    try:
        job.state = "running"
        job.progress_pct = 20.0

        out_video = out_dir / "overlay.mp4"
        out_report = out_dir / "report.pdf"

        display_model = (
            f"{original_model_name} — hızlar yeniden hesaplandı, tespit tekrarlanmadı"
            if original_model_name
            else "(tekrar tespit edilmedi — yalnızca kalibrasyon güncellendi)"
        )

        result = run_pipeline(
            video_path=video_path,
            calibration_path=cal_json_path,
            out_video=out_video,
            out_report=out_report,
            frame_step=original_frame_step,
            progress=True,
            video_sha256=video_sha256,
            precomputed_tracks=tracks,
            model_name=display_model,
        )
        job.progress_pct = 90.0
        _finalize_job(job, result, out_video, out_report, out_dir)

    except Exception as exc:
        import traceback as _tb
        full = _tb.format_exc()
        print(f"\n[RECALIBRATE HATA] job={job.job_id}\n{full}", flush=True)
        job.state = "error"
        job.error = f"{type(exc).__name__}: {exc}"


@app.post("/api/pipeline", status_code=202)
async def start_pipeline(req: PipelineRequest) -> dict:
    if _tmp_dir is None:
        raise HTTPException(status_code=503, detail="Sunucu hazır değil.")

    video_path = _get_video_path(req.video_id)

    job_id = str(uuid.uuid4())
    job = _job_store.create(job_id)

    out_dir = _tmp_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    cal_json_path = out_dir / "calibration.json"

    control_points = [
        ControlPoint(
            id=cp.id,
            pixel=cp.pixel,
            world_m=cp.world_m,
            source=cp.source,
            held_out=cp.held_out,
        )
        for cp in req.control_points
    ]

    # Sunucu-tarafı H yeniden hesaplama — istemcinin gönderdiği H kabul edilmez
    try:
        cal_result = compute_homography(control_points)
    except CalibrationError as e:
        raise HTTPException(status_code=422, detail=f"Sunucu-tarafı kalibrasyon başarısız: {e}")

    # Audit: istemci H ile sunucu H karşılaştır; farklıysa logla
    client_H = np.array(req.calibration.homography, dtype=np.float64)
    max_diff = float(np.max(np.abs(client_H - cal_result.homography)))
    if max_diff > 1e-4:
        print(
            f"[AUDIT UYARI] job={job_id}: istemci H sunucu H'den farklı "
            f"(max_diff={max_diff:.2e}). Sunucu H kullanılıyor.",
            flush=True,
        )

    # LOO ve holdout yeniden üret (adli tutarlılık)
    loo_rms_val = loo_rms(control_points)
    holdout_ids = [p.id for p in control_points if p.held_out]
    h_rows: list[dict] = []
    if holdout_ids:
        try:
            h_rows = holdout_validation(control_points, holdout_ids)
        except CalibrationError:
            pass
    cal_result.holdout_rows = h_rows
    cal_result.loo_rms_m = loo_rms_val

    meta = read_video_meta(video_path)
    fps = req.fps_override if req.fps_override is not None else meta.fps
    fps_source = "operator_override" if req.fps_override is not None else "container"

    save_calibration(
        cal_json_path,
        cal_result,
        control_points,
        fps=fps,
        fps_source=fps_source,
        frame_n=req.frame_n,
    )

    video_sha256 = _sha256(video_path)
    model_name = _MODEL_MAP.get(req.model_size, "yolo11n.pt")

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(job, video_path, cal_json_path, out_dir, req.frame_step, model_name,
              fps, fps_source, video_sha256),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@app.get("/api/job/{job_id}/status", response_model=JobStatusOut)
async def job_status(job_id: str) -> JobStatusOut:
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    return JobStatusOut(
        job_id=job.job_id,
        state=job.state,
        progress_pct=job.progress_pct,
        eta_s=job.eta_s,
        error=job.error,
    )


@app.get("/api/job/{job_id}/report")
async def download_report(job_id: str) -> FileResponse:
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.state != "done" or job.report_path is None:
        raise HTTPException(status_code=404, detail="Rapor henüz hazır değil.")
    return FileResponse(
        path=job.report_path, filename="rapor.pdf", media_type="application/pdf"
    )


@app.post("/api/job/{job_id}/report/regenerate", status_code=200)
async def regenerate_report(job_id: str) -> dict:
    """result_data.json + axle_check_*.json ile raporu yeniden üretir.

    Orijinal report.pdf korunur — yeni rapor report_v2.pdf olarak yazılır.
    Forensic kural: eski rapor değişmez; aks doğrulaması yeni versiyona eklenir.
    """
    job = _get_done_job(job_id)
    out_dir = _job_out_dir(job_id)

    if not (out_dir / "result_data.json").exists():
        raise HTTPException(
            status_code=404,
            detail="result_data.json bulunamadı — bu analiz yeni format desteklemiyor.",
        )

    try:
        result = read_result_data(out_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analiz verisi okunamadı: {exc}")

    # Tüm axle_check_*.json dosyalarını topla
    axle_checks = []
    for p in sorted(out_dir.glob("axle_check_*.json")):
        try:
            data = json.loads(p.read_text())
            track_id_str = p.stem.replace("axle_check_", "")
            data["track_id"] = int(track_id_str) if track_id_str.isdigit() else track_id_str
            axle_checks.append(data)
        except Exception:
            pass

    report_v2_path = out_dir / "report_v2.pdf"
    try:
        from src.output.report import generate_report
        generate_report(result, report_v2_path, axle_checks=axle_checks or None)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Rapor üretilemedi: {exc}")

    job.report_v2_path = report_v2_path
    return {"status": "ok", "axle_check_count": len(axle_checks)}


@app.get("/api/job/{job_id}/report/v2")
async def download_report_v2(job_id: str) -> FileResponse:
    """Aks doğrulaması eklenmiş güncellenmiş raporu indir."""
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.report_v2_path is None or not job.report_v2_path.exists():
        raise HTTPException(status_code=404, detail="Güncellenmiş rapor henüz oluşturulmadı.")
    return FileResponse(
        path=job.report_v2_path, filename="rapor_v2.pdf", media_type="application/pdf"
    )


@app.get("/api/job/{job_id}/overlay")
async def stream_overlay(job_id: str) -> FileResponse:
    """Tarayıcı içi oynatma — inline Content-Disposition."""
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.state != "done" or job.overlay_path is None:
        raise HTTPException(status_code=404, detail="Overlay video henüz hazır değil.")
    return FileResponse(
        path=job.overlay_path,
        media_type="video/mp4",
        content_disposition_type="inline",
    )


@app.get("/api/job/{job_id}/overlay/download")
async def download_overlay(job_id: str) -> FileResponse:
    """İndirme — attachment Content-Disposition."""
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.state != "done" or job.overlay_path is None:
        raise HTTPException(status_code=404, detail="Overlay video henüz hazır değil.")
    return FileResponse(
        path=job.overlay_path,
        filename="overlay.mp4",
        media_type="video/mp4",
        content_disposition_type="attachment",
    )


@app.get("/api/job/{job_id}/results", response_model=JobResultOut)
async def job_results(job_id: str) -> JobResultOut:
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.state != "done" or job.result_json is None:
        raise HTTPException(status_code=404, detail="Sonuçlar henüz hazır değil.")
    estimates = [SpeedEstimateOut(**e) for e in job.result_json["estimates"]]
    return JobResultOut(
        job_id=job_id,
        vehicle_count=job.result_json["vehicle_count"],
        estimates=estimates,
    )


@app.get("/api/job/{job_id}/plan-view")
async def job_plan_view(job_id: str) -> Response:
    """Tamamlanmış analiz için kuş bakışı — homografi doğrulama amaçlı."""
    job = _get_done_job(job_id)
    if not job.video_path:
        raise HTTPException(status_code=404, detail="Video yolu kaydedilmemiş.")
    cal_json_path = _job_out_dir(job_id) / "calibration.json"
    if not cal_json_path.exists():
        raise HTTPException(status_code=404, detail="Kalibrasyon verisi bulunamadı.")
    cal_result, points, _ = load_calibration(cal_json_path)
    cal_frame_n = json.loads(cal_json_path.read_text()).get("frame_n") or 0
    frame = _read_frame(Path(job.video_path), cal_frame_n)
    img = compute_plan_view(frame, cal_result.homography, points)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(status_code=500, detail="Görsel PNG'ye kodlanamadı.")
    return Response(content=buf.tobytes(), media_type="image/png")


# ── Aks genişliği çapraz doğrulama (M9) ─────────────────────────────────────────
# Not: Yalnızca destekleyici kanıt üretir — bkz. tasks/M9.md, DECISIONS.md.
# confidence_level hesabına dahil edilmez; PDF raporu değiştirmez (bkz. bilinen sınırlama).

def _job_out_dir(job_id: str) -> Path:
    if _tmp_dir is None:
        raise HTTPException(status_code=503, detail="Sunucu hazır değil.")
    return _tmp_dir / job_id


def _get_done_job(job_id: str) -> JobState:
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.state != "done":
        raise HTTPException(status_code=404, detail="İş henüz tamamlanmadı.")
    return job


def _load_all_tracks_or_404(job_id: str) -> list:
    tracks_path = _job_out_dir(job_id) / "tracks.json"
    if not tracks_path.exists():
        raise HTTPException(status_code=404, detail="Track verisi bulunamadı.")
    return load_tracks(tracks_path)


def _get_track_or_404(job_id: str, track_id: int):
    for t in _load_all_tracks_or_404(job_id):
        if t.track_id == track_id:
            return t
    raise HTTPException(status_code=404, detail=f"Track {track_id} bulunamadı.")


@app.get(
    "/api/job/{job_id}/track/{track_id}/axle-suggest-frame",
    response_model=AxleSuggestFrameResponse,
)
async def axle_suggest_frame(job_id: str, track_id: int) -> AxleSuggestFrameResponse:
    _get_done_job(job_id)
    track = _get_track_or_404(job_id, track_id)
    return AxleSuggestFrameResponse(frame_n=suggest_axle_frame(track))


@app.post(
    "/api/job/{job_id}/track/{track_id}/axle-check",
    response_model=AxleCheckResponse,
)
async def axle_check(job_id: str, track_id: int, req: AxleCheckRequest) -> AxleCheckResponse:
    _get_done_job(job_id)
    _get_track_or_404(job_id, track_id)  # track var mı doğrula

    cal_json_path = _job_out_dir(job_id) / "calibration.json"
    if not cal_json_path.exists():
        raise HTTPException(status_code=404, detail="Kalibrasyon verisi bulunamadı.")
    _, control_points, _ = load_calibration(cal_json_path)

    # Sunucu-tarafı H yeniden hesaplanır — /api/pipeline ile aynı ilke (R4).
    try:
        cal_result = compute_homography(control_points)
    except CalibrationError as e:
        raise HTTPException(status_code=422, detail=f"Kalibrasyon yeniden hesaplanamadı: {e}")

    result = axle_cross_check(
        cal_result.homography, req.pixel_left, req.pixel_right, req.known_width_m
    )

    # Audit kaydı: kalıcı, zaman damgalı — rapora otomatik eklenmez (bilinen sınırlama,
    # bkz. PROGRESS.md), ama denetim izinde saklanır.
    audit = {
        **result,
        "pixel_left": list(req.pixel_left),
        "pixel_right": list(req.pixel_right),
        "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (_job_out_dir(job_id) / f"axle_check_{track_id}.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2)
    )

    return AxleCheckResponse(**result)


@app.post(
    "/api/job/{job_id}/track/{track_id}/axle-step",
    response_model=AxleStepResponse,
)
async def axle_step(job_id: str, track_id: int, req: AxleStepRequest) -> AxleStepResponse:
    """Dingil adımlama hız tahmini (T8).

    Operatörün işaretlediği ön/arka teker piksel konumu + dingil mesafesinden yola çıkar;
    track contact_pixel'lerini H üzerinden dünya uzayında izleyerek adım zamanlarını bulur.
    H-tabanlı hızla bağımsız çapraz doğrulama üretir — confidence_level hesabına dahil edilmez.
    """
    from src.speed.axle_stepping import AxleStepper

    _get_done_job(job_id)
    track = _get_track_or_404(job_id, track_id)

    if not track.points:
        raise HTTPException(status_code=422, detail="Bu track'te hiç nokta yok.")

    cal_json_path = _job_out_dir(job_id) / "calibration.json"
    if not cal_json_path.exists():
        raise HTTPException(status_code=404, detail="Kalibrasyon verisi bulunamadı.")
    _, control_points, (fps, _) = load_calibration(cal_json_path)

    try:
        cal_result = compute_homography(control_points)
    except CalibrationError as e:
        raise HTTPException(status_code=422, detail=f"Kalibrasyon yeniden hesaplanamadı: {e}")

    H = cal_result.homography

    try:
        stepper = AxleStepper(
            H=H,
            front_pixel=req.front_pixel,
            rear_pixel=req.rear_pixel,
            wheelbase_m=req.wheelbase_m,
            fps=fps,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Track noktalarını frame_n'den itibaren işle
    for tp in track.points:
        if tp.frame >= req.frame_n:
            stepper.feed(tp.frame, tp.contact_pixel)

    r = stepper.result()
    return AxleStepResponse(
        speed_kmh=round(r.speed_kmh, 2) if r.speed_kmh is not None else None,
        ci_kmh=round(r.ci_kmh, 2) if r.ci_kmh is not None else None,
        step_count=r.step_count,
        steps=[AxleStepOut(frame=s.frame, distance_m=s.distance_m) for s in r.steps],
        interrupted=r.interrupted,
        interrupt_reason=r.interrupt_reason,
        initial_distance_m=round(r.initial_distance_m, 4),
    )


@app.post("/api/job/{job_id}/recalibrate", status_code=202)
async def recalibrate(job_id: str, req: RecalibrateRequest) -> dict:
    """Aks doğrulamasını kalibrasyona ekleyip mevcut track'lerle (tespit tekrarlanmadan)
    yeni bir job olarak hızlıca yeniden analiz eder. Eski job/rapor değişmeden kalır —
    forensic bütünlük için her analiz sonucu kendi kalibrasyonuyla sabittir."""
    if _tmp_dir is None:
        raise HTTPException(status_code=503, detail="Sunucu hazır değil.")

    old_job = _get_done_job(job_id)
    tracks = _load_all_tracks_or_404(job_id)
    video_path = _get_video_path(req.video_id)

    old_cal_path = _job_out_dir(job_id) / "calibration.json"
    if not old_cal_path.exists():
        raise HTTPException(status_code=404, detail="Kalibrasyon verisi bulunamadı.")
    _, _, (cal_fps, cal_fps_source) = load_calibration(old_cal_path)
    cal_frame_n = json.loads(old_cal_path.read_text()).get("frame_n")

    base_points = [
        ControlPoint(
            id=cp.id, pixel=cp.pixel, world_m=cp.world_m, source=cp.source, held_out=cp.held_out
        )
        for cp in req.control_points
    ]
    try:
        base_result = compute_homography(base_points)
    except CalibrationError as e:
        raise HTTPException(status_code=422, detail=f"Mevcut kalibrasyon geçersiz: {e}")

    try:
        cp_left, cp_right = axle_points_to_control_points(
            base_result.homography,
            req.pixel_left,
            req.pixel_right,
            req.known_width_m,
            id_prefix=f"axle_track{req.track_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    new_points = base_points + [cp_left, cp_right]
    try:
        new_cal_result = compute_homography(new_points)
    except CalibrationError as e:
        raise HTTPException(
            status_code=422, detail=f"Aks noktaları eklenince kalibrasyon başarısız: {e}"
        )

    new_job_id = str(uuid.uuid4())
    new_job = _job_store.create(new_job_id)
    new_out_dir = _tmp_dir / new_job_id
    new_out_dir.mkdir(parents=True, exist_ok=True)
    new_cal_path = new_out_dir / "calibration.json"
    save_calibration(new_cal_path, new_cal_result, new_points, fps=cal_fps, fps_source=cal_fps_source, frame_n=cal_frame_n)

    video_sha256 = _sha256(video_path)
    thread = threading.Thread(
        target=_run_recalibrate_thread,
        args=(new_job, video_path, new_cal_path, new_out_dir, tracks, video_sha256,
              old_job.frame_step or 1, old_job.model_name_used or ""),
        daemon=True,
    )
    thread.start()

    return {"job_id": new_job_id, "source_job_id": old_job.job_id}


# ── Static files ──────────────────────────────────────────────────────────────
# Not: Bu mount dosyanın SONUNDA kalmalı. "/" mount'u açgözlüdür; yukarıda
# tanımlı /api/* rotaları daha önce kaydedildiği için onlar öncelik kazanır.

# React/Vite SPA. Build edilmişse "/"'te servis edilir; aksi halde (build öncesi)
# API yine ayağa kalkar ama "/" açıklayıcı bir 503 döner.
if (_WEB_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
else:
    @app.get("/", response_class=HTMLResponse)
    async def _spa_not_built() -> HTMLResponse:
        return HTMLResponse(
            "<!doctype html><meta charset='utf-8'>"
            "<title>Araç Hız Tespit Sistemi</title>"
            "<p>Arayüz henüz derlenmedi. <code>cd frontend &amp;&amp; npm run build</code> çalıştırın.</p>",
            status_code=503,
        )
