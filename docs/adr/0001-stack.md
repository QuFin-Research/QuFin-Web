# ADR 0001: Stack

**Status:** Accepted (1 Nov 2026)

## Context
QuFin is data first: point-in-time storage, connectors, statistics and models. Web, iOS, Android
and institutional clients must share one contract (Blueprint sections 08-09).

## Decision
- **API:** Python 3.12+, FastAPI, Pydantic v2 (camelCase on the wire, unknown fields rejected),
  SQLAlchemy 2.0 with Alembic migrations, OpenAPI as the contract. Python because the data and
  model libraries (pandas, statsmodels, LightGBM, sdmx1) are strongest there.
- **Web:** Next.js 16 (App Router) on Node.js, TypeScript, shadcn/ui on Base UI, Tailwind,
  TanStack Query and Form with Zod, Recharts.
- **Mobile:** Expo (React Native), sharing the design system and typed API client (Phase 5).
- **Repository:** one monorepo: `apps/web`, `apps/mobile`, `services/api`, `data`, `ml`, `infra`.
- **Quality:** ruff, mypy and pytest for Python; tsc and oxlint for TypeScript; CI on every PR;
  gitleaks, CodeQL and Dependabot.

## Consequences
Two runtimes (Python, Node.js) talking over HTTP. The API is the only path to data for every
client, so rules on data origin, freshness and point-in-time reads are enforced once, in the API.
