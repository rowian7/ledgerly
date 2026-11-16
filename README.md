# Ledgerly

A personal finance tracker. Log income and expenses, see where your money goes each month, and export your data as CSV.

Built with **Python, FastAPI, SQLAlchemy 2.0 and Pydantic v2** on the backend and a dependency-free **vanilla JavaScript** frontend with Chart.js.

<!-- Add a screenshot: docs/screenshot.png -->

## Features

- Account registration and login with **bcrypt** password hashing and **JWT** bearer tokens
- Create, edit, delete and filter transactions (by month, type, category) with pagination
- Monthly dashboard: income / expenses / net, spending-by-category doughnut, 6-month income-vs-expense trend
- CSV export (correctly escapes commas and quotes)
- Strict per-user data isolation: other users' records return 404, not 403, so their existence isn't leaked
- Auto-generated interactive API docs at `/docs` (OpenAPI)
- 17 automated tests, linting with Ruff, GitHub Actions CI across Python 3.11–3.13, Docker image

## Design decisions

| Decision | Why |
|---|---|
| Money stored as **integer cents**, exposed as `Decimal` strings | Floats can't represent 0.10 exactly; `0.1 + 0.2 != 0.3`. There's a test for this. |
| Same error for "unknown user" and "wrong password" | Prevents username enumeration. |
| Dependency injection for the DB session and current user | Each request gets its own session; tests swap in an in-memory database with one line. |
| Monthly trend grouped in Python, not with SQL date functions | `strftime` is SQLite-only; this keeps the code portable to Postgres. |
| Frontend renders user text with `textContent`, never `innerHTML` | Prevents stored XSS from transaction descriptions. |
| Settings via environment variables (`pydantic-settings`) | Twelve-factor style; no secrets in code. |

## Project structure

```
app/
  main.py            FastAPI app, router wiring, static files
  config.py          Settings from env vars
  database.py        SQLAlchemy engine/session + get_db dependency
  models.py          User and Transaction ORM models
  schemas.py         Pydantic request/response models and validation
  security.py        Password hashing, JWT creation, get_current_user
  money.py, months.py  Small pure helpers (easy to unit test)
  routers/           auth, transactions, stats endpoints
  static/            index.html, app.js, styles.css
tests/               pytest suite (fresh in-memory DB per test)
seed_demo.py         Fills the DB with 6 months of demo data
```

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python seed_demo.py            # optional: demo / demo-password
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the app and http://localhost:8000/docs for the API docs.

### Tests and lint

```bash
pytest
ruff check . && ruff format --check .
```

### Docker

```bash
docker build -t ledgerly .
docker run -p 8000:8000 -e LEDGERLY_SECRET_KEY=$(openssl rand -hex 32) -v ledgerly-data:/data ledgerly
```

## Configuration

| Variable | Default | |
|---|---|---|
| `LEDGERLY_SECRET_KEY` | dev-only value | **Set this in production** (signs JWTs) |
| `LEDGERLY_DATABASE_URL` | `sqlite:///./ledgerly.db` | Any SQLAlchemy URL |
| `LEDGERLY_ACCESS_TOKEN_MINUTES` | `1440` | Token lifetime |

## API overview

| Method | Path | |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get a JWT |
| GET | `/api/auth/me` | Current user |
| GET | `/api/transactions?month=&kind=&category=&limit=&offset=` | List (paginated) |
| POST | `/api/transactions` | Create |
| GET / PUT / DELETE | `/api/transactions/{id}` | Read / update / delete |
| GET | `/api/transactions/export.csv?month=` | CSV download |
| GET | `/api/stats/summary?month=YYYY-MM` | Monthly totals + by category |
| GET | `/api/stats/monthly?months=6&until=YYYY-MM` | Income vs expenses trend |

## Possible next steps

- Database migrations with Alembic
- Monthly budgets per category with over-budget warnings
- Recurring transactions
- Refresh tokens / httpOnly cookie auth
- Deploy to Fly.io or Render with Postgres
