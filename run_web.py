"""Arranque de FastAPI leyendo PORT (Railway/Heroku); por defecto 8000 (local Windows/Linux)."""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
