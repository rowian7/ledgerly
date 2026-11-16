from app.months import parse_month, shift_month


def add(client, auth, kind, amount, category, date):
    r = client.post(
        "/api/transactions",
        json={"kind": kind, "amount": amount, "category": category, "date": date},
        headers=auth,
    )
    assert r.status_code == 201


def test_month_summary(client, auth):
    add(client, auth, "income", "2000.00", "Salary", "2026-03-01")
    add(client, auth, "expense", "800.00", "Rent", "2026-03-02")
    add(client, auth, "expense", "45.20", "Groceries", "2026-03-05")
    add(client, auth, "expense", "30.00", "Groceries", "2026-03-20")
    add(client, auth, "expense", "999.00", "Rent", "2026-04-01")  # different month

    s = client.get("/api/stats/summary?month=2026-03", headers=auth).json()
    assert s["income"] == "2000.00"
    assert s["expenses"] == "875.20"
    assert s["net"] == "1124.80"
    assert s["by_category"] == [
        {"category": "Rent", "amount": "800.00"},
        {"category": "Groceries", "amount": "75.20"},
    ]


def test_empty_month_summary(client, auth):
    s = client.get("/api/stats/summary?month=2026-01", headers=auth).json()
    assert s["income"] == s["expenses"] == s["net"] == "0.00"
    assert s["by_category"] == []


def test_monthly_trend_fills_gaps_and_crosses_year_boundary(client, auth):
    add(client, auth, "expense", "10.00", "Fun", "2025-11-10")
    add(client, auth, "income", "50.00", "Gift", "2026-01-15")

    rows = client.get("/api/stats/monthly?months=4&until=2026-01", headers=auth).json()
    assert [r["month"] for r in rows] == ["2025-10", "2025-11", "2025-12", "2026-01"]
    assert rows[1]["expenses"] == "10.00"
    assert rows[2]["expenses"] == "0.00"
    assert rows[3]["income"] == "50.00"


def test_month_helpers():
    from datetime import date

    assert parse_month("2026-12") == (date(2026, 12, 1), date(2027, 1, 1))
    assert shift_month(date(2026, 1, 31), -1) == date(2025, 12, 1)
    assert shift_month(date(2026, 11, 5), 3) == date(2027, 2, 1)
