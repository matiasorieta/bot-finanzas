import json
import logging
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_api_exceptions

logger = logging.getLogger(__name__)

# Orden: modelos con mejor cupo típico en free tier primero; fallback si cuota o nombre inválido.
_DEFAULT_MODEL_CHAIN: tuple[str, ...] = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
)

_RETRY_EXCEPTIONS: tuple[type[BaseException], ...] = (
    google_api_exceptions.ResourceExhausted,
    google_api_exceptions.InvalidArgument,
    google_api_exceptions.NotFound,
    google_api_exceptions.FailedPrecondition,
)

ALLOWED_CATEGORIES = [
    "comida",
    "supermercado",
    "salidas",
    "transporte",
    "suscripciones",
    "servicios",
    "gimnasio",
    "mascota",
    "familia",
    "auto",
    "viajes",
    "compras",
    "cuotas",
    "otros",
]

_SYSTEM_PROMPT = f"""Eres un extractor de gastos para mensajes en español (WhatsApp).
Devuelve EXCLUSIVAMENTE un objeto JSON válido, sin markdown ni texto adicional.

Esquema obligatorio:
{{
  "amount": <número>,
  "category": "<string>",
  "description": "<string corta>",
  "date": "YYYY-MM-DD"
}}

Categorías permitidas (STRICT, usa exactamente una de estas en minúsculas):
{json.dumps(ALLOWED_CATEGORIES, ensure_ascii=False)}

Reglas de monto:
- "5 lucas", "5k", "5 mil" → 5000 (en este contexto lucas/k = miles de la moneda local).
- Interpreta números con coma o punto decimal de forma coherente.

Reglas de fecha:
- Si el usuario dice "ayer", usa la fecha de ayer respecto al día de hoy del sistema (se te dará la fecha de referencia).
- Si dice "hoy", usa la fecha de hoy de referencia.
- Si no hay fecha clara, usa la fecha de hoy de referencia.

Descripción: muy breve, sin inventar detalles que no estén en el mensaje.

Hoy de referencia (UTC): se insertará en el prompt de usuario como FECHA_REFERENCIA.
"""


def _reference_today() -> date:
    return date.today()


def _model_chain() -> list[str]:
    explicit = (os.environ.get("GEMINI_MODEL") or "").strip()
    if explicit:
        return [explicit] + [m for m in _DEFAULT_MODEL_CHAIN if m != explicit]
    return list(_DEFAULT_MODEL_CHAIN)


def _payload_from_parsed(data: dict[str, Any], ref: date) -> dict[str, Any]:
    amount = data.get("amount")
    category = str(data.get("category", "otros")).strip().lower()
    description = str(data.get("description", "")).strip()
    date_str = str(data.get("date", ref.isoformat())).strip()

    if category not in ALLOWED_CATEGORIES:
        category = "otros"

    if not isinstance(amount, (int, float)):
        raise ValueError("amount inválido")

    parsed_date = date.fromisoformat(date_str)

    return {
        "amount": float(amount),
        "category": category,
        "description": description or "sin descripción",
        "date": parsed_date.isoformat(),
    }


def extract_expense(text: str) -> dict[str, Any]:
    """Parsea texto del usuario y devuelve dict con amount, category, description, date (YYYY-MM-DD)."""
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no está definida")

    genai.configure(api_key=api_key)
    ref = _reference_today()
    yesterday = ref - timedelta(days=1)

    user_prompt = (
        f"FECHA_REFERENCIA_HOY: {ref.isoformat()}\n"
        f"FECHA_AYER: {yesterday.isoformat()}\n\n"
        f"Mensaje del usuario:\n{text.strip()}"
    )

    gen_cfg = {
        "temperature": 0.1,
        "response_mime_type": "application/json",
    }

    chain = _model_chain()
    preferred = chain[0]
    last_error: BaseException | None = None
    for model_name in chain:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=gen_cfg,
                system_instruction=_SYSTEM_PROMPT,
            )
            response = model.generate_content(user_prompt)
            if not response.candidates:
                raise ValueError("Respuesta vacía o bloqueada por el modelo")
            raw = (response.text or "").strip()
            data = json.loads(raw)
            result = _payload_from_parsed(data, ref)
            if model_name != preferred:
                logger.info("Gemini OK con modelo fallback: %s", model_name)
            return result
        except _RETRY_EXCEPTIONS as e:
            last_error = e
            logger.warning("Gemini modelo %s no disponible o sin cuota: %s", model_name, e)
            continue
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning("Gemini modelo %s respuesta inválida: %s", model_name, e)
            continue

    msg = f"Ningún modelo de Gemini pudo procesar el gasto (probados: {chain})."
    if last_error:
        raise RuntimeError(msg) from last_error
    raise RuntimeError(msg)


def apply_cuotas_override(text: str, category: str) -> str:
    t = text.lower()
    if "cuota" in t or "visa" in t or "master" in t:
        return "cuotas"
    return category


def to_decimal_amount(amount: float) -> Decimal:
    return Decimal(str(amount)).quantize(Decimal("0.01"))
