# Scorecard versions

Rule 20: the scorecard recipe (which indicators enter each pillar, their directions, weights and
calibration) is proprietary and lives in a private methodology. Every change to it takes effect
only after the bias gate (S7), a point-in-time backtest and the QuFin owner's approval. This file is
the public record that those steps happened, without disclosing the recipe.

Each score served by the API carries `scorecardVersion` (below) and `catalogVersion` (a hash of
what the catalog declared for the scored indicators and of every source decision, provisional ones
included). `uv run python -m app.cli catalog-version` prints both. Every distinct live score shown
to users is kept with both versions in `score_snapshots`.

| Version | Date | What changed (no recipe) | Private methodology commit | S7 bias gate | Owner approval |
|---|---|---|---|---|---|
| 2026.11.1 | 19 Nov 2026 | First versioned recipe: the five-pillar US scorecard as it stood | `ec2d0ba` (private repository QuFin-Research/QuFin_Private, folder `private/`) | Passed 19 Nov 2026: 175 months, 2012-01 to 2026-07, every mean difference within ±0.03 (limit ±0.25) | Approved By: Haroon & Date: 19 Nov 2026 |

The S7 gate is the point-in-time backtest of the scorecard against complete information
(`scorecard-bias`); no separate strategy backtest was run for this baseline.

Open, for the owner: write the approval for each version in the last column. Until then the row
is a baseline, not an approval.

Source changes do not change the scorecard version. They change the catalog version, are recorded as
source decisions (`uv run python -m app.cli source-history`), and never alter a past score: as of an
earlier date the series that served the pair then is read (rules 16 and 38).
