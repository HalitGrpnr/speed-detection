"""Kabul testleri — M7 FastAPI uç noktaları."""
from __future__ import annotations

import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


# ── Test video yardımcısı ─────────────────────────────────────────────────────

def _make_test_video(path: Path, width: int = 320, height: int = 240,
                     fps: float = 25.0, frames: int = 30) -> None:
    """Minimal test videosu oluştur (sentetik, 30 kare)."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    rng = np.random.default_rng(42)
    for _ in range(frames):
        frame = (rng.random((height, width, 3)) * 255).astype(np.uint8)
        writer.write(frame)
    writer.release()


@pytest.fixture(scope='module')
def tmp_video(tmp_path_factory):
    """Paylaşımlı test videosu."""
    d = tmp_path_factory.mktemp('video')
    p = d / 'test.mp4'
    _make_test_video(p)
    return p


@pytest.fixture(scope='module')
def client(tmp_video):
    """FastAPI TestClient — video önceden yüklü."""
    # Modülü import etmeden önce çevre hazır olsun
    from src.ui.app import app, _video_store
    import tempfile
    from pathlib import Path as _Path

    with TestClient(app) as c:
        # Uygulama başlangıcında _tmp_dir set edildi; video_store'a elle ekle
        from src.ui import app as ui_app
        # Upload endpoint üzerinden yükle
        with tmp_video.open('rb') as f:
            resp = c.post('/api/video/upload', files={'file': ('test.mp4', f, 'video/mp4')})
        assert resp.status_code == 200, resp.text
        c._video_id = resp.json()['video_id']
        c._video_meta = resp.json()
        yield c


# ── 4 non-collinear kontrol noktası (birim testlerden alınan H kullanılır) ───

def _valid_points():
    """4 non-collinear kontrol noktası."""
    return [
        {'id': 'cp1', 'pixel': [100.0, 400.0], 'world_m': [0.0, 0.0],  'source': 'operator'},
        {'id': 'cp2', 'pixel': [220.0, 400.0], 'world_m': [3.5, 0.0],  'source': 'operator'},
        {'id': 'cp3', 'pixel': [240.0, 300.0], 'world_m': [3.5, 5.0],  'source': 'operator'},
        {'id': 'cp4', 'pixel': [110.0, 300.0], 'world_m': [0.0, 5.0],  'source': 'operator'},
    ]


# ── Test 1: Video meta ────────────────────────────────────────────────────────

def test_upload_returns_valid_meta(client):
    meta = client._video_meta
    assert meta['fps'] > 0
    assert meta['width'] == 320
    assert meta['height'] == 240
    assert meta['frame_count'] == 30
    assert len(meta['sha256']) == 64


# ── Test 2: Kare döndürme ─────────────────────────────────────────────────────

def test_get_frame_returns_jpeg(client):
    vid = client._video_id
    r = client.get(f'/api/video/{vid}/frame/0')
    assert r.status_code == 200
    assert r.headers['content-type'] == 'image/jpeg'
    assert len(r.content) > 0


def test_get_frame_mid(client):
    vid = client._video_id
    r = client.get(f'/api/video/{vid}/frame/15')
    assert r.status_code == 200


# ── Test 3: Geçersiz kare numarası ───────────────────────────────────────────

def test_invalid_frame_returns_404(client):
    vid = client._video_id
    r = client.get(f'/api/video/{vid}/frame/9999')
    assert r.status_code == 404


def test_negative_frame_returns_404(client):
    vid = client._video_id
    r = client.get(f'/api/video/{vid}/frame/-1')
    assert r.status_code == 404


# ── Test 4: Kalibrasyon — 4 geçerli nokta ────────────────────────────────────

def test_calibrate_valid_points(client):
    vid = client._video_id
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    assert r.status_code == 200
    data = r.json()
    assert data['rms_m'] > 0
    assert data['inlier_count'] > 0
    assert data['confidence_layer'] == 'operator'
    assert len(data['homography']) == 3
    assert len(data['homography'][0]) == 3
    assert isinstance(data['planarity_warning'], bool)


# ── Test 5: Kalibrasyon — 3 nokta yetersiz ───────────────────────────────────

def test_calibrate_too_few_points_returns_422(client):
    vid = client._video_id
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()[:3]
    })
    assert r.status_code == 422


# ── Test 6: AutoRef uç noktası ────────────────────────────────────────────────

def test_autoref_returns_list(client):
    vid = client._video_id
    r = client.post(f'/api/video/{vid}/autoref', json={
        'frame_n': 0, 'lane_width_m': 3.5, 'dash_length_m': 3.0
    })
    assert r.status_code == 200
    assert isinstance(r.json(), list)  # boş olabilir (sentetik kare), ama liste olmalı


# ── Test 7: Pipeline başlatma — job_id döner ─────────────────────────────────

def test_pipeline_start_returns_job_id(client):
    vid = client._video_id
    # Önce kalibrasyon al
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    # Pipeline'ı mock ile başlat (gerçek YOLO/tracking çalıştırma)
    with patch('src.ui.app._run_pipeline_thread') as mock_thread:
        mock_thread.return_value = None

        r = client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
            'frame_step': 1,
            'model_size': 'nano',
        })

    assert r.status_code == 202
    data = r.json()
    assert 'job_id' in data
    assert len(data['job_id']) > 0


# ── Test 8: Job status — bilinmeyen ID ───────────────────────────────────────

def test_job_status_unknown_returns_404(client):
    r = client.get('/api/job/00000000-0000-0000-0000-000000000000/status')
    assert r.status_code == 404


# ── Test 9: Statik dosya — index.html ────────────────────────────────────────

def test_static_index_returns_html(client):
    r = client.get('/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert 'Araç Hız Tespit' in r.text


# ── Test 10: Upload boyutu aşıldı ────────────────────────────────────────────

def test_upload_size_limit(client):
    from src.ui import app as ui_app
    # MAX_UPLOAD_BYTES geçici olarak küçült
    original = ui_app._MAX_UPLOAD_BYTES
    ui_app._MAX_UPLOAD_BYTES = 10  # 10 byte

    big_data = b'X' * 100
    r = client.post('/api/video/upload',
                    files={'file': ('big.mp4', io.BytesIO(big_data), 'video/mp4')})
    ui_app._MAX_UPLOAD_BYTES = original
    assert r.status_code == 413


# ── Test 11: Bilinmeyen video ID ─────────────────────────────────────────────

def test_frame_unknown_video_id_returns_404(client):
    r = client.get('/api/video/nonexistent-id/frame/0')
    assert r.status_code == 404


# ── Test 12: Job sonuçları — henüz hazır değil ───────────────────────────────

def test_job_results_not_ready_returns_404(client):
    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    # Pipeline başlat ama thread çalışmasın → state "queued"
    with patch('threading.Thread') as mock_t:
        mock_t.return_value.start = lambda: None
        r = client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
        })
    job_id = r.json().get('job_id', '')

    if job_id:
        r2 = client.get(f'/api/job/{job_id}/results')
        assert r2.status_code == 404


# ── Test 13: Thumbnail uç noktası ────────────────────────────────────────────

def test_thumbnail_returns_jpeg(client):
    vid = client._video_id
    r = client.get(f'/api/video/{vid}/thumbnail')
    assert r.status_code == 200
    assert r.headers['content-type'] == 'image/jpeg'


# ── R3: Kalibrasyon LOO ve holdout alanları ───────────────────────────────────

def test_calibrate_returns_point_count(client):
    """calibrate yanıtı point_count içermeli."""
    vid = client._video_id
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    assert r.status_code == 200
    data = r.json()
    assert 'point_count' in data
    assert data['point_count'] == 4


def test_calibrate_loo_rms_none_for_four_points(client):
    """4 nokta için LOO RMS None olmalı (< 5 nokta)."""
    vid = client._video_id
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    assert r.status_code == 200
    data = r.json()
    assert 'loo_rms_m' in data
    assert data['loo_rms_m'] is None


def test_calibrate_holdout_rows_empty_when_none_held_out(client):
    """held_out nokta yoksa holdout_rows boş liste olmalı."""
    vid = client._video_id
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    assert r.status_code == 200
    data = r.json()
    assert data['holdout_rows'] == []


def test_calibrate_five_points_gives_loo_rms(client):
    """5 nokta → LOO RMS float döner."""
    vid = client._video_id
    five_points = _valid_points() + [
        {'id': 'cp5', 'pixel': [160.0, 350.0], 'world_m': [1.75, 2.5], 'source': 'operator'},
    ]
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': five_points
    })
    assert r.status_code == 200
    data = r.json()
    assert data['loo_rms_m'] is not None
    assert data['loo_rms_m'] >= 0.0


# ── R4: Sunucu-tarafı H yeniden hesaplama + SHA-256 ──────────────────────────

def test_pipeline_server_recomputes_H_from_control_points(client):
    """start_pipeline istemcinin gönderdiği H'yi değil, kontrol noktalarından
    yeniden hesapladığı H'yi kullanmalı (sahte H gönderilse bile iş başlar)."""
    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    # Sahte H — istemci manipüle ediyor
    calibration['homography'] = [[9, 9, 9], [9, 9, 9], [9, 9, 9]]

    with patch('src.ui.app._run_pipeline_thread') as mock_thread:
        mock_thread.return_value = None
        r = client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
            'frame_step': 1,
            'model_size': 'nano',
        })

    # Job kabul edilmeli (422 değil) — sunucu kendi H'sini kullanır
    assert r.status_code == 202
    assert 'job_id' in r.json()


