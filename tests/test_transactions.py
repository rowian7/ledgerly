from tests.conftest import make_user


def tx(**overrides):
    body = {
        "kind": "expense",
        "amount": "12.50",
        "category": "groceries",
        "description": "Weekly shop",
        "date": "2026-03-14",
    }
    return {**body, **overrides}


def test_create_and_list(client, auth):
    r = client.post("/api/transactions", json=tx(), headers=auth)
    assert r.status_code == 201
    created = r.json()
    assert created["amount"] == "12.50"
    assert created["category"] == "Groceries"  # normalised

    r = client.get("/api/transactions", headers=auth)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["id"] == created["id"]


def test_money_has_no_float_rounding_errors(client, auth):
    for amount in ["0.10", "0.20"]:
        client.post("/api/transactions", json=tx(amount=amount), headers=auth)
    summary = client.get("/api/stats/summary?month=2026-03", headers=auth).json()
    assert summary["expenses"] == "0.30"  # 0.1 + 0.2 != 0.3 with floats


def test_filters(client, auth):
    client.post("/api/transactions", json=tx(date="2026-03-01"), headers=auth)
    client.post("/api/transactions", json=tx(date="2026-04-01"), headers=auth)
    salary = tx(kind="income", category="Salary", date="2026-03-31")
    client.post("/api/transactions", json=salary, headers=auth)

    march = client.get("/api/transactions?month=2026-03", headers=auth).json()
    assert march["total"] == 2
    assert [t["date"] for t in march["items"]] == ["2026-03-31", "2026-03-01"]  # newest first

    income = client.get("/api/transactions?kind=income", headers=auth).json()
    assert income["total"] == 1

    groceries = client.get("/api/transactions?category=GROCERIES", headers=auth).json()
    assert groceries["total"] == 2


def test_pagination(client, auth):
    for day in range(1, 6):
        client.post("/api/transactions", json=tx(date=f"2026-03-0{day}"), headers=auth)
    page = client.get("/api/transactions?limit=2&offset=2", headers=auth).json()
    assert page["total"] == 5
    assert [t["date"] for t in page["items"]] == ["2026-03-03", "2026-03-02"]


def test_update_and_delete(client, auth):
    tx_id = client.post("/api/transactions", json=tx(), headers=auth).json()["id"]

    r = client.put(f"/api/transactions/{tx_id}", json=tx(amount="99.99", category="Fun"), headers=auth)
    assert r.status_code == 200
    assert r.json()["amount"] == "99.99"
    assert r.json()["category"] == "Fun"

    assert client.delete(f"/api/transactions/{tx_id}", headers=auth).status_code == 204
    assert client.get(f"/api/transactions/{tx_id}", headers=auth).status_code == 404


def test_users_cannot_see_or_touch_each_others_data(client, auth):
    tx_id = client.post("/api/transactions", json=tx(), headers=auth).json()["id"]
    mallory = make_user(client, "mallory", "password123")

    assert client.get(f"/api/transactions/{tx_id}", headers=mallory).status_code == 404
    assert client.put(f"/api/transactions/{tx_id}", json=tx(), headers=mallory).status_code == 404
    assert client.delete(f"/api/transactions/{tx_id}", headers=mallory).status_code == 404
    assert client.get("/api/transactions", headers=mallory).json()["total"] == 0


def test_validation(client, auth):
    assert client.post("/api/transactions", json=tx(amount="-5"), headers=auth).status_code == 422
    assert client.post("/api/transactions", json=tx(amount="1.234"), headers=auth).status_code == 422
    assert client.post("/api/transactions", json=tx(kind="gift"), headers=auth).status_code == 422
    assert client.post("/api/transactions", json=tx(category="   "), headers=auth).status_code == 422
    assert client.get("/api/transactions?month=2026-13", headers=auth).status_code == 422


def test_csv_export(client, auth):
    client.post("/api/transactions", json=tx(description='Milk, "fresh"'), headers=auth)
    r = client.get("/api/transactions/export.csv?month=2026-03", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0] == "date,kind,category,amount,description"
    assert lines[1] == '2026-03-14,expense,Groceries,12.50,"Milk, ""fresh"""'
