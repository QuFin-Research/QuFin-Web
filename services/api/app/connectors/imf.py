"""IMF data connector (SDMX 2.1, keyless): https://data.imf.org

Used only for what FRED does not carry live (rule 17): FRED republishes many IMF series with
vintages, and those are loaded from FRED instead.
"""

from typing import Any

from app.connectors.sdmx import SdmxClient

BASE_URL = "https://api.imf.org/external/sdmx/2.1"
# International Liquidity (the former IFS reserves tables), checked on 7 Nov 2026.
IL_FLOW = "IMF.STA,IL,13.0.1"


class ImfClient(SdmxClient):
    source = "imf"

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 120.0)
        # The IMF answers in SDMX-ML unless JSON is asked for in the Accept header.
        kwargs.setdefault(
            "headers", {"Accept": "application/vnd.sdmx.data+json;version=1.0.0, application/json"}
        )
        super().__init__(base_url, **kwargs)
