"""Başlatıcı — geliştirme ve PyInstaller paketi için.

Uvicorn'u arka plan thread'inde başlatır, hazır olunca tarayıcıyı açar.
Frozen (PyInstaller) ortamında subprocess + `-m uvicorn` kullanılamaz;
bunun yerine uvicorn.run() doğrudan thread içinde çağrılır.
"""
from __future__ import annotations

import socket
import threading
import time
import webbrowser

PORT = 8742


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _serve() -> None:
    import uvicorn
    from src.ui.app import app  # noqa: PLC0415
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def main() -> None:
    if not _port_free(PORT):
        # Sunucu zaten çalışıyor (ikinci tıklama)
        webbrowser.open(f"http://127.0.0.1:{PORT}")
        return

    t = threading.Thread(target=_serve, daemon=True)
    t.start()

    # Sunucu hazır olana kadar bekle (maks 15 sn)
    for _ in range(30):
        if not _port_free(PORT):
            break
        time.sleep(0.5)

    webbrowser.open(f"http://127.0.0.1:{PORT}")

    try:
        while t.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nKapatılıyor…")


if __name__ == "__main__":
    main()
