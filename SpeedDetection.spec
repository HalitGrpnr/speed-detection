# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Araç Hız Tespit Sistemi
Kullanım: .venv/bin/pyinstaller SpeedDetection.spec
Çıktı: dist/SpeedDetection/  (--onedir)
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# FastAPI / Uvicorn ekosistemi — dinamik import ağırlıklı olduğundan collect_all gerekir
_uvicorn   = collect_all("uvicorn")
_fastapi   = collect_all("fastapi")
_starlette = collect_all("starlette")
_anyio     = collect_all("anyio")

datas = [
    # Statik web dosyaları — app.py'de sys._MEIPASS/src/ui/static olarak aranır
    ("src/ui/static", "src/ui/static"),
]
datas += _uvicorn[0] + _fastapi[0] + _starlette[0] + _anyio[0]

binaries = _uvicorn[1] + _fastapi[1] + _starlette[1] + _anyio[1]

hiddenimports = (
    _uvicorn[2] + _fastapi[2] + _starlette[2] + _anyio[2]
    + [
        # HTTP / async altyapısı
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets.auto",
        "anyio._backends._asyncio",
        "anyio._backends._trio",
        "h11",
        "click",
        "multipart",
        "multipart.multipart",
        # Uygulama modülleri (PyInstaller bazen bulamaz)
        "src",
        "src.ui", "src.ui.app", "src.ui.schemas", "src.ui.job_store",
        "src.calibration", "src.calibration.homography",
        "src.calibration.io", "src.calibration.models", "src.calibration.metrics",
        "src.detection", "src.detection.video", "src.detection.models",
        "src.detection.tracker", "src.detection.detector",
        "src.autoref", "src.autoref.proposer", "src.autoref.lane",
        "src.autoref.markers", "src.autoref.models",
        "src.speed", "src.speed.calculator", "src.speed.smoother", "src.speed.models",
        "src.reliability", "src.reliability.confidence", "src.reliability.planarity",
        "src.output", "src.output.pipeline", "src.output.overlay",
        "src.output.report", "src.output.models",
        # Bilimsel yığın
        "scipy.optimize", "scipy.linalg", "scipy.stats",
        "numpy", "cv2",
        # Rapor
        "reportlab", "reportlab.pdfgen", "reportlab.lib",
        "reportlab.platypus",
    ]
)

a = Analysis(
    ["src/ui/launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Test/geliştirme bağımlılıkları pakete girmesin
        "pytest", "httpx", "playwright",
        "IPython", "jupyter", "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SpeedDetection",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # Minimal terminal penceresi — hata/log görünürlüğü için
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SpeedDetection",
)
