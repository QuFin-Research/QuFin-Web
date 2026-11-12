"""OECD Data Explorer connector (SDMX, keyless): https://data-explorer.oecd.org"""

from typing import Any

from app.connectors.sdmx import SdmxClient

BASE_URL = "https://sdmx.oecd.org/public/rest"
# Composite leading indicators, business and consumer confidence (latest version).
CLI_FLOW = "OECD.SDD.STES,DSD_STES@DF_CLI,"


class OecdClient(SdmxClient):
    source = "oecd"
    min_interval = 3.0  # rule 28: limits requests per hour (see docs/data-connections.md)

    def __init__(self, base_url: str = BASE_URL, **kwargs: Any) -> None:
        kwargs.setdefault("timeout", 120.0)
        super().__init__(base_url, **kwargs)
