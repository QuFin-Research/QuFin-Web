"""ECB Data Portal connector (SDMX, keyless): https://data.ecb.europa.eu/help/api/overview"""

from typing import Any

from app.connectors.sdmx import SdmxClient

BASE_URL = "https://data-api.ecb.europa.eu/service"


class EcbClient(SdmxClient):
    source = "ecb"
    min_interval = 1.0  # rule 28: no published limit found

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 60.0)
        super().__init__(base_url, **kwargs)
