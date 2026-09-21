#!/usr/bin/env python3
"""Run trace: structured per-run event log plus token usage."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunTrace:
    """Collects events, tool calls, and token usage for one run."""

    run_dir: Path
    verbose: bool = False
    started_at: float = field(default_factory=time.time)
    events: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, dict[str, int]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def log(
        self, kind: str, *, agent: str | None = None, message: str = "", **fields: Any
    ) -> None:
        """Append one structured event, echoing it to stdout in verbose mode."""
        event = {
            "t": round(time.time() - self.started_at, 3),
            "event": kind,
            "agent": agent,
            "message": message,
            **fields,
        }
        with self._lock:
            self.events.append(event)
        if self.verbose:
            prefix = f"[{agent}] " if agent else ""
            print(f"[trace] {prefix}{kind}: {message}")

    def record_usage(self, agent: str, model: str, usage: Any) -> None:
        """Accumulate prompt/completion/total tokens for an agent's model call."""
        if usage is None:
            return
        entry = self.usage.setdefault(
            agent, {"calls": 0, "prompt": 0, "completion": 0, "total": 0}
        )
        entry["calls"] += 1
        entry["prompt"] += getattr(usage, "prompt_tokens", 0) or 0
        entry["completion"] += getattr(usage, "completion_tokens", 0) or 0
        entry["total"] += getattr(usage, "total_tokens", 0) or 0
        self.log(
            "llm_usage",
            agent=agent,
            model=model,
            total=getattr(usage, "total_tokens", 0),
        )

    def save(self) -> Path:
        """Write the trace to `trace.json` in the run directory."""
        path = self.run_dir / "trace.json"
        payload = {
            "started_at": self.started_at,
            "duration_seconds": round(time.time() - self.started_at, 3),
            "usage": self.usage,
            "events": self.events,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
        return path
