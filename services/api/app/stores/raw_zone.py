"""The raw zone: every payload a connector fetches, kept as received (Blueprint section 03).

Any stored number can be traced to the file it came from. Files are written once and never
overwritten: `<root>/<source>/<YYYY-MM-DD>/<name>-<HHMMSS>-<sha256 prefix>.<ext>`, with one line
per file appended to `<root>/manifest.jsonl` (path, checksum, size, time). Locally the root is
`QUFIN_RAW_DIR`; in the cloud it becomes an S3 bucket with versioning and object lock (P1-05).

Credentials never reach the raw zone: connectors store response bodies, not request URLs.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class RawFile:
    path: Path
    sha256: str
    size: int


class RawZone:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(
        self, source: str, name: str, payload: bytes, ext: str = "json", now: datetime | None = None
    ) -> RawFile:
        now = now or datetime.now(UTC)
        digest = hashlib.sha256(payload).hexdigest()
        folder = self.root / _SAFE.sub("_", source) / now.strftime("%Y-%m-%d")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{_SAFE.sub('_', name)}-{now.strftime('%H%M%S')}-{digest[:12]}.{ext}"
        if not path.exists():  # same content in the same second: already kept
            with path.open("xb") as f:
                f.write(payload)
        entry = {
            "path": path.relative_to(self.root).as_posix(),
            "sha256": digest,
            "bytes": len(payload),
            "source": source,
            "name": name,
            "fetched_at": now.isoformat(),
        }
        with (self.root / "manifest.jsonl").open("a", encoding="utf-8") as manifest:
            manifest.write(json.dumps(entry) + "\n")
        return RawFile(path, digest, len(payload))
