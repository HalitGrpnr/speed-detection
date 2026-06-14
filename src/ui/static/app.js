/**
 * app.js — Durum makinesi, adım geçişleri, API çağrıları.
 */

const API = {
  async uploadVideo(file) {
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/video/upload', { method: 'POST', body: fd });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },

  async getFrame(videoId, frameN) {
    return `/api/video/${videoId}/frame/${frameN}`;
  },

  async calibrate(videoId, frameN, points) {
    const r = await fetch('/api/calibrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, frame_n: frameN, control_points: points }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },

  async autoref(videoId, frameN, laneWidth, dashLength, dNear) {
    const r = await fetch(`/api/video/${videoId}/autoref`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        frame_n: frameN,
        lane_width_m: laneWidth,
        dash_length_m: dashLength,
        d_near_m: dNear,
      }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },

  async startPipeline(videoId, calibration, points, options) {
    const r = await fetch('/api/pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: videoId,
        calibration,
        control_points: points,
        fps_override: options.fpsOverride || null,
        frame_step: options.frameStep,
        model_size: options.modelSize,
      }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },

  async jobStatus(jobId) {
    const r = await fetch(`/api/job/${jobId}/status`);
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },

  async jobResults(jobId) {
    const r = await fetch(`/api/job/${jobId}/results`);
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    return r.json();
  },
};

// ── App state ─────────────────────────────────────────────────────────────────

const State = {
  videoMeta: null,
  frameN: 0,
  calPoints: [],
  calibration: null,
  jobId: null,
  jobResults: null,
};

// ── DOM refs ──────────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

// ── Step navigation ───────────────────────────────────────────────────────────

let currentStep = 1;

function showStep(n) {
  document.querySelectorAll('.step-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.step-indicator .step').forEach((el, i) => {
    el.classList.toggle('active', i + 1 === n);
    el.classList.toggle('done',   i + 1 < n);
  });
  $(`step${n}`).classList.add('active');
  currentStep = n;
  window.scrollTo(0, 0);
}

// ── Step 1 — Video yükle ──────────────────────────────────────────────────────

function initStep1() {
  const zone  = $('drop-zone');
  const input = $('file-input');

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  });
  input.addEventListener('change', () => { if (input.files[0]) handleUpload(input.files[0]); });
}

async function handleUpload(file) {
  $('upload-status').style.display = 'block';
  $('upload-status').textContent = 'Yükleniyor…';
  $('upload-status').className = 'status info';
  try {
    const meta = await API.uploadVideo(file);
    State.videoMeta = meta;
    $('upload-status').textContent =
      `✓ ${file.name} — ${meta.width}×${meta.height} @ ${meta.fps.toFixed(2)} fps — ${meta.frame_count} kare`;
    $('upload-status').className = 'status ok';
    $('meta-sha').textContent = meta.sha256;
    $('meta-block').style.display = 'block';
    $('btn-to-step2').disabled = false;
  } catch (e) {
    $('upload-status').textContent = `Hata: ${e.message}`;
    $('upload-status').className = 'status error';
  }
}

// ── Step 2 — Kalibrasyon karesi ───────────────────────────────────────────────

function initStep2() {
  $('frame-slider').addEventListener('input', () => {
    const n = parseInt($('frame-slider').value, 10);
    $('frame-num-display').textContent = n;
    $('frame-num-input').value = n;
    State.frameN = n;
    updateFramePreview();
  });

  $('frame-num-input').addEventListener('change', () => {
    const n = Math.max(0, Math.min(
      State.videoMeta.frame_count - 1,
      parseInt($('frame-num-input').value, 10) || 0
    ));
    $('frame-num-input').value = n;
    $('frame-slider').value = n;
    $('frame-num-display').textContent = n;
    State.frameN = n;
    updateFramePreview();
  });

  $('btn-prev-frame').addEventListener('click', () => {
    const n = Math.max(0, State.frameN - 1);
    $('frame-num-input').value = n;
    $('frame-slider').value = n;
    $('frame-num-display').textContent = n;
    State.frameN = n;
    updateFramePreview();
  });

  $('btn-next-frame').addEventListener('click', () => {
    const n = Math.min(State.videoMeta.frame_count - 1, State.frameN + 1);
    $('frame-num-input').value = n;
    $('frame-slider').value = n;
    $('frame-num-display').textContent = n;
    State.frameN = n;
    updateFramePreview();
  });
}

function enterStep2() {
  const meta = State.videoMeta;
  $('frame-slider').max = meta.frame_count - 1;
  const mid = Math.floor(meta.frame_count / 2);
  $('frame-slider').value = mid;
  $('frame-num-input').value = mid;
  $('frame-num-display').textContent = mid;
  State.frameN = mid;
  updateFramePreview();
}

function updateFramePreview() {
  const src = `/api/video/${State.videoMeta.video_id}/frame/${State.frameN}?t=${Date.now()}`;
  $('frame-preview').src = src;
}

// ── Step 3 — Kontrol noktaları ────────────────────────────────────────────────

let calCanvas = null;
let rmsDebounce = null;

function initStep3() {
  calCanvas = $('cal-canvas');
  CalibrationCanvas.init(calCanvas, onPointsChanged);

  $('btn-delete-point').addEventListener('click', () => {
    CalibrationCanvas.deleteSelected();
  });

  $('btn-autoref').addEventListener('click', runAutoRef);

  $('btn-preset-lane').addEventListener('click', () => {
    const pts = CalibrationCanvas.getPoints();
    if (pts.length < 2) {
      alert('En az 2 nokta gerekli. İlk tıkladığınız iki nokta sol ve sağ şerit olarak atanır.');
      return;
    }
    // Sol şerit X=0, sağ şerit X=3.5 — en son eklenen 2 nokta
    const last2 = pts.slice(-2);
    last2[0].world_m = [0.0, last2[0].world_m[1]];
    last2[1].world_m = [3.5, last2[1].world_m[1]];
    const updated = [...pts.slice(0, -2), ...last2];
    CalibrationCanvas.setPoints(updated);
    onPointsChanged(updated);
  });

  $('btn-preset-rect').addEventListener('click', () => {
    const pts = CalibrationCanvas.getPoints();
    if (pts.length < 4) {
      alert('En az 4 nokta gerekli.\nTıklama sırası: (1) yakın-sol  (2) yakın-sağ  (3) uzak-sol  (4) uzak-sağ');
      return;
    }
    const laneWidth = parseFloat($('autoref-lane-width').value) || 3.5;
    const yDist     = parseFloat($('autoref-dash-length').value) || 3.0;
    // Son 4 noktaya sırayla koordinat ata
    const n = pts.length;
    const coords = [[0, 0], [laneWidth, 0], [0, yDist], [laneWidth, yDist]];
    coords.forEach(([x, y], i) => { pts[n - 4 + i].world_m = [x, y]; });
    CalibrationCanvas.setPoints(pts);
    onPointsChanged(pts);
  });
}

async function enterStep3() {
  const src = `/api/video/${State.videoMeta.video_id}/frame/${State.frameN}?t=${Date.now()}`;
  await CalibrationCanvas.loadImage(src);
  CalibrationCanvas.setPoints([]);
  State.calPoints = [];
  renderPointsTable([]);
  updateRmsDisplay(null);
}

function onPointsChanged(pts) {
  State.calPoints = pts;
  renderPointsTable(pts);
  scheduleRmsUpdate(pts);
}

function renderPointsTable(pts) {
  const tbody = $('points-table-body');
  tbody.innerHTML = '';
  pts.forEach((pt, i) => {
    const tr = document.createElement('tr');
    tr.dataset.idx = i;
    const srcLabel = { operator: 'Operatör', auto: 'Otomatik', site_measurement: 'Saha' };
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>(${pt.pixel[0].toFixed(0)}, ${pt.pixel[1].toFixed(0)})</td>
      <td><input class="coord-input" type="number" step="0.01" value="${pt.world_m[0].toFixed(2)}" data-axis="x" data-idx="${i}"></td>
      <td><input class="coord-input" type="number" step="0.01" value="${pt.world_m[1].toFixed(2)}" data-axis="y" data-idx="${i}"></td>
      <td>
        <select class="source-select" data-idx="${i}">
          <option value="operator"         ${pt.source === 'operator'         ? 'selected' : ''}>Operatör</option>
          <option value="auto"             ${pt.source === 'auto'             ? 'selected' : ''}>Otomatik</option>
          <option value="site_measurement" ${pt.source === 'site_measurement' ? 'selected' : ''}>Saha</option>
        </select>
      </td>
      <td><button class="btn-tiny btn-danger" data-del="${i}">✕</button></td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('.coord-input').forEach(inp => {
    inp.addEventListener('change', () => {
      const idx = parseInt(inp.dataset.idx, 10);
      const axis = inp.dataset.axis;
      const pts2 = CalibrationCanvas.getPoints();
      if (axis === 'x') pts2[idx].world_m[0] = parseFloat(inp.value) || 0;
      else              pts2[idx].world_m[1] = parseFloat(inp.value) || 0;
      CalibrationCanvas.setPoints(pts2);
      scheduleRmsUpdate(pts2);
    });
  });

  tbody.querySelectorAll('.source-select').forEach(sel => {
    sel.addEventListener('change', () => {
      const idx = parseInt(sel.dataset.idx, 10);
      const pts2 = CalibrationCanvas.getPoints();
      pts2[idx].source = sel.value;
      CalibrationCanvas.setPoints(pts2);
    });
  });

  tbody.querySelectorAll('[data-del]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.del, 10);
      const pts2 = CalibrationCanvas.getPoints();
      pts2.splice(idx, 1);
      CalibrationCanvas.setPoints(pts2);
      onPointsChanged(pts2);
    });
  });

  $('btn-to-step4').disabled = pts.length < 4;
}

