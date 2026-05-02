"""Arranque de Streamlit leyendo PORT; por defecto 8501.

Quita STREAMLIT_SERVER_PORT del entorno del hijo si viene como '$PORT' literal u otro valor inválido:
Streamlit mezcla esa variable con --server.port y falla antes de aplicar el CLI.
"""

import os
import subprocess
import sys

from port_util import port_from_env

if __name__ == "__main__":
    port = str(port_from_env(8501))
    env = os.environ.copy()
    env.pop("STREAMLIT_SERVER_PORT", None)
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
        env=env,
    )
