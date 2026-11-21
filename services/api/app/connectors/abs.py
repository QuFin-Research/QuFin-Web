"""Australian Bureau of Statistics data API (SDMX, keyless): https://data.api.abs.gov.au

The ABS publishes SDMX 2.1 at `/rest/data/<flow>/<key>`; flows look like `ABS,CPI,2.0.0`. The
terms (CC BY 4.0 per the supplier's table of 21 Nov 2026) were not read here, so a series from this
source stays unscored and flagged until they are (rule 7). Rule 28: one request every two seconds.
"""

from typing import Any

from app.connectors.sdmx import SdmxClient

BASE_URL = "https://data.api.abs.gov.au/rest"


class AbsClient(SdmxClient):
    source = "abs"
    min_interval = 2.0  # rule 28: no stated rate; one request every two seconds

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 120.0)
        super().__init__(base_url, **kwargs)
