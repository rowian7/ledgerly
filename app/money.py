from decimal import Decimal


def cents_to_money(cents: int | None) -> Decimal:
    """1250 -> Decimal('12.50'). Always two decimal places, never a float."""
    return Decimal(cents or 0).scaleb(-2)


def money_to_cents(amount: Decimal) -> int:
    return int(amount.scaleb(2))
