"""Whether the series of one concept share a scale, so countries can be compared as stored.

A concept ("consumer_prices") is one indicator in every country (rules 18 and 19), even when the
countries' statistics offices publish it differently: the US index level and the euro area's annual
rate of change are both "CPI". Their stored values are then not on one scale, and ranking or
pooling them as they are would compare 337 with 4.0. Rule 23: such series need a common basis.

This finds the concepts whose series do not share one unit kind, currency and basis. Each must be
declared in `COMPARED_AS` (`app/data/indicator_concepts.py`) with the basis countries are compared
on; one that is not declared fails the release check, so a country added later cannot slip in with
a different scale unnoticed.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.domain.units import UnitInfo, comparable


@dataclass(frozen=True)
class ConceptScale:
    same_scale: bool
    reason: str


def concept_scales(units: Mapping[str, Iterable[UnitInfo]]) -> dict[str, ConceptScale]:
    """Per concept: whether every series reads on the same scale as the first, and if not why."""
    result: dict[str, ConceptScale] = {}
    for concept, infos in units.items():
        items = list(infos)
        verdict = ConceptScale(True, "same unit and currency")
        if items:
            first = items[0]
            for other in items[1:]:
                if not comparable(first, other).same_scale:
                    verdict = ConceptScale(False, f"{_describe(first)} against {_describe(other)}")
                    break
        result[concept] = verdict
    return result


def _describe(unit: UnitInfo) -> str:
    return f"{unit.kind} ({unit.basis}{', ' + unit.currency if unit.currency else ''})"
