"""Which scorecard and catalog a score was computed with (rule 20).

A score is only reproducible if it says what built it. Two identifiers travel with every score:

- `SCORECARD_VERSION`: the recipe (indicators, directions, weights, constants). It changes only
  when the recipe does, after the bias gate, a point-in-time backtest and the owner's approval,
  and each change is recorded in `docs/scorecard-versions.md`.
- the catalog version: a short hash of what the catalog declares for the scored indicators (source,
  change kind, adjustment, variant) and of every source decision, provisional ones included.
  It changes when a source changes or a change kind is re-declared, so a score computed before
  that is recognisably a different version.
"""

import hashlib
import json

from sqlalchemy.orm import Session

from app.data.macro_catalog import BY_ID
from app.data.scorecard_catalog import SCORED
from app.data.series_variants import variant_of
from app.stores.source_decisions import SourceStore

SCORECARD_VERSION = "2026.11.1"


def catalog_version(session: Session) -> str:
    declared = []
    for series_id in sorted(SCORED):
        entry = BY_ID[series_id]
        declared.append(
            [
                series_id,
                entry.source,
                entry.change,
                entry.published_as_change,
                variant_of(series_id, entry.country),
            ]
        )
    decisions = [
        [
            d.country,
            d.concept,
            d.series_id,
            d.source,
            d.effective_from.isoformat(),
            d.effective_to.isoformat() if d.effective_to else None,
            d.status,
        ]
        for d in SourceStore(session).all()
    ]
    blob = json.dumps({"declared": declared, "decisions": decisions}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]
