"""Macro data by indicator and by country, and point-in-time reads by canonical code."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy import select

from app.core.auth import DbSession
from app.core.clock import Today
from app.data.indicator_concepts import COMPARED_AS, CONCEPTS, SERIES_CONCEPTS
from app.data.macro_catalog import BY_ID
from app.data.taxonomy import COUNTRY_BY_ISO2, COUNTRY_BY_ISO3, PILLARS, pillar_for
from app.domain.comparability import concept_scales
from app.domain.comparison import BASES, Point, on_basis, points_ago
from app.domain.units import UnitInfo, classify
from app.jobs.check_data import LAG_WINDOW, macro_status
from app.schemas.taxonomy import (
    Comparison,
    ComparisonPoint,
    ComparisonRow,
    Country,
    EconomicEvent,
    Indicator,
    MissingCountry,
    PillarScores,
    PitSeries,
)
from app.stores.macro import MacroStore
from app.stores.point_in_time import CountryNotFoundError, PointInTime, SeriesNotFoundError
from app.stores.taxonomy import CountryRow, calendar_window

router = APIRouter(prefix="/v1/macro", tags=["macro taxonomy"])

CanonicalCode = Annotated[
    str, Path(pattern=r"^[A-Z0-9]{3}\.[A-Z]{3,12}\.[A-Z0-9_]{2,64}\.[A-Z]\.[A-Z]{2,5}$")
]
AsOf = Annotated[
    str | None,
    Query(
        alias="asOf",
        description="A moment (ISO 8601) or a day. A timestamp sees vintages dated before its "
        "day; a day ('2026-09-10') sees everything published through that day.",
    ),
]
MAX_EVENTS = 1000


def parse_as_of(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        if len(value) == 10:  # a day: the close of that day, so its own releases count
            return datetime.combine(date.fromisoformat(value) + timedelta(days=1), time(), UTC)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422, detail="asOf must be an ISO 8601 date or time"
        ) from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@router.get("/countries", response_model=list[Country])
def list_countries(session: DbSession) -> list[Country]:
    """Every country with its blocs and how many series of each pillar are stored."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in MacroStore(session).list_series():
        if (s.meta.country, s.meta.id) in SERIES_CONCEPTS:
            counts[s.meta.country][s.meta.pillar or ""] += 1
    rows = {r.iso2: r for r in session.scalars(select(CountryRow))}
    result = []
    for iso2, place in COUNTRY_BY_ISO2.items():
        row = rows.get(iso2)
        result.append(
            Country(
                iso3=place.iso3,
                iso2=iso2,
                name=place.name,
                currency=place.currency,
                central_bank=place.central_bank,
                g7=row.g7 if row else place.g7,
                g20=row.g20 if row else place.g20,
                gcc=row.gcc if row else place.gcc,
                em=row.em if row else place.em,
                series_count=sum(counts[iso2].values()),
                pillars={p: counts[iso2][p] for p in PILLARS if counts[iso2].get(p)}
                | {p: n for p, n in counts[iso2].items() if p not in PILLARS and p},
            )
        )
    return sorted(result, key=lambda c: (-c.series_count, c.name))


@router.get("/indicators", response_model=list[Indicator])
def list_indicators(session: DbSession) -> list[Indicator]:
    """Every indicator once, with the countries that have it (the by-indicator view)."""
    groups: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)
    pillars: dict[str, str] = {}
    units: dict[str, list[UnitInfo]] = defaultdict(list)
    for s in MacroStore(session).list_series():
        key = SERIES_CONCEPTS.get((s.meta.country, s.meta.id))
        place = COUNTRY_BY_ISO2.get(s.meta.country)
        if key is None or place is None:
            continue
        groups[key].add(place.iso3)
        counts[key] += 1
        units[key].append(classify(s.meta.units, s.meta.country, s.meta.source))
        pillars.setdefault(key, s.meta.pillar or pillar_for(s.meta.country, s.meta.id) or "")
    scales = concept_scales(units)
    return sorted(
        (
            Indicator(
                concept=key,
                name=CONCEPTS[key].name,
                explanation=CONCEPTS[key].explanation,
                acronym=CONCEPTS[key].acronym,
                pillar=pillars[key],
                series_count=counts[key],
                countries=sorted(groups[key]),
                same_scale=scales[key].same_scale,
                scale_note=None if scales[key].same_scale else scales[key].reason,
                compared_as=COMPARED_AS.get(key),
            )
            for key in groups
        ),
        key=lambda i: (i.pillar, i.name),
    )


HISTORY_MONTHS = 36
# Enough stored history for a year-on-year change at the start of the 36 months shown.
COMPARE_LOOKBACK = timedelta(days=(HISTORY_MONTHS + 14) * 31)


