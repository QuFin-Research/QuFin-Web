# QuFin API

FastAPI backend for QuFin: market snapshots and signals, macro scorecards, backtests and the
decision journal. Research and decision support, not investment advice.

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

Interactive docs: <http://localhost:8000/docs> (hidden when `QUFIN_ENVIRONMENT=production`).

To point the web app at it, set this in `apps/web/.env.local` and restart `npm run dev`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Without that variable the web app keeps using its built-in mock, which returns the same numbers.

> Behind a TLS-inspecting proxy, `uv sync` may fail with `invalid peer certificate`.
> Set `UV_SYSTEM_CERTS=1` so uv uses the Windows certificate store.

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/v1/assets` | `AssetSnapshot[]`: price, 1-day change, regime, latest signal, walk-forward hit rate |
| `GET` | `/v1/assets/{symbol}` | `AssetDetail`: snapshot plus candles, signals and signal drivers; `404` if unknown |
| `GET` | `/v1/scorecards/countries` | `CountryScore[]`, strongest overall first |
| `POST` | `/v1/backtests` | Strategy or decision-rule backtest (see below) |
| `GET` | `/v1/decisions` | Logged decisions, newest first |
| `POST` | `/v1/decisions` | Log a decision; returns it with `id` and `createdAt` (`201`) |
| `DELETE` | `/v1/decisions/{id}` | `204`, or `404` if not found |

JSON uses camelCase, matching the TypeScript types in `apps/web/src/features/market/api/types.ts`
and the `Decision` type in `apps/web/src/features/journal/utils/store.ts`.

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
| `QUFIN_DATABASE_URL` | `sqlite:///./qufin.db` | Decision journal store; Postgres 16 later |

## Layout

```
app/
  main.py            app factory: CORS, security headers, routers
  core/config.py     pydantic-settings
  schemas/           Pydantic v2 request/response models (camelCase on the wire)
  data/repository.py MarketRepository protocol + the sample implementation
  data/sample.py     port of the web app's deterministic generator
  domain/            snapshots, regime, hit rate; backtest engine
  stores/            decision journal (SQLAlchemy)
  routes/            HTTP endpoints
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

- Authentication, and decisions scoped to a user (needed before this is exposed publicly)
- Postgres/TimescaleDB, migrations (Alembic) and point-in-time macro storage
- Real data connectors and the model service
- Rate limiting