function scheduleRmsUpdate(pts) {
  clearTimeout(rmsDebounce);
  rmsDebounce = setTimeout(() => triggerRmsUpdate(pts), 400);
}

async function triggerRmsUpdate(pts) {
  if (pts.length < 4) { updateRmsDisplay(null); return; }
  try {
    const cal = await API.calibrate(State.videoMeta.video_id, State.frameN, pts);
    updateRmsDisplay(cal);
  } catch (e) {
    console.warn('Kalibrasyon RMS güncellenemedi:', e);
    updateRmsDisplay(null);
  }
}

function updateRmsDisplay(cal) {
  const box = $('rms-box');
  if (!cal) {
    box.textContent = 'RMS: — (≥4 nokta gerekli)';
    box.className = 'rms-box rms-na';
    return;
  }
  const rms_cm = (cal.rms_m * 100).toFixed(1);
  const cls = cal.rms_m < 0.05 ? 'rms-good' : cal.rms_m < 0.20 ? 'rms-medium' : 'rms-bad';
  let msg = `RMS: ${rms_cm} cm — ${cal.confidence_layer}`;
  if (cal.loo_rms_m != null) {
    msg += `  |  LOO: ${(cal.loo_rms_m * 100).toFixed(1)} cm`;
  }
  if ((cal.point_count || 0) < 6) {
    msg += '  ⚠ Redundancy yok (< 6 nokta) — RMS yanıltıcı olabilir';
  }
  if (cal.planarity_warning) msg += '  ⚠ Düzlemsellik uyarısı';
  box.textContent = msg;
  box.className = `rms-box ${cls}`;
}

