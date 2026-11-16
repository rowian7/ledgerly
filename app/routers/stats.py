from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.money import cents_to_money
from app.months import parse_month, shift_month
from app.schemas import CategoryTotal, MonthSummary, MonthTotal
from app.security import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary", response_model=MonthSummary)
def month_summary(
    month: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Income, expenses and spending-by-category for one month."""
    start, end = parse_month(month)
    in_month = (
        Transaction.user_id == user.id,
        Transaction.date >= start,
        Transaction.date < end,
    )

    totals = dict(
        db.execute(
            select(Transaction.kind, func.sum(Transaction.amount_cents))
            .where(*in_month)
            .group_by(Transaction.kind)
        ).all()
    )
    by_cat = db.execute(
        select(Transaction.category, func.sum(Transaction.amount_cents).label("total"))
        .where(*in_month, Transaction.kind == "expense")
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount_cents).desc())
    ).all()

    income, expenses = cents_to_money(totals.get("income")), cents_to_money(totals.get("expense"))
    return MonthSummary(
        month=month,
        income=income,
        expenses=expenses,
        net=income - expenses,
        by_category=[CategoryTotal(category=c, amount=cents_to_money(t)) for c, t in by_cat],
    )


@router.get("/monthly", response_model=list[MonthTotal])
def monthly_totals(
    months: int = Query(6, ge=1, le=24),
    until: str | None = Query(None, description="Last month to include, YYYY-MM (default: this month)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Income vs expenses for each of the last N months (oldest first, gaps filled with 0)."""
    last_start = parse_month(until)[0] if until else date.today().replace(day=1)
    first = shift_month(last_start, -(months - 1))
    end = shift_month(last_start, 1)

    # Group by (year, month) in Python rather than with a DB-specific date function,
    # so the same code works on SQLite and Postgres.
    rows = db.execute(
        select(Transaction.date, Transaction.kind, Transaction.amount_cents).where(
            Transaction.user_id == user.id, Transaction.date >= first, Transaction.date < end
        )
    ).all()
    lookup: dict[tuple[str, str], int] = {}
    for d, kind, cents in rows:
        key = (d.strftime("%Y-%m"), kind)
        lookup[key] = lookup.get(key, 0) + cents

    out = []
    for i in range(months):
        key = shift_month(first, i).strftime("%Y-%m")
        out.append(
            MonthTotal(
                month=key,
                income=cents_to_money(lookup.get((key, "income"))),
                expenses=cents_to_money(lookup.get((key, "expense"))),
            )
        )
    return out