def test_pipeline_passes_sha256_to_thread(client):
    """start_pipeline video SHA-256'yı thread args'larına geçirmeli."""
    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    captured = {}

    class _CapturingThread:
        def __init__(self, target=None, args=(), daemon=False, **kw):
            captured['args'] = args
        def start(self):
            pass

    with patch('threading.Thread', _CapturingThread):
        client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
        })

    thread_args = captured.get('args', ())
    sha_found = any(
        isinstance(a, str) and len(a) == 64 and all(c in '0123456789abcdef' for c in a)
        for a in thread_args
    )
    assert sha_found, f"SHA-256 (64 hex) thread args içinde bulunamadı: {thread_args}"


def test_calibrate_holdout_validation_runs(client):
    """held_out=True nokta varsa holdout_rows dolu döner."""
    vid = client._video_id
    pts = _valid_points() + [
        {'id': 'cp5', 'pixel': [160.0, 350.0], 'world_m': [1.75, 2.5],
         'source': 'operator', 'held_out': True},
    ]
    r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': pts
    })
    assert r.status_code == 200
    data = r.json()
    assert len(data['holdout_rows']) == 1
    row = data['holdout_rows'][0]
    assert row['id'] == 'cp5'
    assert 'error_m' in row


# ── R6: Entegrasyon test katmanı (UI) ─────────────────────────────────────────

