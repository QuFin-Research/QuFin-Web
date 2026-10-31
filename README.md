# QuFin-Web

Web platform for **QuFin**, an AI trading-intelligence companion for FX, metals, energy and crypto.

## Repository layout

| Path | What it is |
|---|---|
| `apps/web` | Next.js 16 web app: public landing page and the research dashboard |
| `services/api` | *(Phase 1)* FastAPI backend: data APIs, signals, backtests, auth |
| `apps/mobile` | *(later)* Expo React Native app sharing the same API |

## Run the web app

Requires Node.js 22 or newer.

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000.

## What is in `apps/web` today

- **Landing page** (`/`): hero, features, how it works, pricing tiers (placeholder prices).
- **Overview** (`/dashboard/overview`): KPIs, today's signals ranked by conviction, macro scorecard.
- **Asset workspace** (`/dashboard/markets/[symbol]`): candlestick chart with signal markers,
  signal drivers, and the **decision panel**: plan entry/stop/target/size, **backtest that decision**
  on history, and log it.
- **Backtest lab** (`/dashboard/backtest`): follow-signals / high-conviction / buy-and-hold strategies
  with costs, equity curve, drawdown, Sharpe, hit rate.
- **Decision journal** (`/dashboard/journal`): every logged decision marked to the latest close, with
  the backtest seen at entry.

All data is **deterministic sample data** (`src/features/market/lib/mock-data.ts`). Each feature's
`api/service.ts` is the only file to change when the FastAPI endpoints exist. The journal is stored in
the browser until the decisions API and auth are in place.

## Built on

- [next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) (MIT): app shell,
  shadcn/ui components, data-table, theming. Clerk, Sentry and demo pages removed with its cleanup script.
- [Tremor](https://tremor.so) patterns: KPI cards, diverging bar list, Recharts-based charts.
- [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) (Apache-2.0): price chart.
  The TradingView attribution logo must stay visible.
- [Next.js SaaS Starter](https://github.com/nextjs/saas-starter): reference for the landing/pricing structure;
  Stripe checkout and auth are Phase 1 work.

## Not investment advice

QuFin provides research and decision-support tools. Backtested results do not guarantee future returns.
