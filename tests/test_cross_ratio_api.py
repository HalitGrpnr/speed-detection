"""T28 Faz 3 — H'siz takip işi + cross-ratio VP önizleme ve hız endpoint'leri."""
from __future__ import annotations

import json
import time
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.detection.models import Track, TrackPoint
from src.detection.video import read_video_meta
from tests.test_vp_sources import _synthetic_video

VP = np.array([640.0, 160.0])
N_FRAMES = 12
WB = 2.65


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    frames, boxes, vp = _synthetic_video(vp=tuple(VP), n=N_FRAMES)
    path = tmp_path_factory.mktemp("xr") / "xr.avi"
    h, w = frames[0].shape[:2]
    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25.0, (w, h))
    for f in frames:
        wr.write(f)
    wr.release()
    track = Track(track_id=7, vehicle_class="car", points=[
        TrackPoint(frame=i, t_s=i / 25.0, contact_pixel=((b[0] + b[2]) / 2, b[3]), bbox=tuple(b))
        for i, b in enumerate(boxes)
    ])
    return path, track


@pytest.fixture(scope="module")
def client(synthetic):
    from src.ui.app import app

    path, track = synthetic
    with TestClient(app) as c:
        with path.open("rb") as f:
            r = c.post("/api/video/upload", files={"file": ("xr.avi", f, "video/x-msvideo")})
        assert r.status_code == 200, r.text
        video_id = r.json()["video_id"]

        def fake_tracking(video_path, **kw):
            return [track], read_video_meta(video_path)

        with patch("src.ui.app.run_tracking", side_effect=fake_tracking):
            r = c.post("/api/track", json={"video_id": video_id})
            assert r.status_code == 202, r.text
            job_id = r.json()["job_id"]
            for _ in range(100):
                st = c.get(f"/api/job/{job_id}/status").json()
                if st["state"] in ("done", "error"):
                    break
                time.sleep(0.05)
        assert st["state"] == "done", st
        c._job_id = job_id
        yield c


def _lane_lines():
    # VP'den geçen üç çizgi (operatör işaretleri gibi)
    lines = []
    for x_bot in (150.0, 450.0, 1000.0):
        bot = np.array([x_bot, 700.0])
        mid = VP + 0.5 * (bot - VP)
        lines.append([mid.tolist(), bot.tolist()])
    return lines


def _marks_and_refs(speed_kmh=60.0, n=8):
    """VP'ye giden doğru üzerinde, 1/r modeline göre sabit hızla ilerleyen temas noktaları."""
    d = np.array([-0.35, 1.0])
    d /= np.linalg.norm(d)
    r1, r2 = 620.0, 575.0                       # arka / ön teker teması (VP'ye uzaklık)
    C = WB * r1 * r2 / (r1 - r2)
    v = speed_kmh / 3.6
    marks = []
    for k in range(n):
        x = v * k / 25.0                        # arka tekerin gerçek konumu (m)
        r = C / (x + C / r1)                    # X = C(1/r − 1/r1) tersi
        p = VP + d * r
        marks.append({"frame": k, "pixel": p.tolist()})
    return marks, (VP + d * r1).tolist(), (VP + d * r2).tolist()


def test_tracking_job_without_calibration(client):
    job_id = client._job_id
    tracks = client.get(f"/api/job/{job_id}/tracks").json()
    assert len(tracks) == 1 and tracks[0]["track_id"] == 7
    assert tracks[0]["point_count"] == N_FRAMES and len(tracks[0]["points"]) == N_FRAMES
    res = client.get(f"/api/job/{job_id}/results").json()
    assert res["vehicle_count"] == 1
    log = client.get(f"/api/job/{job_id}/session-log").json()
    events = [e["event"] for e in log]
    assert "tracking_started" in events and "tracking_run" in events
    started = next(e for e in log if e["event"] == "tracking_started")
    assert len(started["video_sha256"]) == 64


