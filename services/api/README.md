# QuFin API

FastAPI backend for QuFin: accounts, market snapshots and signals, macro scorecards, backtests
and the decision journal. Research and decision support, not investment advice.

This first version serves the same deterministic sample data as the web app's offline mock
(`apps/web/src/features/market/lib/mock-data.ts`), behind a data-access layer that real
connectors (FRED/ALFRED, CFTC, EIA, price vendors) will replace.

## Run it

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd services/api
uv sync
cp .env.example .env    # optional: every setting has a safe local default
uv run uvicorn app.main:app --reload --port 8000
```

Or start it from the repository root with one command, in any shell (PowerShell, cmd or bash):

```bash
uv run --directory services/api uvicorn app.main:app --reload --port 8000
```

Interactive docs: <http://localhost:8000/docs> (hidden when `QUFIN_ENVIRONMENT=production`).

To point the web app at it, set this in `apps/web/.env.local` and restart `npm run dev`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Without that variable the web app keeps using its built-in mock, which returns the same numbers.

> Behind a TLS-inspecting proxy, `uv sync` may fail with `invalid peer certificate`.
> Set `UV_SYSTEM_CERTS=1` so uv uses the Windows certificate store
> (PowerShell: `$env:UV_SYSTEM_CERTS = "1"`; bash: `export UV_SYSTEM_CERTS=1`).

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/v1/assets` | `AssetSnapshot[]`: price, 1-day change, regime, latest signal, walk-forward hit rate |
| `GET` | `/v1/assets/{symbol}` | `AssetDetail`: snapshot plus candles, signals and signal drivers; `404` if unknown |
| `GET` | `/v1/scorecards/countries` | `CountryScore[]`, strongest overall first |
| `POST` | `/v1/auth/sign-up` | Create an account and sign in (`201`); `409` if the email is taken |
| `POST` | `/v1/auth/sign-in` | Sign in; `401` with the same message for unknown email or wrong password |
| `POST` | `/v1/auth/sign-out` | End the session (`204`) |
| `GET` | `/v1/auth/me` | The signed-in user, or `401` |
| `POST` | `/v1/backtests` | Strategy or decision-rule backtest (see below). Signed in |
| `GET` | `/v1/decisions` | Your logged decisions, newest first. Signed in |
| `POST` | `/v1/decisions` | Log a decision; returns it with `id` and `createdAt` (`201`). Signed in |
| `DELETE` | `/v1/decisions/{id}` | `204`, or `404` if not found or not yours. Signed in |
| `GET` | `/v1/macro/series` | Macro series in the point-in-time store, with coverage |
| `GET` | `/v1/macro/series/{id}?asOf=&start=&end=` | The series as published on `asOf` (latest when omitted) |
| `GET` | `/v1/macro/series/{id}/revisions?period=` | Every published value of one period, first release first |

Market data and scorecards are public for now (sample data); they move behind sign-in when
licensed data arrives.

### Accounts and sessions

- Passwords: 12–128 characters, no composition rules (ASVS 2.1), hashed with Argon2id and
  re-hashed on sign-in when the parameters change.
- Sessions: a 256-bit random token in an `httpOnly`, `SameSite=Lax` cookie (`Secure` when
  `QUFIN_COOKIE_SECURE=true`). Only its SHA-256 digest is stored, it expires after
  `QUFIN_SESSION_TTL_HOURS`, is replaced on every sign-in and deleted on sign-out.
- Sign-in and sign-up are rate limited per IP and per email (`429` with `Retry-After`).
- Writes (`POST`/`DELETE`) carrying an `Origin` outside `QUFIN_CORS_ORIGINS` are refused with
  `403`, on top of the SameSite cookie and the CORS preflight.
- Browsers send the cookie because the web app calls the API with `credentials: 'include'`.
  `localhost:3000` and `localhost:8000` are the same site, so this works locally. In
  production, serve both from one registrable domain (e.g. `app.qufin.ai` and `api.qufin.ai`)
  and set `QUFIN_COOKIE_DOMAIN` if the web app needs to read the session server-side.

JSON uses camelCase, matching the TypeScript types in `apps/web/src/features/market/api/types.ts`
and the `Decision` type in `apps/web/src/features/journal/utils/store.ts`.

### Point-in-time macro data

Macro releases get revised, sometimes heavily. A backtest that uses today's revised numbers for
a decision made last year has look-ahead bias. The store therefore keeps every vintage, the way
ALFRED does: each row is one published value of one period, valid from `realtime_start` to
`realtime_end`. `asOf=2026-09-20` returns exactly what had been published by that day, and
`/revisions` shows how a figure changed from its first print.

