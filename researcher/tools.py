#!/usr/bin/env python3
"""Tools exposed to the agents, plus dispatch and transcript indexing.

Each agent gets its own `Toolbox` that shares the run's source registry and
trace. Tool results are JSON strings so they serialize cleanly into the model's
`tool` messages. Tools never raise across the boundary: failures are returned as
`{"error": ...}`.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from trace import RunTrace
from typing import Any

import requests
import trafilatura
from config import Settings
from ddgs import DDGS
from pypdf import PdfReader
from sources import SourceRegistry
from validate import validate_critique

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
FETCH_MAX_TOKENS = 6000
TRANSCRIPT_MAX_CHARS = 12000
HEADING_RE = re.compile(r"^##\s+(\d{1,3}:\d{2})\s*-\s*(.+?)\s*$")
BOILERPLATE_RE = re.compile(
    r"^(accept|agree|cookie|subscribe|sign in|log in|share|advertisement)\b",
    re.IGNORECASE,
)
BOT_BLOCK_STATUSES = {401, 403, 405, 406, 429}


def _reachable(status: int) -> bool:
    """A URL is reachable when the status is OK or a bot-block response."""
    return status < 400 or status in BOT_BLOCK_STATUSES


def _liveness(status: int) -> bool | None:
    """Classify an HTTP status: reachable, dead, or unknown (server/bot error)."""
    if _reachable(status):
        return True
    if 400 <= status < 500:
        return False
    return None


def _truncate_tokens(text: str, max_tokens: int) -> tuple[str, bool]:
    """Truncate text to a token budget; returns (text, truncated)."""
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text, False
        return encoding.decode(tokens[:max_tokens]), True
    except Exception:  # noqa: BLE001
        approx = max_tokens * 4
        return (text[:approx], True) if len(text) > approx else (text, False)


def _clean_text(text: str) -> str:
    """Collapse whitespace and drop obvious boilerplate lines."""
    kept: list[str] = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if len(line) < 3 or BOILERPLATE_RE.match(line):
            continue
        if kept and kept[-1] == line:
            continue
        kept.append(line)
    return "\n".join(kept)


def extract_title(html: str) -> str:
    """Extract the page title from HTML metadata with trafilatura."""
    with contextlib.suppress(Exception):
        metadata = trafilatura.extract_metadata(html)
        if metadata and metadata.title:
            return metadata.title.strip()
    return ""


def html_to_text(html: str) -> str:
    """Extract the main text from an HTML page with trafilatura."""
    extracted = None
    with contextlib.suppress(Exception):
        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False
        )
    return _clean_text(extracted or "")


def pdf_to_text(data: bytes) -> tuple[str, int]:
    """Extract text from PDF bytes with pypdf; returns (text, page_count)."""
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return _clean_text("\n".join(pages)), len(reader.pages)


@dataclass
class Chapter:
    """One transcript chapter."""

    timestamp: str
    title: str
    body: str


class TranscriptIndex:
    """Searchable index over `processed/episode-N.md`."""

    def __init__(self, text: str) -> None:
        self.chapters: list[Chapter] = []
        current: Chapter | None = None
        for line in text.splitlines():
            match = HEADING_RE.match(line)
            if match:
                current = Chapter(match.group(1), match.group(2), "")
                self.chapters.append(current)
                continue
            if current is not None:
                current.body += line + "\n"
        for chapter in self.chapters:
            chapter.body = chapter.body.strip()

    def find(self, query: str, limit: int = 3) -> list[Chapter]:
        """Find chapters by timestamp prefix or case-insensitive title substring."""
        query = query.strip()
        if not query:
            return self.chapters[:limit]
        matches = [c for c in self.chapters if c.timestamp.startswith(query)]
        if not matches:
            lowered = query.lower()
            matches = [c for c in self.chapters if lowered in c.title.lower()]
        if not matches:
            matches = [c for c in self.chapters if lowered in c.body.lower()]
        return matches[:limit]


TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for English-language sources on a topic. Returns titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a URL and return its main text. Handles HTML pages and PDFs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "url_alive",
            "description": "Check whether a URL is reachable (HTTP status).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to check."}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_transcript",
            "description": "Read the English transcript chapter(s) matching a timestamp or title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Timestamp like 06:17 or a title/substring; empty returns the first chapters.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "note_write",
            "description": "Persist research notes under a topic id for the writer to reuse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_id": {
                        "type": "string",
                        "description": "Short slug for the topic.",
                    },
                    "content": {"type": "string", "description": "The notes to save."},
                },
                "required": ["topic_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate",
            "description": "Run deterministic structure/citation checks on a Markdown critique draft.",
            "parameters": {
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": "The full critique Markdown.",
                    }
                },
                "required": ["markdown"],
            },
        },
    },
]

TOOL_NAMES = {spec["function"]["name"] for spec in TOOL_SPECS}
WRITER_TOOLS = [
    "web_search",
    "fetch_url",
    "url_alive",
    "read_transcript",
    "note_write",
    "validate",
]
RESEARCH_TOOLS = [
    "web_search",
    "fetch_url",
    "url_alive",
    "read_transcript",
    "note_write",
]
REVIEWER_TOOLS = ["web_search", "fetch_url", "url_alive", "read_transcript", "validate"]


@dataclass
class Toolbox:
    """Binds the agent tools to a run's shared state for one agent."""

    settings: Settings
    registry: SourceRegistry
    trace: RunTrace
    agent: str
    content_text: str
    transcript: TranscriptIndex
    notes_dir: Path
    session: requests.Session = field(default_factory=requests.Session)
    seen_urls: set[str] = field(default_factory=set)

    def specs(self, names: list[str]) -> list[dict[str, Any]]:
        """Return the function specs for the named tools."""
        return [spec for spec in TOOL_SPECS if spec["function"]["name"] in names]

    def dispatch(self, name: str, arguments: str) -> str:
        """Execute a tool by name and return its JSON result string."""
        handlers: dict[str, Callable[..., Any]] = {
            "web_search": self.web_search,
            "fetch_url": self.fetch_url,
            "url_alive": self.url_alive,
            "read_transcript": self.read_transcript,
            "note_write": self.note_write,
            "validate": self.validate,
        }
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return json.dumps({"error": f"invalid JSON arguments: {arguments!r}"})
        if name not in TOOL_NAMES:
            return json.dumps({"error": f"unknown tool: {name}"})
        try:
            result = handlers[name](**args)
        except Exception as exc:  # noqa: BLE001
            self.trace.log("tool_error", agent=self.agent, message=name, error=str(exc))
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})
        self.trace.log("tool_call", agent=self.agent, message=name, arguments=args)
        return json.dumps(result, ensure_ascii=False)

    def web_search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        """Search the web with ddgs and register every returned URL.

        The default metacrawl backend is used: pinning a single provider
        (e.g. ``duckduckgo``) turns flaky under parallel load and silently
        returns "No results found." for many queries, so ddgs fans out across
        its providers instead (as in the original pipeline). Transient network
        failures and empty responses are retried a few times before being
        surfaced to the agent.
        """
        last_error = ""
        for attempt in range(3):
            try:
                results: list[dict[str, str]] = []
                with DDGS() as ddgs:
                    for item in ddgs.text(query, max_results=max_results):
                        url = item.get("href") or item.get("url") or ""
                        if not url:
                            continue
                        title = item.get("title", "")
                        self.registry.add(url, title=title, origin="search")
                        self.seen_urls.add(url)
                        results.append(
                            {
                                "title": title,
                                "url": url,
                                "snippet": item.get("body", ""),
                            }
                        )
                if results:
                    return results
                last_error = "no results found"
                if attempt:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
            time.sleep(0.5 + attempt)
        raise RuntimeError(f"web_search failed for {query!r}: {last_error}")

    def fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch a URL and return cleaned main text; supports HTML and PDF."""
        response = self.session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=self.settings.request_timeout,
            allow_redirects=True,
        )
        status = response.status_code
        content_type = response.headers.get("Content-Type", "").lower()
        is_pdf = "application/pdf" in content_type or url.lower().split("?")[
            0
        ].endswith(".pdf")
        liveness = _liveness(status)
        if liveness is False:
            self.registry.mark_fetched(url, ok=False, status=status)
            return {"error": f"HTTP {status}", "url": url}
        if liveness is None:
            self.registry.add(url, origin="fetch")
            return {"error": f"HTTP {status} (blocked or unavailable)", "url": url}
        if is_pdf:
            text, pages = pdf_to_text(response.content)
            if len(text) < 200:
                self.registry.mark_fetched(url, ok=False, status=status, title="")
                return {"error": "no extractable text (possibly scanned)", "url": url}
            truncated_text, truncated = _truncate_tokens(text, FETCH_MAX_TOKENS)
            self.registry.mark_fetched(url, ok=True, status=status)
            return {
                "url": url,
                "pages": pages,
                "text": truncated_text,
                "truncated": truncated,
            }
        title = extract_title(response.text)
        text = html_to_text(response.text)
        truncated_text, truncated = _truncate_tokens(text, FETCH_MAX_TOKENS)
        self.registry.mark_fetched(url, ok=True, status=status, title=title)
        return {
            "url": url,
            "title": title,
            "text": truncated_text,
            "truncated": truncated,
        }

    def url_alive(self, url: str) -> dict[str, Any]:
        """Check URL liveness and record the result in the registry.

        Bot-blocking responses (401/403/405/429) count as reachable so a real
        source behind a bot wall is not mistaken for a dead link.
        """
        try:
            response = self.session.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                allow_redirects=True,
                stream=True,
            )
            ok = _liveness(response.status_code)
            response.close()
            self.registry.mark_alive(url, ok=ok, status=response.status_code)
            return {"url": url, "status": response.status_code, "ok": ok}
        except requests.RequestException as exc:
            self.registry.mark_alive(url, ok=None, status=None)
            return {"url": url, "status": None, "ok": None, "error": str(exc)}

    def read_transcript(self, query: str) -> dict[str, Any]:
        """Return transcript chapters matching a timestamp/title query."""
        chapters = self.transcript.find(query)
        if not chapters:
            return {
                "error": "no matching chapter",
                "headings": [
                    f"{c.timestamp} - {c.title}" for c in self.transcript.chapters
                ],
            }
        return {
            "chapters": [
                {
                    "timestamp": c.timestamp,
                    "title": c.title,
                    "text": c.body[:TRANSCRIPT_MAX_CHARS],
                }
                for c in chapters
            ]
        }

    def note_write(self, topic_id: str, content: str) -> dict[str, Any]:
        """Append notes under a topic id in the run's notes directory."""
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", topic_id).strip("-") or "notes"
        path = self.notes_dir / f"{slug}.md"
        existing = path.read_text("utf-8") if path.exists() else ""
        path.write_text(f"{existing}{content.strip()}\n\n", "utf-8")
        return {"path": str(path), "bytes": path.stat().st_size}

    def validate(self, markdown: str) -> dict[str, Any]:
        """Run the deterministic gates and return any problems."""
        problems = validate_critique(markdown, self.content_text, self.registry)
        return {"ok": not problems, "problems": [str(p) for p in problems]}
