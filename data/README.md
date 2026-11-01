# Data platform

Where the data platform grows as it leaves `services/api` (Blueprint sections 03-04):

- connectors and their tests move here once orchestration (Dagster) runs them;
- the raw zone (immutable source files) lives under `QUFIN_RAW_DIR` locally and in S3 later;
- the series registry and licence register are in `docs/`.

Today the connectors, point-in-time store and checks live in `services/api/app`
(`connectors/`, `stores/`, `jobs/`), driven by `python -m app.cli`.