Series come from FRED/ALFRED (St. Louis Fed). The tracked US series and the scorecard dimension
each informs are in `app/data/macro_catalog.py`. To load them you need a free FRED API key
(<https://fred.stlouisfed.org/docs/api/api_key.html>), set as `QUFIN_FRED_API_KEY` in `.env`:

```bash
uv run python -m app.cli ingest-fred                      # the whole catalog, since 2000
uv run python -m app.cli ingest-fred UNRATE CPIAUCSL --start 2015-01-01
```

Each run reloads the full vintage history of each series in one transaction, so it is safe to
repeat; schedule it daily once deployed. The client trusts the operating system's certificate
store (`truststore`), so it works behind a TLS-inspecting proxy that the machine trusts. The key
never appears in logs or error messages.

### Backtests

`POST /v1/backtests` takes a `kind` and the symbol; the server looks up the series itself.

```json
{ "kind": "strategy", "symbol": "EURUSD", "strategy": "all-signals",
  "minEdge": 0.05, "rebalanceDays": 5, "costBps": 3, "lookbackDays": 504 }
```

```json
{ "kind": "decision-rule", "symbol": "XAUUSD", "direction": "long",
  "stopPct": 0.01, "targetPct": 0.02, "maxHoldDays": 10, "minEdge": 0.05, "costBps": 2 }
```

The maths is a port of `apps/web/src/features/backtest/lib/engine.ts`: signals formed at day
_t_'s close act on day _t+1_ (no look-ahead), costs are charged on every position change, and
when a bar touches both stop and target the stop is assumed first. One difference from the
TypeScript result: `profitFactor` is `null` (not `Infinity`, which JSON cannot carry) when there
are winning trades and no losing ones.

## Configuration

Settings come from `QUFIN_*` environment variables or a local `.env` (never committed). See
`.env.example`.

| Variable | Default | Notes |
| --- | --- | --- |
| `QUFIN_ENVIRONMENT` | `development` | `production` hides `/docs` and `/openapi.json` |
| `QUFIN_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated; `*` is rejected |
| `QUFIN_DATABASE_URL` | `sqlite:///./qufin.db` | SQLite locally; `postgresql+psycopg://…` for Postgres |
| `QUFIN_AUTO_MIGRATE` | `true` | Apply migrations on startup; set `false` where deploys run them |
| `QUFIN_FRED_API_KEY` | unset | Needed only for `ingest-fred` |
| `QUFIN_SESSION_TTL_HOURS` | `168` | Session lifetime (1–720) |
| `QUFIN_COOKIE_SECURE` | `false` | Must be `true` over HTTPS; required in production |
| `QUFIN_COOKIE_DOMAIN` | unset | Parent domain when the web app and API are on subdomains |
| `QUFIN_AUTH_RATE_LIMIT` | `10` | Sign-in/sign-up attempts per IP and per email in each window |
| `QUFIN_AUTH_RATE_WINDOW_SECONDS` | `900` | Rate-limit window |

### Database and migrations

The schema is owned by Alembic (`migrations/`). The API applies pending migrations on startup
unless `QUFIN_AUTO_MIGRATE=false`; you can also run them yourself:

```bash
uv run alembic upgrade head            # or: uv run python -m app.cli migrate
uv run alembic revision --autogenerate -m "describe the change"   # after changing models
```

A local `qufin.db` created before migrations existed is adopted automatically (stamped at
revision `0001`, then upgraded), so existing accounts and decisions are kept.

For Postgres 16 with TimescaleDB, `compose.yaml` starts one locally:

```bash
docker compose up -d     # needs POSTGRES_PASSWORD set in your shell first
```

then set `QUFIN_DATABASE_URL=postgresql+psycopg://qufin:<password>@localhost:5432/qufin`.

## Layout

```
app/
  main.py            app factory: CORS, origin check, security headers, routers
  schemas/           Pydantic v2 request/response models (camelCase on the wire)
  data/repository.py MarketRepository protocol + the sample implementation
  data/sample.py     port of the web app's deterministic generator
  domain/            snapshots, regime, hit rate; backtest engine
  data/macro_catalog.py  macro series QuFin tracks, by country and scorecard dimension
  core/              settings, auth dependencies, password/token security, rate limiting
  connectors/        external data sources (FRED/ALFRED)
  jobs/              ingestion jobs
  stores/            users, sessions, decisions and point-in-time macro data (SQLAlchemy)
  routes/            HTTP endpoints
  cli.py             `migrate` and `ingest-fred` commands
migrations/          Alembic revisions
tests/               pytest, including parity with the TypeScript code
scripts/             web-parity-fixture.mts
```

To plug in real data, implement `MarketRepository` (in `app/data/repository.py`) and return it
from `get_market_repository`. Routes and domain code do not change.

## Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

`tests/test_web_parity.py` checks that the API serves the same numbers as the web app's mock
and backtest engine, using a fixture generated from the TypeScript code. Regenerate it when
`mock-data.ts` or `engine.ts` change (Node 23.6+ runs the `.mts` file directly):

```bash
node scripts/web-parity-fixture.mts > tests/fixtures/web_parity.json
```

Floats match to about 1e-12 relative; the last bit of `log`/`exp`/`cos` can differ between
Python and V8.

## Not yet

- Scorecards computed from the point-in-time macro store instead of sample data
- CFTC positioning and EIA energy connectors; non-US macro sources
- A scheduler for daily ingestion; TimescaleDB hypertables once price data is stored
- Email verification, password reset and MFA; a breached-password check on sign-up
- Shared rate-limit store (Redis or the reverse proxy) once there is more than one worker
- The model service
