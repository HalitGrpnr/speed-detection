from __future__ import annotations

import hashlib
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
from src.calibration.homography import compute_homography
from src.calibration.io import save_calibration
from src.calibration.models import CalibrationError, CalibrationResult, ControlPoint
from src.detection.video import read_video_meta
from src.output.pipeline import run_pipeline

from .job_store import JobState, JobStore
from .schemas import (
    AutoRefRequest,
    CalibrateRequest,
    CalibrateResponse,
    JobResultOut,
    JobStatusOut,
    PipelineRequest,
    ProposedPointOut,
    SpeedEstimateOut,
    VideoMetaOut,
)

_STATIC_DIR = Path(__file__).parent / "static"
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

    return CalibrateResponse(
        rms_m=result.reprojection_rms_m,
        inlier_count=len(result.used_point_ids),
        confidence_layer=result.confidence_layer,
        homography=result.homography.tolist(),
        planarity_warning=result.planarity_warning,
    )


# ── AutoRef endpoint ──────────────────────────────────────────────────────────

@app.post("/api/video/{video_id}/autoref", response_model=list[ProposedPointOut])
async def autoref(video_id: str, req: AutoRefRequest) -> list[ProposedPointOut]:
    path = _get_video_path(video_id)
    frame = _read_frame(path, req.frame_n)

    proposer = AutoProposer(
        lane_width_m=req.lane_width_m,
        dash_length_m=req.dash_length_m,
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

def _run_pipeline_thread(
    job: JobState,
    video_path: Path,
    cal_json_path: Path,
    out_dir: Path,
    frame_step: int,
    model_name: str,
) -> None:
    try:
        job.state = "running"
        job.progress_pct = 5.0

        out_video = out_dir / "overlay.mp4"
        out_report = out_dir / "report.pdf"

        result = run_pipeline(
            video_path=video_path,
            calibration_path=cal_json_path,
            out_video=out_video,
            out_report=out_report,
            frame_step=frame_step,
            model_name=model_name,
            progress=False,
        )

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

        job.overlay_path = out_video if out_video.exists() else None
        job.report_path = out_report if out_report.exists() else None
        job.result_json = {"vehicle_count": len(estimates), "estimates": estimates}
        job.progress_pct = 100.0
        job.state = "done"

    except Exception as exc:
        job.state = "error"
        job.error = str(exc)


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

    H = np.array(req.calibration.homography, dtype=np.float64)
    cal_result = CalibrationResult(
        homography=H,
        used_point_ids=[cp.id for cp in req.control_points if not cp.held_out],
        excluded_point_ids=[],
        reprojection_rms_m=req.calibration.rms_m,
        confidence_layer=req.calibration.confidence_layer,
        planarity_warning=req.calibration.planarity_warning,
    )
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

    meta = read_video_meta(video_path)
    fps = req.fps_override if req.fps_override is not None else meta.fps
    fps_source = "operator_override" if req.fps_override is not None else "container"

    save_calibration(
        cal_json_path,
        cal_result,
        control_points,
        fps=fps,
        fps_source=fps_source,
    )

    model_name = _MODEL_MAP.get(req.model_size, "yolo11n.pt")

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(job, video_path, cal_json_path, out_dir, req.frame_step, model_name),
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


@app.get("/api/job/{job_id}/overlay")
async def download_overlay(job_id: str) -> FileResponse:
    job = _job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="İş bulunamadı.")
    if job.state != "done" or job.overlay_path is None:
        raise HTTPException(status_code=404, detail="Overlay video henüz hazır değil.")
    return FileResponse(
        path=job.overlay_path, filename="overlay.mp4", media_type="video/mp4"
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


# ── Static files ──────────────────────────────────────────────────────────────

@app.get("/")
async def index() -> HTMLResponse:
    return HTMLResponse((_STATIC_DIR / "index.html").read_text(encoding="utf-8"))


app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
