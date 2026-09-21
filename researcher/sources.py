#!/usr/bin/env python3
"""Source registry and provenance for a run.

Every URL returned by `web_search` or actually retrieved by `fetch_url` is
registered here. The writer/reviewer may only cite URLs present in this
registry, so a model can never invent a reference. Thread-safe because research
subagents run concurrently.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path


def normalize_url(url: str) -> str:
    """Canonicalize a URL for registry lookups (drop fragment and trailing slash)."""
    url = url.strip().split("#", 1)[0]
    if url.endswith("/") and url.count("/") > 3:
        url = url[:-1]
    return url


@dataclass
class Source:
    """A single retrieved source with its provenance."""

    url: str
    title: str = ""
    outlet: str = ""
    origin: str = "search"
    alive: bool | None = None
    http_status: int | None = None
    fetched: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def citable(self) -> bool:
        """A source is citable when it was retrieved and is not known dead."""
        return self.alive is not False


class SourceRegistry:
    """Thread-safe collection of the sources retrieved during a run."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}
        self._lock = threading.Lock()

    def add(
        self, url: str, *, title: str = "", outlet: str = "", origin: str = "search"
    ) -> Source:
        """Register a URL (idempotent), enriching an existing entry."""
        key = normalize_url(url)
        with self._lock:
            source = self._sources.get(key)
            if source is None:
                source = Source(url=key, title=title, outlet=outlet, origin=origin)
                self._sources[key] = source
            else:
                source.title = source.title or title
                source.outlet = source.outlet or outlet
            return source

    def mark_fetched(
        self, url: str, *, ok: bool, status: int | None, title: str = ""
    ) -> None:
        """Record the outcome of fetching a URL's content."""
        source = self.add(url, origin="fetch")
        with self._lock:
            source.fetched = True
            source.alive = ok
            source.http_status = status
            source.title = source.title or title

    def mark_alive(self, url: str, *, ok: bool | None, status: int | None) -> None:
        """Record the outcome of a liveness check (`None` = unknown)."""
        source = self.add(url)
        with self._lock:
            source.alive = ok
            source.http_status = status

    def get(self, url: str) -> Source | None:
        """Return the registered source for a URL, if any."""
        return self._sources.get(normalize_url(url))

    def has(self, url: str) -> bool:
        """Return whether a URL was actually retrieved during this run."""
        return normalize_url(url) in self._sources

    def all(self) -> list[Source]:
        """Return every registered source, ordered by first registration."""
        with self._lock:
            return list(self._sources.values())

    def save(self, path: Path) -> None:
        """Write the registry to a JSON file."""
        payload = [asdict(s) for s in self.all()]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
