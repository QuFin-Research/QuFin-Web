# ADR 0006: Cloud region and data residency

**Status:** Proposed; decision needed from the founder (1 Nov 2026)

## Context
The Terraform skeleton defaults to `eu-west-1` as a placeholder. Users are expected in the GCC,
the UK, the EU and the US; Saudi Arabia's PDPL and GDPR both affect where personal data may be
stored.

## Options
1. **me-central-1 (UAE)** or **me-south-1 (Bahrain)**: close to GCC users; check PDPL transfer
   rules and service availability (e.g. managed TimescaleDB options).
2. **eu-west-1 (Ireland)** or **eu-central-1 (Frankfurt)**: GDPR-friendly, full service range.
3. **Split:** personal data in the users' region, market and macro data (not personal) wherever is
   cheapest.

## Needed
Counsel's view on PDPL and GDPR (P0-13, P0-16) before the AWS accounts are created (P0-09).