def _make_simple_track():
    """Yatay, sabit hızlı 30 karelık sentetik track (test_ui_api yerel yardımcısı)."""
    from src.detection.models import Track, TrackPoint
    points = [
        TrackPoint(
            frame=i, t_s=float(i),
            contact_pixel=(float(i), 20.0),
            bbox=(float(i), 10.0, float(i + 20), 30.0),
        )
        for i in range(30)
    ]
    return Track(track_id=1, vehicle_class="car", points=points)


def test_pipeline_frame_step_reaches_thread_args(client):
    """start_pipeline frame_step=3 → thread args içinde 3 görünür."""
    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    captured = {}

    class _CapturingThread:
        def __init__(self, target=None, args=(), daemon=False, **kw):
            captured['args'] = args
        def start(self):
            pass

    with patch('threading.Thread', _CapturingThread):
        client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
            'frame_step': 3,
        })

    thread_args = captured.get('args', ())
    assert 3 in thread_args, f"frame_step=3 thread args içinde bulunamadı: {thread_args}"


def test_pipeline_fps_override_reaches_thread_args(client):
    """fps_override=60 → thread args içinde 60.0 görünür."""
    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    captured = {}

    class _CapturingThread:
        def __init__(self, target=None, args=(), daemon=False, **kw):
            captured['args'] = args
        def start(self):
            pass

    with patch('threading.Thread', _CapturingThread):
        client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
            'fps_override': 60.0,
        })

    thread_args = captured.get('args', ())
    assert 60.0 in thread_args, f"fps_override=60.0 thread args içinde bulunamadı: {thread_args}"


