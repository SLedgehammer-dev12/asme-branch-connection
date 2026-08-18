# =============================================================================
# ASME B31.8 Pipeline Designer V3.3 — Standalone Launcher
# PyInstaller ile .exe ve macOS App olarak paketlenecek baslatici
# =============================================================================
import sys
import os
import subprocess
import socket
import webbrowser
import time
import threading
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')


def get_free_port():
    """Bos bir port bulur."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def get_base_dir():
    """
    PyInstaller --onefile modunda sys._MEIPASS gecici klasorudur.
    Normal calismada __file__ dizini kullanilir.
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def open_browser(port, delay=2.0):
    """Belirtilen sure sonra tarayiciyi acar."""
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main():
    base_dir = get_base_dir()
    app_path = os.path.join(base_dir, "app.py")
    port = get_free_port()

    # Tarayiciyi arka planda ac
    browser_thread = threading.Thread(target=open_browser, args=(port, 3.0), daemon=True)
    browser_thread.start()

    # Streamlit'i calistir
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.address", "localhost",
        "--theme.primaryColor", "#4CAF50",
        "--theme.base", "light",
        "--global.developmentMode", "false"
    ]

    # Streamlit CLI'yi dogrudan cagir
    from streamlit.web import cli as stcli
    stcli.main()


if __name__ == "__main__":
    main()
