"""One name per publisher.

`macro_series.source_name` keeps the producer's wording exactly as the source states it, because
that is the traceable provenance (rule 4): FRED says "International Monetary Fund", the IMF's own
API connector says "International Monetary Fund (from national central banks)". The same
organisation under two spellings splits any count, filter or licence lookup by publisher in two,
so every series also stores `publisher`, the canonical organisation, from this module.

An unknown name passes through unchanged (trimmed); add an alias when a new wording appears.
"""

import re

# Exact wordings seen in the sources, mapped to the one canonical name.
ALIASES: dict[str, str] = {
    "International Monetary Fund (from national central banks)": "International Monetary Fund",
    "OECD (from national sources)": "OECD",
    "Bank for International Settlements (from national central banks)": (
        "Bank for International Settlements"
    ),
    "U.S. Department of the Treasury. Fiscal Service": (
        "U.S. Department of the Treasury, Bureau of the Fiscal Service"
    ),
    "Board of Governors of the Federal Reserve System (US)": (
        "Board of Governors of the Federal Reserve System"
    ),
    "Board of Governors of the Federal Reserve System (H.15); spread calculated by FRED": (
        "Board of Governors of the Federal Reserve System"
    ),
    "Moody's (Baa yield) and Federal Reserve H.15; spread calculated by FRED": (
        "Moody's; Board of Governors of the Federal Reserve System"
    ),
}

# "(from national sources)": how the publisher gets its data, not who it is.
_QUALIFIER = re.compile(r"\s*\((?:from|via)\s[^)]*\)\s*$", re.IGNORECASE)


def canonical_publisher(source_name: str | None) -> str | None:
    if source_name is None:
        return None
    name = " ".join(source_name.split())
    if not name:
        return None
    return ALIASES.get(name) or _QUALIFIER.sub("", name) or name
