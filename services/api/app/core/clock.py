from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends


def today() -> date:
    """Today's date in UTC; a dependency so tests can fix the clock."""
    return datetime.now(UTC).date()


Today = Annotated[date, Depends(today)]
