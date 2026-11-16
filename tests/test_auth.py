def test_register_login_and_me(client):
    r = client.post("/api/auth/register", json={"username": "Bob", "password": "hunter2hunter2"})
    assert r.status_code == 201
    assert r.json()["username"] == "bob"  # usernames are case-insensitive

    r = client.post("/api/auth/login", json={"username": "BOB", "password": "hunter2hunter2"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "bob"


def test_duplicate_username_rejected(client):
    body = {"username": "carol", "password": "password123"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409


def test_wrong_password_and_unknown_user_look_the_same(client):
    client.post("/api/auth/register", json={"username": "dave", "password": "password123"})
    wrong = client.post("/api/auth/login", json={"username": "dave", "password": "nope-nope-nope"})
    missing = client.post("/api/auth/login", json={"username": "ghost", "password": "password123"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"username": "erin", "password": "short"})
    assert r.status_code == 422


def test_protected_routes_need_a_valid_token(client):
    assert client.get("/api/transactions").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/transactions", headers=bad).status_code == 401
