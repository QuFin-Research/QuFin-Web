"""The comparison studio: one indicator across up to 10 countries, or several for one country.

The API does the work (Rules D, E, F, G): it puts every selected series on one frequency, computes
the actual value or the change over that frequency, enforces the 10-country cap and reports which
frequencies are possible and why. The web app only renders it.
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.core.auth import DbSession
from app.core.clock import Today
from app.data.indicator_concepts import CONCEPTS, SERIES_CONCEPTS
from app.data.macro_catalog import BY_ID
from app.data.taxonomy import COUNTRY_BY_ISO2, COUNTRY_BY_ISO3
from app.domain.comparability import concept_scales
from app.domain.harmonize import (
    FREQUENCIES,
    LABEL,
    MAX_COUNTRIES,
    POC_NAME,
    Frequency,
    Obs,
    adjustment_tag,
    aggregate,
    aggregation_for,
    allowed_frequencies,
    native_frequency,
    poc,
)
from app.domain.units import classify
from app.jobs.check_data import LAG_WINDOW, macro_status
from app.schemas.studio import (
    Metric,
    StudioCatalog,
    StudioCatalogSeries,
    StudioIndicator,
    StudioPoint,
    StudioResult,
    StudioSeries,
)
from app.stores.macro import MacroStore, SeriesSummary

router = APIRouter(prefix="/v1/studio", tags=["comparison studio"])

Concept = Annotated[str, Query(pattern=r"^[a-z0-9_]{2,64}$", description="Indicator concept key")]
FrequencyParam = Annotated[
    Frequency | None,
    Query(description="Display frequency; omitted means the lowest frequency all series share"),
]
MetricParam = Annotated[Metric, Query(description="actual value, or poc (percentage of change)")]
Years = Annotated[int, Query(ge=1, le=40, description="Years of history")]
# A rate or spread moves in points whatever the catalog says about its source.
_POINT_KINDS = frozenset({"rate_percent", "ratio"})


def _in_points(summary: SeriesSummary) -> bool:
    entry = BY_ID.get(summary.meta.id)
    if entry is not None:
        return entry.change == "diff"
    return summary.meta.unit_kind in _POINT_KINDS


def _label(summary: SeriesSummary, concept: str | None, iso3: str) -> str:
    name = CONCEPTS[concept].name if concept in CONCEPTS else summary.meta.title
    return f"{name} ({iso3})"


class _Native:
    """One selected series with its stored points, before any frequency is chosen."""

    def __init__(self, summary: SeriesSummary, iso3: str, country: str, today: date, years: int):
        self.summary = summary
        self.iso3, self.country = iso3, country
        self.concept = SERIES_CONCEPTS.get((summary.meta.country, summary.meta.id))
        self.label = _label(summary, self.concept, iso3)
        self.frequency = native_frequency(summary.meta.frequency)
        self.today = today
        self.years = years
        self.points: list[Obs] = []
        self.last_vintage: date | None = None
        self.published_as_change = bool(
            BY_ID.get(summary.meta.id) and BY_ID[summary.meta.id].published_as_change
        )

    def load(self, store: MacroStore) -> None:
        start = self.today - timedelta(days=366 * self.years)
        vintages = store.as_of(self.summary.meta.id, None, start=start)
        self.points = [Obs(v.period, v.value) for v in vintages if v.value is not None]
        self.last_vintage = max((v.realtime_start for v in vintages), default=None)


def _render(
    selected: list[_Native],
    store: MacroStore,
    today: date,
    frequency: Frequency | None,
    metric: Metric,
    mode: str,
    name: str,
    group_axes: bool,
) -> StudioResult:
    for item in selected:
        item.load(store)
    selected = [s for s in selected if s.points]
    if not selected:
        raise HTTPException(status_code=404, detail="No stored data for that selection")
    allowed = allowed_frequencies([(s.label, s.frequency) for s in selected])
    chosen = frequency or allowed.common
    if chosen not in allowed.frequencies:
        raise HTTPException(
            status_code=422,
            detail=(allowed.notice or f"{LABEL[chosen]} is not available")
            + f" Available: {', '.join(allowed.frequencies)}.",
        )
    releases = store.first_releases(today - LAG_WINDOW)
    notices: list[str] = []
    tags = {adjustment_tag(s.summary.meta.seasonal_adjustment) for s in selected}
    if len(tags) > 1:
        notices.append(
            "These series mix adjustments ("
            + ", ".join(sorted(tags))
            + "): seasonal adjustment differs between lines. Compare levels with care."
        )
    units = [
        classify(s.summary.meta.units, s.summary.meta.country, s.summary.meta.source)
        for s in selected
    ]
    if metric == "actual" and len(selected) > 1 and not group_axes:
        verdict = concept_scales({"x": units})["x"]
        if not verdict.same_scale:
            notices.append(
                f"Actual values are not on one scale ({verdict.reason}); use PoC to compare them."
            )
    axes: dict[tuple[str, str | None, str], int] = {}
    series: list[StudioSeries] = []
    for item, unit in zip(selected, units, strict=True):
        meta = item.summary.meta
        how = aggregation_for(unit.kind, item.concept)
        shown = aggregate(item.points, item.frequency, chosen, how)
        changed = chosen != item.frequency
        unit_text, note = meta.units, None
        if metric == "poc":
            shown, kind = poc(
                shown,
                chosen,
                in_points=_in_points(item.summary),
                published_as_change=item.published_as_change,
            )
            unit_text = kind
            note = (
                f"{POC_NAME[chosen]}: "
                + {
                    "%": "percent change from the previous period",
                    "pp": "difference from the previous period in the series' own units "
                    "(a rate or spread is never changed in percent)",
                    "as published": "the source already publishes this series as a change, "
                    "so it is shown as published and not changed again",
                }[kind]
            )
        axis_key = (unit.kind, unit.currency, unit.basis if metric == "actual" else unit_text)
        axis = axes.setdefault(axis_key, len(axes))
        status = macro_status(meta, item.summary.last_period, releases.get(meta.id, {}), today)
        series.append(
            StudioSeries(
                series_id=meta.id,
                canonical_code=meta.canonical_code,
                iso3=item.iso3,
                country=item.country,
                label=item.label,
                concept=item.concept,
                native_frequency=item.frequency,
                adjustment=adjustment_tag(meta.seasonal_adjustment),
                adjustment_text=meta.seasonal_adjustment,
                units=meta.units,
                display_unit=unit_text,
                aggregation=how if changed else None,
                metric_note=note,
                axis=axis if group_axes else 0,
                publisher=meta.publisher,
                last_vintage=item.last_vintage,
                usable=status.freshness.usable,
                status_note=status.freshness.reason,
                points=[StudioPoint(period=p.period, value=round(p.value, 6)) for p in shown],
            )
        )
    return StudioResult(
        mode=mode,  # type: ignore[arg-type]
        name=name,
        metric=metric,
        frequency=chosen,
        poc_name=POC_NAME[chosen] if metric == "poc" else None,
        allowed_frequencies=list(allowed.frequencies),
        restriction=allowed.notice,
        notices=notices,
        series=series,
    )


@router.get("/catalog", response_model=StudioCatalog)
def catalog(session: DbSession) -> StudioCatalog:
    """Indicators, countries, native frequencies, SA/NSA tags and update stamps for the pickers."""
    store = MacroStore(session)
    rows: list[StudioCatalogSeries] = []
    countries: dict[str, set[str]] = {}
    for s in store.list_series():
        place = COUNTRY_BY_ISO2.get(s.meta.country)
        if place is None:
            continue
        concept = SERIES_CONCEPTS.get((s.meta.country, s.meta.id))
        if concept:
            countries.setdefault(concept, set()).add(place.iso3)
        rows.append(
            StudioCatalogSeries(
                series_id=s.meta.id,
                canonical_code=s.meta.canonical_code,
                iso3=place.iso3,
                concept=concept,
                name=CONCEPTS[concept].name if concept in CONCEPTS else s.meta.title,
                native_frequency=native_frequency(s.meta.frequency),
                adjustment=adjustment_tag(s.meta.seasonal_adjustment),
                units=s.meta.units,
                source=s.meta.source,
                publisher=s.meta.publisher,
                last_period=s.last_period,
                last_updated=s.meta.last_updated.date() if s.meta.last_updated else None,
            )
        )
    rows.sort(key=lambda r: (r.iso3, r.name))
    return StudioCatalog(
        max_countries=MAX_COUNTRIES,
        frequencies=list(FREQUENCIES),
        indicators=[
            StudioIndicator(
                concept=c,
                name=CONCEPTS[c].name,
                explanation=CONCEPTS[c].explanation,
                countries=sorted(isos),
            )
            for c, isos in sorted(countries.items(), key=lambda kv: CONCEPTS[kv[0]].name)
        ],
        series=rows,
    )


@router.get("/compare", response_model=StudioResult)
def compare(
    session: DbSession,
    today: Today,
    concept: Concept,
    countries: Annotated[
        list[str],
        Query(description=f"ISO3 codes, 1 to {MAX_COUNTRIES}; repeat the parameter or comma-join"),
    ],
    frequency: FrequencyParam = None,
    metric: MetricParam = "actual",
    years: Years = 10,
) -> StudioResult:
    """One indicator for up to 10 countries, all on the same frequency (Rules D, E, F, G)."""
    if concept not in CONCEPTS:
        raise HTTPException(status_code=404, detail=f"Unknown indicator {concept}")
    codes = list(dict.fromkeys(c.strip().upper() for raw in countries for c in raw.split(",") if c))
    if not 1 <= len(codes) <= MAX_COUNTRIES:
        raise HTTPException(
            status_code=422, detail=f"Select 1 to {MAX_COUNTRIES} countries, got {len(codes)}"
        )
    unknown = [c for c in codes if c not in COUNTRY_BY_ISO3]
    if unknown:
        raise HTTPException(status_code=404, detail="Unknown country: " + ", ".join(unknown))
    store = MacroStore(session)
    by_country: dict[str, SeriesSummary] = {}
    for s in store.list_series():
        place = COUNTRY_BY_ISO2.get(s.meta.country)
        if (
            place
            and place.iso3 in codes
            and SERIES_CONCEPTS.get((s.meta.country, s.meta.id)) == concept
        ):
            by_country[place.iso3] = s
    selected = [
        _Native(by_country[c], c, COUNTRY_BY_ISO3[c].name, today, years)
        for c in codes
        if c in by_country
    ]
    result = _render(
        selected, store, today, frequency, metric, "countries", CONCEPTS[concept].name, False
    )
    missing = [COUNTRY_BY_ISO3[c].name for c in codes if c not in by_country]
    if missing:
        result = result.model_copy(
            update={"notices": [*result.notices, "No stored series for: " + ", ".join(missing)]}
        )
    return result


@router.get("/overlay", response_model=StudioResult)
def overlay(
    session: DbSession,
    today: Today,
    country: Annotated[str, Query(pattern=r"^[A-Z]{3}$", description="ISO3 code")],
    series_ids: Annotated[
        list[str], Query(alias="seriesIds", description="Series ids of that country")
    ],
    frequency: FrequencyParam = None,
    metric: MetricParam = "actual",
    years: Years = 10,
) -> StudioResult:
    """Several indicators for one country: actual values on separate axes by unit, or PoC."""
    place = COUNTRY_BY_ISO3.get(country)
    if place is None:
        raise HTTPException(status_code=404, detail="Unknown country")
    ids = list(dict.fromkeys(i.strip() for raw in series_ids for i in raw.split(",") if i))
    if not 1 <= len(ids) <= MAX_COUNTRIES:
        raise HTTPException(
            status_code=422, detail=f"Select 1 to {MAX_COUNTRIES} series, got {len(ids)}"
        )
    store = MacroStore(session)
    found = {s.meta.id: s for s in store.list_series() if s.meta.country == place.iso2}
    unknown = [i for i in ids if i not in found]
    if unknown:
        raise HTTPException(
            status_code=404, detail=f"Not a stored series of {place.name}: " + ", ".join(unknown)
        )
    selected = [_Native(found[i], place.iso3, place.name, today, years) for i in ids]
    return _render(selected, store, today, frequency, metric, "indicators", place.name, True)
