import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.money import cents_to_money, money_to_cents
from app.months import parse_month
from app.schemas import Kind, TransactionIn, TransactionOut, TransactionPage
from app.security import get_current_user

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _to_cents(body: TransactionIn) -> int:
    return money_to_cents(body.amount)


def _get_owned(db: Session, user: User, tx_id: int) -> Transaction:
    tx = db.get(Transaction, tx_id)
    # Return 404 (not 403) for other users' rows so their existence isn't leaked.
    if tx is None or tx.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    return tx


def _filtered(user: User, month: str | None, kind: Kind | None, category: str | None):
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    if month:
        start, end = parse_month(month)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    if kind:
        stmt = stmt.where(Transaction.kind == kind)
    if category:
        stmt = stmt.where(func.lower(Transaction.category) == category.strip().lower())
    return stmt


@router.get("", response_model=TransactionPage)
def list_transactions(
    month: str | None = None,
    kind: Kind | None = None,
    category: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = _filtered(user, month, kind, category)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).offset(offset)
    ).all()
    return TransactionPage(items=[TransactionOut.from_model(t) for t in rows], total=total)


@router.get("/export.csv")
def export_csv(
    month: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(_filtered(user, month, None, None).order_by(Transaction.date)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "kind", "category", "amount", "description"])
    for t in rows:
        amount = cents_to_money(t.amount_cents)
        writer.writerow([t.date.isoformat(), t.kind, t.category, amount, t.description])
    filename = f"ledgerly-{month or 'all'}.csv"
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = Transaction(
        user_id=user.id,
        kind=body.kind,
        amount_cents=_to_cents(body),
        category=body.category,
        description=body.description,
        date=body.date,
    )
    db.add(tx)
    db.commit()
    return TransactionOut.from_model(tx)


@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TransactionOut.from_model(_get_owned(db, user, tx_id))


@router.put("/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: int,
    body: TransactionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = _get_owned(db, user, tx_id)
    tx.kind = body.kind
    tx.amount_cents = _to_cents(body)
    tx.category = body.category
    tx.description = body.description
    tx.date = body.date
    db.commit()
    return TransactionOut.from_model(tx)


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get_owned(db, user, tx_id))
    db.commit()