@router.get("/compare/{concept}", response_model=Comparison)
def compare_countries(
    session: DbSession,
    today: Today,
    concept: Annotated[str, Path(pattern=r"^[a-z0-9_]{2,64}$")],
) -> Comparison:
    """One indicator across countries on a common basis: CPI as year-on-year change,
    unemployment as a share of the labour force. Never raw index levels or head counts."""
    basis = BASES.get(concept)
    if basis is None:
        raise HTTPException(
            status_code=404, detail=f"No comparison basis for {concept}: " + ", ".join(BASES)
        )
    store = MacroStore(session)
    releases = store.first_releases(today - LAG_WINDOW)
    rows: list[ComparisonRow] = []
    covered: set[str] = set()
    methods: set[str] = set()
    for s in store.list_series():
        if SERIES_CONCEPTS.get((s.meta.country, s.meta.id)) != concept:
            continue
        place = COUNTRY_BY_ISO2.get(s.meta.country)
        if place is None:
            continue
        entry = BY_ID.get(s.meta.id)
        as_change = bool(entry and entry.published_as_change)
        vintages = store.as_of(s.meta.id, None, start=today - COMPARE_LOOKBACK)
        stored = [Point(v.period, v.value) for v in vintages if v.value is not None]
        points = on_basis(concept, stored, published_as_change=as_change)
        if not points:
            continue
        covered.add(place.iso3)
        converted = basis.from_level and not as_change
        methods.add(
            "converted from the index level to its year-on-year change"
            if converted
            else "published on this basis by the source"
        )
        latest = points[-1]
        status = macro_status(s.meta, s.last_period, releases.get(s.meta.id, {}), today)
        before_3, before_12 = points_ago(points, 3), points_ago(points, 12)
        rows.append(
            ComparisonRow(
                iso3=place.iso3,
                country=place.name,
                series_id=s.meta.id,
                canonical_code=s.meta.canonical_code,
                publisher=s.meta.publisher,
                source_name=s.meta.source_name,
                period=latest.period,
                value=round(latest.value, 2),
                change_3m=round(latest.value - before_3.value, 2) if before_3 else None,
                change_12m=round(latest.value - before_12.value, 2) if before_12 else None,
                converted=converted,
                stored_as=s.meta.units,
                usable=status.freshness.usable,
                status_note=status.freshness.reason,
                history=[
                    ComparisonPoint(period=p.period, value=round(p.value, 2))
                    for p in points[-HISTORY_MONTHS:]
                ],
            )
        )
    rows.sort(key=lambda r: (not r.usable, -r.value))
    return Comparison(
        concept=concept,
        name=CONCEPTS[concept].name,
        explanation=CONCEPTS[concept].explanation,
        basis=basis.label,
        unit=basis.unit,
        method="; ".join(sorted(methods)) if methods else "no series stored",
        higher_is=basis.higher_is,
        rows=rows,
        missing=sorted(
            (
                MissingCountry(iso3=c.iso3, name=c.name)
                for c in COUNTRY_BY_ISO2.values()
                if c.iso3 not in covered
            ),
            key=lambda m: m.name,
        ),
    )


@router.get("/code/{canonical_code}", response_model=PitSeries)
def get_series_by_code(
    session: DbSession,
    canonical_code: CanonicalCode,
    as_of: AsOf = None,
    start: Annotated[date | None, Query(description="First period")] = None,
    end: Annotated[date | None, Query(description="Last period")] = None,
) -> PitSeries:
    """A series by canonical code: the latest vintages, or exactly as known at `asOf`."""
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")
    when = parse_as_of(as_of)
    service = PointInTime(session)
    try:
        if when is None:
            return service.get_latest_series(canonical_code, start, end)
        return service.get_point_in_time_series(canonical_code, when, start, end)
    except SeriesNotFoundError:
        raise HTTPException(status_code=404, detail="No series with that code") from None


@router.get("/pillar-scores/{iso3}", response_model=PillarScores)
def get_pillar_scores(
    session: DbSession,
    today: Today,
    iso3: Annotated[str, Path(pattern=r"^[A-Z]{3}$")],
    as_of: AsOf = None,
) -> PillarScores:
    """Pillar scores as known at `asOf` (now by default). Only the United States is scored."""
    if iso3 not in COUNTRY_BY_ISO3:
        raise HTTPException(status_code=404, detail="Unknown country")
    when = parse_as_of(as_of) or datetime.combine(today + timedelta(days=1), time(), UTC)
    try:
        return PointInTime(session).compute_macro_pillar_scores(iso3, when)
    except CountryNotFoundError:
        raise HTTPException(status_code=404, detail="Unknown country") from None


@router.get("/calendar", response_model=list[EconomicEvent])
def get_calendar(
    session: DbSession,
    today: Today,
    start: Annotated[date | None, Query(alias="from", description="First release day")] = None,
    end: Annotated[date | None, Query(alias="to", description="Last release day")] = None,
    country: Annotated[str | None, Query(pattern=r"^[A-Z]{3}$", description="ISO3")] = None,
    pillar: Annotated[str | None, Query(pattern=r"^[A-Z]{3,12}$")] = None,
) -> list[EconomicEvent]:
    """Releases between two days (default: last week to next two weeks), soonest first.

    Consensus and surprise are empty until a licensed consensus feed supplies them.
    """
    first = start or today - timedelta(days=7)
    last = end or today + timedelta(days=14)
    if first > last:
        raise HTTPException(status_code=422, detail="from must not be after to")
    place = COUNTRY_BY_ISO3.get(country) if country else None
    if country and place is None:
        raise HTTPException(status_code=404, detail="Unknown country")
    rows = calendar_window(
        session, first, last, pillar=pillar, iso2=place.iso2 if place else None, limit=MAX_EVENTS
    )
    return [
        EconomicEvent(
            canonical_code=series.canonical_code or "",
            series_id=series.id,
            period=event.period,
            release_date=event.release_date,
            release_time_utc=event.release_time_utc,
            status="released" if event.status == "released" else "scheduled",
            previous_value=event.previous_value,
            consensus_estimate=event.consensus_estimate,
            consensus_source=event.consensus_source,
            actual_value=event.actual_value,
            surprise_score=event.surprise_score,
        )
        for event, series in rows
    ]
