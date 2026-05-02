"""Arranque de FastAPI leyendo PORT (Railway/Heroku); por defecto 8000."""

import uvicorn

from port_util import port_from_env

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port_from_env(8000))