def test_vp_preview_lane_and_trajectory(client):
    r = client.post(f"/api/job/{client._job_id}/track/7/cross-ratio/vp",
                    json={"lane_lines": _lane_lines(), "use_trajectory": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert np.linalg.norm(np.array(body["lane"]["point"]) - VP) < 1e-3
    assert body["trajectory"] is not None, body["trajectory_error"]
    assert np.linalg.norm(np.array(body["trajectory"]["point"]) - VP) < 10.0
    assert body["agreement"]["status"] == "agree", body["agreement"]["message"]
    assert body["agreement"]["angle_deg"] < 2.0


def test_vp_preview_requires_two_lane_lines(client):
    r = client.post(f"/api/job/{client._job_id}/track/7/cross-ratio/vp",
                    json={"lane_lines": _lane_lines()[:1], "use_trajectory": False})
    assert r.status_code == 422


def test_cross_ratio_speed_end_to_end(client):
    marks, rear, front = _marks_and_refs(speed_kmh=60.0)
    req = {
        "lane_lines": _lane_lines(),
        "use_trajectory": False,
        "known_length": {"kind": "wheelbase", "length_m": WB, "point_a": rear,
                         "point_b": front, "sigma_m": 0.01, "frame": 0},
        "marks": marks,
    }
    r = client.post(f"/api/job/{client._job_id}/track/7/cross-ratio-speed", json=req)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["speed_kmh"] == pytest.approx(60.0, rel=0.01)
    assert body["ci_kmh"] > 0
    assert set(body["ci_components_kmh"]) == {"fit", "vp", "length"}
    assert body["confidence_level"] in ("high", "medium", "low")
    assert body["vp_used"]["source"] == "lane_manual"
    assert body["fps"] == pytest.approx(25.0)

    from src.ui.app import _job_out_dir
    rec = json.loads((_job_out_dir(client._job_id) / "cross_ratio_7.json").read_text())
    assert rec["method"] == "cross_ratio" and rec["inputs"]["marks"][0]["frame"] == 0
    log = client.get(f"/api/job/{client._job_id}/session-log").json()
    ev = [e for e in log if e["event"] == "cross_ratio_speed"][-1]
    assert ev["speed_kmh"] == body["speed_kmh"] and ev["vp_source"] == "lane_manual"


def test_cross_ratio_speed_with_trajectory_crosscheck(client):
    marks, rear, front = _marks_and_refs()
    req = {
        "lane_lines": _lane_lines(),
        "use_trajectory": True,
        "known_length": {"kind": "wheelbase", "length_m": WB, "point_a": rear, "point_b": front},
        "marks": marks,
    }
    body = client.post(f"/api/job/{client._job_id}/track/7/cross-ratio-speed", json=req).json()
    assert body["vp_alternative"]["source"] == "trajectory"
    assert body["agreement"] is not None
    codes = {g["code"] for g in body["gates"]}
    assert "length_sigma_default" in codes


def test_cross_ratio_speed_needs_vp_source(client):
    marks, rear, front = _marks_and_refs()
    req = {
        "use_trajectory": False,
        "known_length": {"kind": "wheelbase", "length_m": WB, "point_a": rear, "point_b": front},
        "marks": marks,
    }
    r = client.post(f"/api/job/{client._job_id}/track/7/cross-ratio-speed", json=req)
    assert r.status_code == 422
    assert "Perspektif referansı" in r.json()["detail"]


def test_cross_ratio_speed_needs_two_marks(client):
    marks, rear, front = _marks_and_refs()
    req = {
        "lane_lines": _lane_lines(), "use_trajectory": False,
        "known_length": {"kind": "wheelbase", "length_m": WB, "point_a": rear, "point_b": front},
        "marks": marks[:1],
    }
    assert client.post(f"/api/job/{client._job_id}/track/7/cross-ratio-speed", json=req).status_code == 422


def test_unknown_track_404(client):
    r = client.post(f"/api/job/{client._job_id}/track/999/cross-ratio/vp", json={"use_trajectory": False})
    assert r.status_code == 404
