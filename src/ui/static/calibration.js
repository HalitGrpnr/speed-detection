/**
 * calibration.js — Canvas üzerinde nokta tıklama ve yönetimi.
 *
 * Sorumluluklar:
 *  - Kalibrasyon karesini canvas'a çizmek
 *  - Sol tıkla nokta eklemek
 *  - Varolan noktayı sol tıkla seçip sürüklemek
 *  - Seçili noktayı silmek
 *  - Değişikliklerde onChange(points) çağırmak
 */

const CalibrationCanvas = (() => {
  const RADIUS = 8;
  const COLOR_DEFAULT = '#f59e0b';   // sarı
  const COLOR_AUTO    = '#60a5fa';   // mavi (M6 otomatik öneri)
  const COLOR_SITE    = '#34d399';   // yeşil (saha ölçümü)
  const COLOR_SELECT  = '#ef4444';   // kırmızı (seçili)
  const COLOR_TEXT    = '#ffffff';

  let canvas = null;
  let ctx    = null;
  let img    = null;        // HTMLImageElement
  let scale  = 1;           // görüntü pikseli → canvas pikseli
  let offsetX = 0;
  let offsetY = 0;
  let points = [];          // [{id, pixel:[u,v], world_m:[X,Y], source}]
  let selectedIdx = -1;
  let dragging = false;
  let onChange = null;
  let nextId = 1;

  function _sourceColor(src) {
    if (src === 'auto')             return COLOR_AUTO;
    if (src === 'site_measurement') return COLOR_SITE;
    return COLOR_DEFAULT;
  }

  function _canvasToImage(cx, cy) {
    return [(cx - offsetX) / scale, (cy - offsetY) / scale];
  }

  function _imageToCanvas(ix, iy) {
    return [ix * scale + offsetX, iy * scale + offsetY];
  }

  function _findNear(cx, cy) {
    for (let i = points.length - 1; i >= 0; i--) {
      const [px, py] = _imageToCanvas(...points[i].pixel);
      const d = Math.hypot(cx - px, cy - py);
      if (d <= RADIUS + 4) return i;
    }
    return -1;
  }

  function draw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (img) {
      ctx.drawImage(img, offsetX, offsetY, img.naturalWidth * scale, img.naturalHeight * scale);
    }

    points.forEach((pt, i) => {
      const [cx, cy] = _imageToCanvas(...pt.pixel);
      const isSelected = i === selectedIdx;
      const color = isSelected ? COLOR_SELECT : _sourceColor(pt.source);

      ctx.beginPath();
      ctx.arc(cx, cy, RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = color + 'cc';
      ctx.fill();
      ctx.strokeStyle = isSelected ? COLOR_SELECT : '#fff';
      ctx.lineWidth = isSelected ? 2.5 : 1.5;
      ctx.stroke();

      // numara etiketi
      ctx.fillStyle = COLOR_TEXT;
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(i + 1), cx, cy);

      // dünya koordinat etiketi (seçiliyse)
      if (isSelected) {
        const label = `(${pt.world_m[0].toFixed(2)}, ${pt.world_m[1].toFixed(2)}) m`;
        ctx.font = '11px sans-serif';
        ctx.fillStyle = '#000';
        ctx.fillRect(cx + RADIUS + 2, cy - 8, label.length * 6.5, 16);
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'left';
        ctx.fillText(label, cx + RADIUS + 4, cy);
      }
    });
  }

  function _layout() {
    if (!canvas || !img) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    const maxW = rect.width || 800;
    const maxH = window.innerHeight * 0.55;
    const scaleW = maxW / img.naturalWidth;
    const scaleH = maxH / img.naturalHeight;
    scale = Math.min(scaleW, scaleH, 1);
    canvas.width  = img.naturalWidth  * scale;
    canvas.height = img.naturalHeight * scale;
    offsetX = 0;
    offsetY = 0;
    draw();
  }

  function _onMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const cx = (e.clientX - rect.left) * (canvas.width  / rect.width);
    const cy = (e.clientY - rect.top)  * (canvas.height / rect.height);

    const hit = _findNear(cx, cy);
    if (hit >= 0) {
      selectedIdx = hit;
      dragging = true;
    } else {
      // Yeni nokta ekle
      const [ix, iy] = _canvasToImage(cx, cy);
      const id = `cp_op_${nextId++}`;
      points.push({ id, pixel: [ix, iy], world_m: [0, 0], source: 'operator' });
      selectedIdx = points.length - 1;
      dragging = false;
      if (onChange) onChange([...points]);
    }
    draw();
  }

  function _onMouseMove(e) {
    if (!dragging || selectedIdx < 0) return;
    const rect = canvas.getBoundingClientRect();
    const cx = (e.clientX - rect.left) * (canvas.width  / rect.width);
    const cy = (e.clientY - rect.top)  * (canvas.height / rect.height);
    const [ix, iy] = _canvasToImage(cx, cy);
    points[selectedIdx].pixel = [
      Math.max(0, Math.min(img.naturalWidth  - 1, ix)),
      Math.max(0, Math.min(img.naturalHeight - 1, iy)),
    ];
    draw();
  }

  function _onMouseUp() {
    if (dragging && selectedIdx >= 0) {
      if (onChange) onChange([...points]);
    }
    dragging = false;
  }

  // ── Public API ────────────────────────────────────────────────────────────

  function init(canvasEl, changeCallback) {
    canvas = canvasEl;
    ctx = canvas.getContext('2d');
    onChange = changeCallback;

    canvas.addEventListener('mousedown', _onMouseDown);
    canvas.addEventListener('mousemove', _onMouseMove);
    canvas.addEventListener('mouseup',   _onMouseUp);
    canvas.addEventListener('mouseleave', _onMouseUp);

    window.addEventListener('resize', _layout);
  }

  function loadImage(src) {
    return new Promise((resolve) => {
      img = new Image();
      img.onload = () => { _layout(); resolve(); };
      img.src = src;
    });
  }

  function getPoints() { return [...points]; }

  function setPoints(newPoints) {
    points = newPoints.map(p => ({ ...p }));
    const maxId = points.reduce((m, p) => {
      const n = parseInt(p.id.replace(/\D/g, ''), 10);
      return isNaN(n) ? m : Math.max(m, n);
    }, 0);
    nextId = maxId + 1;
    selectedIdx = -1;
    draw();
  }

  function updateWorldM(idx, worldM) {
    if (idx >= 0 && idx < points.length) {
      points[idx].world_m = worldM;
      draw();
    }
  }

  function updateSource(idx, source) {
    if (idx >= 0 && idx < points.length) {
      points[idx].source = source;
      draw();
    }
  }

  function deleteSelected() {
    if (selectedIdx < 0) return;
    points.splice(selectedIdx, 1);
    selectedIdx = Math.min(selectedIdx, points.length - 1);
    if (onChange) onChange([...points]);
    draw();
  }

  function getSelectedIdx() { return selectedIdx; }

  function addAutoProposals(proposals) {
    const autoPoints = proposals.map((p, i) => ({
      id: `cp_auto_${Date.now()}_${i}`,
      pixel: p.pixel,
      world_m: p.world_m,
      source: 'auto',
    }));
    points.push(...autoPoints);
    if (onChange) onChange([...points]);
    draw();
  }

  return {
    init,
    loadImage,
    getPoints,
    setPoints,
    updateWorldM,
    updateSource,
    deleteSelected,
    getSelectedIdx,
    addAutoProposals,
  };
})();
