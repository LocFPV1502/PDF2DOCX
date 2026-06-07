"""Bootstrapper: start Streamlit server + auto-open browser."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path


def find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main():
    """Launch Streamlit server and open browser."""
    # Determine project root
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        project_root = Path(sys._MEIPASS)
        app_path = project_root / "app.py"
    else:
        project_root = Path(__file__).parent
        app_path = project_root / "app.py"

    # Find free port
    port = find_free_port()

    print(f"[PDF OCR Converter] Starting on port {port}...")

    # Build Streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.address", "localhost",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light",
    ]

    # Set environment variables
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    # Start Streamlit process
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Wait for server to be ready
    url = f"http://localhost:{port}"
    ready = False
    max_wait = 30  # seconds

    for i in range(max_wait * 2):  # check every 0.5s
        time.sleep(0.5)
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                ready = True
                break
        except (ConnectionRefusedError, OSError):
            continue

    if ready:
        print(f"[PDF OCR Converter] Server ready at {url}")
        # Open browser
        webbrowser.open(url)
    else:
        print(f"[PDF OCR Converter] Warning: Server may not be ready. Try opening {url}")

    # Wait for process to finish (user closes browser or Ctrl+C)
    def signal_handler(sig, frame):
        print("\n[PDF OCR Converter] Shutting down...")
        process.terminate()
        process.wait(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait(timeout=5)

    print("[PDF OCR Converter] Done.")


if __name__ == "__main__":
    main()
