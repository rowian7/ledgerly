"""Create a demo user with six months of realistic transactions.

python seed_demo.py          # user: demo / password: demo-password
"""

import random
from datetime import date

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Transaction, User
from app.months import shift_month
from app.security import hash_password

USERNAME, PASSWORD = "demo", "demo-password"

# (category, min, max, times per month)
EXPENSES = [
    ("Rent", 950, 950, 1),
    ("Groceries", 25, 90, 6),
    ("Transport", 3, 40, 8),
    ("Eating out", 12, 55, 4),
    ("Bills", 40, 120, 3),
    ("Fun", 10, 80, 3),
]


def main() -> None:
    Base.metadata.create_all(engine)
    rng = random.Random(42)
    with SessionLocal() as db:
        old = db.scalar(select(User).where(User.username == USERNAME))
        if old:
            db.delete(old)
            db.commit()
        user = User(username=USERNAME, hashed_password=hash_password(PASSWORD))
        db.add(user)
        db.flush()

        this_month = date.today().replace(day=1)
        for back in range(5, -1, -1):
            start = shift_month(this_month, -back)
            last_day = 28 if back else min(date.today().day, 28)
            db.add(
                Transaction(
                    user_id=user.id,
                    kind="income",
                    amount_cents=245000,
                    category="Salary",
                    description="Monthly pay",
                    date=start,
                )
            )
            for cat, lo, hi, n in EXPENSES:
                for _ in range(n):
                    db.add(
                        Transaction(
                            user_id=user.id,
                            kind="expense",
                            amount_cents=rng.randint(lo * 100, hi * 100),
                            category=cat,
                            description="",
                            date=start.replace(day=rng.randint(1, last_day)),
                        )
                    )
        db.commit()
    print(f"Seeded demo data. Log in as {USERNAME} / {PASSWORD}")


if __name__ == "__main__":
    main()
