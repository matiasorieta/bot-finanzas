from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Expense


def create_expense(
    db: Session,
    *,
    amount: Decimal | float,
    category: str,
    description: str,
    expense_date: date,
) -> Expense:
    row = Expense(
        amount=amount,
        category=category,
        description=description,
        date=expense_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_expenses(db: Session, limit: int = 500) -> list[Expense]:
    stmt = select(Expense).order_by(Expense.date.desc(), Expense.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def get_expenses_by_date_range(
    db: Session,
    start: date,
    end: date,
    limit: int = 2000,
) -> list[Expense]:
    stmt = (
        select(Expense)
        .where(Expense.date >= start, Expense.date <= end)
        .order_by(Expense.date.desc(), Expense.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_summary_by_category(
    db: Session,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    stmt = select(Expense.category, func.sum(Expense.amount).label("total"))
    if start is not None:
        stmt = stmt.where(Expense.date >= start)
    if end is not None:
        stmt = stmt.where(Expense.date <= end)
    stmt = stmt.group_by(Expense.category).order_by(func.sum(Expense.amount).desc())
    rows = db.execute(stmt).all()
    if not rows:
        return pd.DataFrame(columns=["category", "total"])
    return pd.DataFrame(rows, columns=["category", "total"])


def get_daily_spending(
    db: Session,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    stmt = select(Expense.date, func.sum(Expense.amount).label("total"))
    if start is not None:
        stmt = stmt.where(Expense.date >= start)
    if end is not None:
        stmt = stmt.where(Expense.date <= end)
    stmt = stmt.group_by(Expense.date).order_by(Expense.date.asc())
    rows = db.execute(stmt).all()
    if not rows:
        return pd.DataFrame(columns=["date", "total"])
    df = pd.DataFrame(rows, columns=["date", "total"])
    df["date"] = pd.to_datetime(df["date"])
    return df