def test_pipeline_e2e_thread_completes(client):
    """UI e2e: gerçek thread (YOLO mock'lu) → job 'done' state'e ulaşır, sonuçlar erişilebilir."""
    import time

    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()

    track = _make_simple_track()

    # patch.start/stop: thread boyunca patch'ler aktif kalır
    p_tracker = patch('src.output.pipeline.VehicleTracker')
    p_overlay = patch('src.output.pipeline.write_overlay_video')
    p_report = patch('src.output.pipeline.generate_report')

    MockTracker = p_tracker.start()
    p_overlay.start()
    p_report.start()
    MockTracker.return_value.process_video.return_value = ([track], {})

    try:
        r = client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
            'frame_step': 1,
            'model_size': 'nano',
        })
        assert r.status_code == 202
        job_id = r.json()['job_id']

        state = 'queued'
        sr = None
        for _ in range(60):
            time.sleep(0.1)
            sr = client.get(f'/api/job/{job_id}/status')
            state = sr.json()['state']
            if state in ('done', 'error'):
                break

        assert state == 'done', f"İş tamamlanamadı: {sr.json() if sr else 'no response'}"

        rr = client.get(f'/api/job/{job_id}/results')
        assert rr.status_code == 200
        data = rr.json()
        assert 'estimates' in data
        assert 'vehicle_count' in data
    finally:
        p_tracker.stop()
        p_overlay.stop()
        p_report.stop()


# ── M9 — Aks genişliği çapraz doğrulama ──────────────────────────────────────

def _run_completed_job(client) -> str:
    """Yardımcı: kalibre et, mock'lu pipeline'ı çalıştır, tamamlanmış job_id döndür."""
    import time

    vid = client._video_id
    cal_r = client.post('/api/calibrate', json={
        'video_id': vid, 'frame_n': 0, 'control_points': _valid_points()
    })
    calibration = cal_r.json()
    track = _make_simple_track()

    p_tracker = patch('src.output.pipeline.VehicleTracker')
    p_overlay = patch('src.output.pipeline.write_overlay_video')
    p_report = patch('src.output.pipeline.generate_report')
    MockTracker = p_tracker.start()
    p_overlay.start()
    p_report.start()
    MockTracker.return_value.process_video.return_value = ([track], {})

    try:
        r = client.post('/api/pipeline', json={
            'video_id': vid,
            'calibration': calibration,
            'control_points': _valid_points(),
            'frame_step': 1,
            'model_size': 'nano',
        })
        job_id = r.json()['job_id']
        state = 'queued'
        for _ in range(60):
            time.sleep(0.1)
            sr = client.get(f'/api/job/{job_id}/status')
            state = sr.json()['state']
            if state in ('done', 'error'):
                break
        assert state == 'done'
    finally:
        p_tracker.stop()
        p_overlay.stop()
        p_report.stop()

    return job_id


def test_axle_suggest_frame_returns_frame(client):
    job_id = _run_completed_job(client)
    r = client.get(f'/api/job/{job_id}/track/1/axle-suggest-frame')
    assert r.status_code == 200
    assert r.json()['frame_n'] is not None


def test_axle_suggest_frame_unknown_track_404(client):
    job_id = _run_completed_job(client)
    r = client.get(f'/api/job/{job_id}/track/999/axle-suggest-frame')
    assert r.status_code == 404


def test_axle_suggest_frame_unknown_job_404(client):
    r = client.get('/api/job/does-not-exist/track/1/axle-suggest-frame')
    assert r.status_code == 404


def test_axle_check_returns_measurement(client):
    job_id = _run_completed_job(client)
    r = client.post(f'/api/job/{job_id}/track/1/axle-check', json={
        'pixel_left': [100.0, 400.0],
        'pixel_right': [220.0, 400.0],
        'known_width_m': 1.5,
    })
    assert r.status_code == 200
    data = r.json()
    assert 'measured_m' in data
    assert data['known_m'] == 1.5
    assert data['error_pct'] >= 0.0


def test_axle_check_unknown_job_404(client):
    r = client.post('/api/job/does-not-exist/track/1/axle-check', json={
        'pixel_left': [100.0, 400.0],
        'pixel_right': [220.0, 400.0],
        'known_width_m': 1.5,
    })
    assert r.status_code == 404
