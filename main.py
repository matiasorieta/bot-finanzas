import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from xml.sax.saxutils import escape

from fastapi import FastAPI, Form, Response
from fastapi.responses import PlainTextResponse

from ai import apply_cuotas_override, extract_expense, to_decimal_amount
from crud import create_expense
from db import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("DATABASE_URL"):
        init_db()
    yield


app = FastAPI(title="Bot Finanzas — Twilio Webhook", lifespan=lifespan)


def _twiml_message(body: str) -> str:
    safe = escape(body, {"'": "&apos;", '"': "&quot;"})
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{safe}</Message>"
        "</Response>"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def twilio_webhook(
    Body: str | None = Form(default=None),
    From: str | None = Form(default=None),
):
    text = (Body or "").strip()
    if not text:
        return PlainTextResponse(
            _twiml_message("No entendí el gasto"),
            media_type="application/xml",
        )

    try:
        parsed = extract_expense(text)
        category = apply_cuotas_override(text, parsed["category"])
        expense_date = date.fromisoformat(parsed["date"])
        amount_dec = to_decimal_amount(parsed["amount"])

        db = SessionLocal()
        try:
            create_expense(
                db,
                amount=amount_dec,
                category=category,
                description=parsed["description"],
                expense_date=expense_date,
            )
        finally:
            db.close()

        msg = f"Guardado: ${float(amount_dec)} en {category}"
        return PlainTextResponse(_twiml_message(msg), media_type="application/xml")
    except Exception as e:
        logger.exception("Error procesando gasto: %s", e)
        return PlainTextResponse(
            _twiml_message("No entendí el gasto"),
            media_type="application/xml",
        )


@app.get("/")
def root():
    return Response(content="POST /webhook para Twilio", media_type="text/plain")