async function runAutoRef() {
  const btn = $('btn-autoref');
  btn.disabled = true;
  btn.textContent = 'Analiz ediliyor…';
  try {
    const laneWidth = parseFloat($('autoref-lane-width').value) || 3.5;
    const dashLen   = parseFloat($('autoref-dash-length').value) || 3.0;
    const dNear     = parseFloat($('autoref-d-near').value) || 5.0;
    const proposals = await API.autoref(
      State.videoMeta.video_id, State.frameN, laneWidth, dashLen, dNear
    );
    if (proposals.length === 0) {
      alert('Şerit tespit edilemedi. Farklı bir kare deneyin veya noktaları elle girin.');
    } else {
      CalibrationCanvas.addAutoProposals(proposals);
    }
  } catch (e) {
    alert(`Otomatik öneri hatası: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'M6 Otomatik Öner';
  }
}

// ── Step 4 — Kalibrasyon onayla ───────────────────────────────────────────────

async function enterStep4() {
  const pts = CalibrationCanvas.getPoints();
  $('step4-status').textContent = 'Kalibrasyon hesaplanıyor…';
  $('step4-status').className = 'status info';
  try {
    const cal = await API.calibrate(State.videoMeta.video_id, State.frameN, pts);
    State.calibration = cal;
    const rms_cm = (cal.rms_m * 100).toFixed(1);
    $('cal-summary-rms').textContent       = `${rms_cm} cm`;
    $('cal-summary-inliers').textContent   = `${cal.inlier_count} / ${pts.length}`;
    $('cal-summary-layer').textContent     = cal.confidence_layer;
    $('cal-summary-planarity').textContent = cal.planarity_warning ? '⚠ Evet' : 'Hayır';

    const looEl = $('cal-summary-loo');
    if (looEl) {
      if (cal.loo_rms_m != null) {
        looEl.textContent = `${(cal.loo_rms_m * 100).toFixed(1)} cm`;
        looEl.className = cal.loo_rms_m < 0.05 ? 'val-good' : cal.loo_rms_m < 0.20 ? 'val-medium' : 'val-bad';
      } else {
        looEl.textContent = `— (${pts.length < 5 ? '< 5 nokta' : 'hesaplanamadı'})`;
        looEl.className = '';
      }
    }
    const redEl = $('cal-summary-redundancy');
    if (redEl) {
      const n = cal.point_count || pts.length;
      redEl.textContent = n >= 6 ? `✓ ${n} nokta` : `⚠ ${n} nokta — redundancy yetersiz`;
      redEl.className = n >= 6 ? 'val-good' : 'val-warn';
    }

    $('step4-status').textContent = '✓ Kalibrasyon hazır.';
    $('step4-status').className = 'status ok';
    $('btn-to-step5').disabled = false;
  } catch (e) {
    $('step4-status').textContent = `Hata: ${e.message}`;
    $('step4-status').className = 'status error';
    $('btn-to-step5').disabled = true;
  }
}

// ── Step 5 — Pipeline ─────────────────────────────────────────────────────────

function initStep5() {
  $('fps-override-check').addEventListener('change', () => {
    $('fps-override-input').disabled = !$('fps-override-check').checked;
  });
}

async function runPipeline() {
  const btn = $('btn-run-pipeline');
  btn.disabled = true;
  $('pipeline-status').textContent = 'Pipeline başlatılıyor…';
  $('pipeline-status').className = 'status info';
  $('progress-bar-fill').style.width = '5%';

  const options = {
    fpsOverride: $('fps-override-check').checked
      ? parseFloat($('fps-override-input').value) : null,
    frameStep: parseInt($('frame-step-select').value, 10),
    modelSize: $('model-size-select').value,
  };

  try {
    const { job_id } = await API.startPipeline(
      State.videoMeta.video_id,
      State.calibration,
      State.calPoints,
      options,
    );
    State.jobId = job_id;
    pollJobStatus(job_id);
  } catch (e) {
    $('pipeline-status').textContent = `Başlatma hatası: ${e.message}`;
    $('pipeline-status').className = 'status error';
    btn.disabled = false;
  }
}

function pollJobStatus(jobId) {
  const timer = setInterval(async () => {
    try {
      const st = await API.jobStatus(jobId);
      $('progress-bar-fill').style.width = `${Math.max(5, st.progress_pct)}%`;

      if (st.state === 'done') {
        clearInterval(timer);
        $('progress-bar-fill').style.width = '100%';
        $('pipeline-status').textContent = '✓ Tamamlandı.';
        $('pipeline-status').className = 'status ok';
        const results = await API.jobResults(jobId);
        State.jobResults = results;
        showStep(6);
        enterStep6();
      } else if (st.state === 'error') {
        clearInterval(timer);
        $('pipeline-status').textContent = `Hata: ${st.error}`;
        $('pipeline-status').className = 'status error';
        $('btn-run-pipeline').disabled = false;
      } else {
        $('pipeline-status').textContent =
          `İşleniyor… ${st.progress_pct.toFixed(0)}%` +
          (st.eta_s ? ` (tahmini: ${st.eta_s.toFixed(0)} sn)` : '');
      }
    } catch {
      // polling hatası geçici olabilir, devam et
    }
  }, 1500);
}

// ── Step 6 — Sonuçlar ─────────────────────────────────────────────────────────

function enterStep6() {
  const results = State.jobResults;
  $('result-count').textContent = `${results.vehicle_count} araç`;

  const tbody = $('results-table-body');
  tbody.innerHTML = '';
  if (results.estimates.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6">Yeterli uzunlukta track bulunamadı.</td></tr>';
  } else {
    results.estimates.forEach(est => {
      const cls = est.confidence_level === 'high' ? 'conf-high'
                : est.confidence_level === 'medium' ? 'conf-medium' : 'conf-low';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${est.track_id}</td>
        <td>${est.vehicle_class}</td>
        <td><strong>${est.speed_kmh.toFixed(1)}</strong></td>
        <td>± ${est.ci_kmh.toFixed(1)}</td>
        <td><span class="conf-badge ${cls}">${est.confidence_level}</span></td>
        <td>${est.frame_count}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  $('btn-download-report').href   = `/api/job/${State.jobId}/report`;
  $('btn-download-overlay').href  = `/api/job/${State.jobId}/overlay/download`;

  // Tarayıcı moov-atom sorununu (OpenCV mp4v varsayılanı) aşmak için
  // videoyu önce belleğe çekip Blob URL'e bağla.
  const videoEl = $('overlay-video');
  videoEl.src = '';
  videoEl.textContent = 'Video yükleniyor…';
  fetch(`/api/job/${State.jobId}/overlay`)
    .then(r => r.blob())
    .then(blob => {
      videoEl.src = URL.createObjectURL(blob);
      videoEl.load();
    })
    .catch(() => {
      videoEl.src = `/api/job/${State.jobId}/overlay`;
      videoEl.load();
    });
}

// ── Buton bağlantıları ────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initStep1();
  initStep2();
  initStep3();
  initStep5();

  $('btn-to-step2').addEventListener('click', () => { showStep(2); enterStep2(); });
  $('btn-to-step1').addEventListener('click', () => showStep(1));

  $('btn-to-step3').addEventListener('click', () => { showStep(3); enterStep3(); });
  $('btn-back-step2').addEventListener('click', () => showStep(2));

  $('btn-to-step4').addEventListener('click', () => { showStep(4); enterStep4(); });
  $('btn-back-step3').addEventListener('click', () => showStep(3));

  $('btn-to-step5').addEventListener('click', () => showStep(5));
  $('btn-back-step4').addEventListener('click', () => { showStep(4); enterStep4(); });

  $('btn-run-pipeline').addEventListener('click', runPipeline);
  $('btn-back-step5').addEventListener('click', () => showStep(5));

  $('btn-new-analysis').addEventListener('click', () => {
    // Durumu sıfırla
    Object.assign(State, {
      videoMeta: null, frameN: 0, calPoints: [],
      calibration: null, jobId: null, jobResults: null,
    });
    $('upload-status').textContent = '';
    $('meta-block').style.display = 'none';
    $('btn-to-step2').disabled = true;
    showStep(1);
  });

  showStep(1);
});
