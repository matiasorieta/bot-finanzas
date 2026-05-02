"""Puerto desde PORT: tolera ausencia, vacío o valores tipo '$PORT' sin expandir (Railway/UI mal configurada)."""

import os


def port_from_env(default: int) -> int:
    raw = (os.environ.get("PORT") or "").strip()
    if not raw or raw.startswith("$"):
        return default
    try:
        n = int(raw)
    except ValueError:
        return default
    if not (1 <= n <= 65535):
        return default
    return n
