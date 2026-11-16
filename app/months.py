"""Helpers for working with calendar months written as 'YYYY-MM'."""

import re
from datetime import date

from fastapi import HTTPException

_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def parse_month(month: str) -> tuple[date, date]:
    """Return (first day of month, first day of next month) for a 'YYYY-MM' string."""
    m = _MONTH_RE.match(month)
    if not m:
        raise HTTPException(422, "month must look like YYYY-MM")
    year, mon = int(m.group(1)), int(m.group(2))
    start = date(year, mon, 1)
    end = date(year + (mon == 12), mon % 12 + 1, 1)
    return start, end


def shift_month(d: date, delta: int) -> date:
    """First day of the month `delta` months away from d's month."""
    idx = d.year * 12 + (d.month - 1) + delta
    return date(idx // 12, idx % 12 + 1, 1)
