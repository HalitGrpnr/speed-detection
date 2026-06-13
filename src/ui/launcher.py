"""Başlatıcı — PyInstaller paketi için.

Uvicorn sunucusunu başlatır, hazır olunca tarayıcıyı açar.
Kullanıcı Python veya komut satırı görmez; tek tıklama ile çalışır.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
import webbrowser

PORT = 8742


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main() -> None:
    if not _port_free(PORT):
        # Sunucu zaten çalışıyor (örn. ikinci tıklama)
        webbrowser.open(f"http://127.0.0.1:{PORT}")
        return

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.ui.app:app",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--log-level", "warning",
        ],
    )

    # Sunucu hazır olana kadar bekle (maks 15 sn)
    for _ in range(30):
        if not _port_free(PORT):
            break
        time.sleep(0.5)

    webbrowser.open(f"http://127.0.0.1:{PORT}")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
