"""Convert native-currency macro values to USD at query time (rule 23)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.data.macro_catalog import BY_ID
from app.data.series_units import SERIES_UNITS
from app.stores.macro import MacroStore

log = logging.getLogger(__name__)

# Currency -> (catalog series, stored quote is currency units per USD).
_DECLARED_FX_SERIES: dict[str, tuple[str, bool]] = {
    "EUR": ("DEXUSEU", False),
    "GBP": ("DEXUSUK", False),
    "JPY": ("DEXJPUS", True),
    "CAD": ("DEXCAUS", True),
    "AUD": ("DEXUSAL", False),
    "CHF": ("DEXSZUS", True),
    "NZD": ("DEXUSNZ", False),
}

# Never request an FX feed that is absent from the live macro catalog.
_CATALOG_CURRENCIES = {
    currency
    for series_id, (_, currency) in SERIES_UNITS.items()
    if series_id in BY_ID and currency is not None
}
FX_SERIES = {
    currency: entry
    for currency, entry in _DECLARED_FX_SERIES.items()
    if entry[0] in BY_ID and currency in _CATALOG_CURRENCIES
}


@dataclass(frozen=True)
class ConversionResult:
    period: date
    native_value: float | None
    value_usd: float | None
    native_currency: str
    fx_rate: float | None
    fx_rate_date: date | None
    fx_source: str | None
    method: str
    usable: bool
    reason: str | None = None


def _period_bounds(period: date, frequency: str) -> tuple[date, date]:
    freq = frequency.strip().lower().replace("-", "_").replace(" ", "_")
    if freq in ("daily", "d"):
        return period, period
    if freq in ("weekly", "w"):
        start = period.fromordinal(period.toordinal() - period.weekday())
        return start, start.fromordinal(start.toordinal() + 6)
    if freq in ("monthly", "m"):
        start = period.replace(day=1)
        next_month = (
            date(period.year + 1, 1, 1)
            if period.month == 12
            else date(period.year, period.month + 1, 1)
        )
        return start, next_month.fromordinal(next_month.toordinal() - 1)
    if freq in ("quarterly", "q"):
        start = period.replace(month=((period.month - 1) // 3) * 3 + 1, day=1)
        end_month = start.month + 2
        next_quarter = (
            date(start.year + 1, 1, 1)
            if end_month == 12
            else date(start.year, end_month + 1, 1)
        )
        return start, next_quarter.fromordinal(next_quarter.toordinal() - 1)
    if freq in ("semi_annual", "semiannual", "s"):
        start = period.replace(month=1 if period.month <= 6 else 7, day=1)
        next_half = date(start.year, 7, 1) if start.month == 1 else date(start.year + 1, 1, 1)
        return start, next_half.fromordinal(next_half.toordinal() - 1)
    if freq in ("annual", "a", "y"):
        return date(period.year, 1, 1), date(period.year, 12, 31)
    raise ValueError(f"unsupported FX conversion frequency: {frequency!r}")


def _usd_per_unit(value: float, inverted: bool) -> float | None:
    if value <= 0:
        return None
    return 1 / value if inverted else value


class CurrencyService:
    def __init__(self, store: MacroStore) -> None:
        self.store = store

    def convert_points(
        self,
        points: Sequence[tuple[date, float | None]],
        native_currency: str,
        frequency: str,
        *,
        is_flow: bool,
        amount_scale: float = 1.0,
        as_of: date | None = None,
    ) -> list[ConversionResult]:
        """Convert already frequency-aligned points; flows use an in-period mean FX rate."""
        if native_currency == "USD":
            return [
                ConversionResult(
                    period=period,
                    native_value=value,
                    value_usd=value * amount_scale if value is not None else None,
                    native_currency=native_currency,
                    fx_rate=None,
                    fx_rate_date=None,
                    fx_source=None,
                    method="identity",
                    usable=value is not None,
                )
                for period, value in points
            ]

        fx = FX_SERIES.get(native_currency)
        if fx is None:
            reason = f"No catalogued USD exchange-rate series for {native_currency} (Rule 37)"
            log.warning("%s; currency conversion is unavailable", reason)
            return [
                ConversionResult(
                    period=period,
                    native_value=value,
                    value_usd=None,
                    native_currency=native_currency,
                    fx_rate=None,
                    fx_rate_date=None,
                    fx_source=None,
                    method="period_average" if is_flow else "period_end",
                    usable=False,
                    reason=reason,
                )
                for period, value in points
            ]

        series_id, inverted = fx
        vintages = self.store.as_of(series_id, as_of=as_of)
        if not vintages:
            log.warning(
                "Catalogued FX series %s has no stored observations for %s conversion",
                series_id,
                native_currency,
            )

        results = []
        for period, value in points:
            method = "period_average" if is_flow else "period_end"
            if value is None:
                results.append(
                    ConversionResult(
                        period, None, None, native_currency, None, None, series_id,
                        method, False, "native observation is missing"
                    )
                )
                continue

            start, end = _period_bounds(period, frequency)
            eligible: list[tuple[date, float]] = []
            for vintage in vintages:
                if vintage.value is None or not (
                    start <= vintage.period <= end if is_flow else vintage.period <= end
                ):
                    continue
                fx_rate = _usd_per_unit(vintage.value, inverted)
                if fx_rate is not None:
                    eligible.append((vintage.period, fx_rate))
            rate: float | None
            rate_date: date | None
            if is_flow:
                in_period = [(day, fx_rate) for day, fx_rate in eligible if start <= day <= end]
                rate = (
                    sum(fx_rate for _, fx_rate in in_period) / len(in_period)
                    if in_period
                    else None
                )
                rate_date = max((day for day, _ in in_period), default=None)
            else:
                rate_date, rate = (
                    max(eligible, key=lambda item: item[0]) if eligible else (None, None)
                )

            rate_reason: str | None = (
                None if rate is not None else f"No usable {series_id} rate for {period}"
            )
            results.append(
                ConversionResult(
                    period=period,
                    native_value=value,
                    value_usd=value * rate * amount_scale if rate is not None else None,
                    native_currency=native_currency,
                    fx_rate=rate,
                    fx_rate_date=rate_date,
                    fx_source=series_id,
                    method=method,
                    usable=rate is not None,
                    reason=rate_reason,
                )
            )
        return results


__all__ = ["FX_SERIES", "ConversionResult", "CurrencyService"]
