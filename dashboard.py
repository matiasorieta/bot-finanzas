import os
from calendar import monthrange
from datetime import date


def _prepare_streamlit_port(default: str = "8501") -> None:
    """Evita STREAMLIT_SERVER_PORT / PORT inválidos (p. ej. el literal '$PORT')."""

    def ok(s: str) -> bool:
        if not s or s.startswith("$"):
            return False
        try:
            n = int(s)
            return 1 <= n <= 65535
        except ValueError:
            return False

    if not ok((os.environ.get("STREAMLIT_SERVER_PORT") or "").strip()):
        os.environ.pop("STREAMLIT_SERVER_PORT", None)

    port = (os.environ.get("PORT") or "").strip()
    os.environ["STREAMLIT_SERVER_PORT"] = port if ok(port) else default


_prepare_streamlit_port()

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from crud import (
    get_daily_spending,
    get_expenses_by_date_range,
    get_summary_by_category,
)
from db import SessionLocal, init_db


def main():
    st.set_page_config(page_title="Dashboard de Gastos", layout="wide")
    st.title("Dashboard de Gastos")

    if not os.environ.get("DATABASE_URL", "").strip():
        st.error("Definí la variable de entorno DATABASE_URL.")
        st.stop()

    try:
        init_db()
    except Exception as e:
        st.error(f"No se pudo conectar o inicializar la base de datos: {e}")
        st.stop()

    today = date.today()
    first_this_month = date(today.year, today.month, 1)

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Desde", value=first_this_month)
    with col2:
        end = st.date_input("Hasta", value=today)

    if start > end:
        st.warning("El rango de fechas es inválido.")
        st.stop()

    db = SessionLocal()
    try:
        _, last_day = monthrange(today.year, today.month)
        month_start = date(today.year, today.month, 1)
        month_end = date(today.year, today.month, last_day)

        month_rows = get_expenses_by_date_range(db, month_start, month_end)
        total_month = sum(float(r.amount) for r in month_rows)

        st.metric("Total gastado del mes actual", f"${total_month:,.2f}")

        st.subheader("Resumen en el rango seleccionado")

        rows = get_expenses_by_date_range(db, start, end)
        by_cat = get_summary_by_category(db, start, end)
        daily = get_daily_spending(db, start, end)

        if not by_cat.empty:
            by_cat = by_cat.copy()
            by_cat["total"] = by_cat["total"].astype(float)

        if not daily.empty:
            daily = daily.copy()
            daily["total"] = daily["total"].astype(float)

        c1, c2 = st.columns(2)
        with c1:
            st.write("**Gasto por categoría**")
            if by_cat.empty:
                st.info("No hay datos en este rango.")
            else:
                chart_df = by_cat.set_index("category")
                st.bar_chart(chart_df)

        with c2:
            st.write("**Gasto diario**")
            if daily.empty:
                st.info("No hay datos en este rango.")
            else:
                line_df = daily.set_index("date")
                st.line_chart(line_df)

        st.write("**Últimos gastos (ordenados por fecha descendente)**")
        if not rows:
            st.info("No hay gastos en este rango.")
        else:
            table = pd.DataFrame(
                [
                    {
                        "fecha": r.date.isoformat(),
                        "monto": float(r.amount),
                        "categoría": r.category,
                        "descripción": r.description,
                        "creado": r.created_at.isoformat() if r.created_at else "",
                    }
                    for r in rows
                ]
            )
            st.dataframe(table, use_container_width=True, hide_index=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
