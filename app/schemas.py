from datetime import date as Date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.money import cents_to_money

Kind = Literal["income", "expense"]


# ---------- auth ----------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- transactions ----------
class TransactionIn(BaseModel):
    kind: Kind
    amount: Decimal = Field(gt=0, le=Decimal("10000000"), decimal_places=2)
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=200)
    date: Date

    @field_validator("category")
    @classmethod
    def normalise_category(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("category must not be blank")
        return v.capitalize()


class TransactionOut(BaseModel):
    id: int
    kind: Kind
    amount: Decimal
    category: str
    description: str
    date: Date

    @classmethod
    def from_model(cls, t) -> "TransactionOut":
        return cls(
            id=t.id,
            kind=t.kind,
            amount=cents_to_money(t.amount_cents),
            category=t.category,
            description=t.description,
            date=t.date,
        )


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int


# ---------- stats ----------
class CategoryTotal(BaseModel):
    category: str
    amount: Decimal


class MonthSummary(BaseModel):
    month: str  # YYYY-MM
    income: Decimal
    expenses: Decimal
    net: Decimal
    by_category: list[CategoryTotal]


class MonthTotal(BaseModel):
    month: str
    income: Decimal
    expenses: Decimal
