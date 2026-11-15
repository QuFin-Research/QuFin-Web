"""What users may be told about how a scorecard is built, decided by QuFin (rule 20).

The summary is always shown: it describes what a score is and what stands behind it, never how it
is weighted. The mechanism (weights, formulas, assumptions) is shown only when QuFin chooses to
disclose it (setting `scorecard_mechanism`). Hiding the mechanism never hides where the data comes
from, how fresh it is, the confidence in a score, or the releases still to come.
"""

from app.data.scorecard_catalog import SCORED
from app.domain.scorecard import HISTORY_YEARS, MOMENTUM_WEIGHT, PILLARS, SCORE_LIMIT

SUMMARY: dict[str, str | list[str]] = {
    "title": "QuFin country scorecard",
    "scale": f"Each pillar and the overall score run from -{SCORE_LIMIT:g} (very weak) to "
    f"+{SCORE_LIMIT:g} (very strong).",
    "pillars": list(PILLARS),
    "statements": [
        "Scores use QuFin's proprietary methodology.",
        "Every indicator is read as it was published at the time, never with later revisions.",
        "Late or missing data lowers confidence, never the score itself.",
        "The confidence figure shows how much of the full evidence is fresh and usable.",
        "Scores describe conditions; they are not investment advice.",
    ],
}


def mechanism() -> dict:
    """The recipe: constants, direction and weight of every scored indicator."""
    return {
        "history_years": HISTORY_YEARS,
        "score_limit": SCORE_LIMIT,
        "momentum_weight": MOMENTUM_WEIGHT,
        "indicators": [
            {
                "id": series_id,
                "direction": "higher_is_stronger" if spec.polarity == 1 else "higher_is_weaker",
                "scored_on": "percent_change_over_a_year" if spec.transform == "yoy" else "level",
                "importance": spec.importance,
            }
            for series_id, spec in SCORED.items()
        ],
        "notes": [
            "pillar score = sum(w x s) / sum(w) over usable indicators",
            "w = importance x timeliness weight; timeliness halves every 60 days of delay",
            "overall = pillars weighted by their confidence",
        ],
    }
