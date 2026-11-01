# Architecture decision records

One file per decision: context, decision, consequences, status. A decision changes only through a
new ADR that supersedes the old one (backlog task P0-08).

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-stack.md) | FastAPI (Python) API, Next.js web, Expo mobile, one monorepo | Accepted |
| [0002](0002-point-in-time-storage.md) | Every observation keeps its vintage; reads are as-of a date | Accepted |
| [0003](0003-orchestration.md) | Command-line jobs now, Dagster for schedules and release sensors | Accepted, Dagster pending |
| [0004](0004-accounts.md) | Own accounts in the API for now; managed identity before launch | Accepted (deviation) |
| [0005](0005-scorecard.md) | Rescaled weighted scorecard with separate confidence; 5 → 8 pillars | Accepted, 8 pillars pending |
| [0006](0006-cloud-region.md) | AWS region and data residency | Proposed, decision needed |
