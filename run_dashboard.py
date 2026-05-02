"""Arranque de Streamlit leyendo PORT; por defecto 8501."""

import os
import subprocess
import sys

if __name__ == "__main__":
    port = os.environ.get("PORT", "8501")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "dashboard.py",
            "--server.port",
            port,
            "--server.address",
            "0.0.0.0",
        ],
        check=True,
    )
