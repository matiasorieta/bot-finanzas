"""
Arranque del dashboard en Railway/Heroku.

Streamlit lee STREAMLIT_SERVER_PORT antes de importar dashboard.py; por eso hay que
sanear el entorno aquí y lanzar `python -m streamlit` como subproceso.
"""

import os
import subprocess
import sys


def _listen_port(default: str = "8501") -> str:
    raw = (os.environ.get("PORT") or "").strip()
    if raw.startswith("$"):
        return default
    try:
        n = int(raw)
        if 1 <= n <= 65535:
            return str(n)
    except ValueError:
        pass
    return default


def main() -> None:
    port = _listen_port()
    os.environ.pop("STREAMLIT_SERVER_PORT", None)
    os.environ["STREAMLIT_SERVER_PORT"] = port
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "dashboard.py",
                "--server.address",
                "0.0.0.0",
            ],
            env=os.environ,
        )
    )


if __name__ == "__main__":
    main()
