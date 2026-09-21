#!/usr/bin/env python3
"""Generic ReAct tool-calling loop over the OpenAI-compatible endpoint.

`run_agent` drives one agent: it sends the system prompt plus a user message,
executes any requested tools through a `Toolbox`, feeds the results back, and
returns the model's final text. When the tool-call budget is exhausted, tools
are withheld from the next request so the agent must produce a final answer.
"""

from __future__ import annotations

import re
from pathlib import Path
from trace import RunTrace

from config import Settings
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tools import Toolbox

FENCE_RE = re.compile(r"^\s*```(?:\w*)\s*$", re.MULTILINE)

RETRYABLE = (APIConnectionError, RateLimitError, APIStatusError)


def make_client(settings: Settings) -> OpenAI:
    """Create the shared OpenAI client for the configured endpoint."""
    return OpenAI(base_url=settings.base_url, api_key=settings.api_key)


def strip_fences(text: str) -> str:
    """Remove Markdown code fences and normalize trailing whitespace."""
    return FENCE_RE.sub("", text).strip()


@retry(
    retry=retry_if_exception_type(RETRYABLE),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    reraise=True,
)
def _create(client: OpenAI, **kwargs):
    """Call the chat completions endpoint with retry/backoff."""
    return client.chat.completions.create(**kwargs)


def _assistant_message(message) -> dict:
    """Serialize an assistant message (including tool calls) as a dict."""
    payload: dict = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


def run_agent(
    client: OpenAI,
    *,
    model: str,
    agent: str,
    system_prompt: str,
    user_message: str,
    toolbox: Toolbox,
    tool_names: list[str],
    max_tool_calls: int,
    trace: RunTrace,
) -> str:
    """Run one agent to completion and return its final text answer."""
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    specs = toolbox.specs(tool_names) if tool_names else []
    calls_used = 0
    trace.log("agent_start", agent=agent, model=model, tools=tool_names)

    while True:
        allow_tools = bool(specs) and calls_used < max_tool_calls
        kwargs: dict = {"model": model, "messages": messages}
        if allow_tools:
            kwargs["tools"] = specs

        response = _create(client, **kwargs)
        trace.record_usage(agent, model, getattr(response, "usage", None))
        message = response.choices[0].message

        if not message.tool_calls:
            content = message.content or ""
            trace.log(
                "agent_done", agent=agent, tool_calls=calls_used, chars=len(content)
            )
            return content

        messages.append(_assistant_message(message))
        for call in message.tool_calls:
            calls_used += 1
            if calls_used > max_tool_calls:
                result = (
                    '{"error": "tool budget exhausted; produce your final answer now"}'
                )
            else:
                result = toolbox.dispatch(call.function.name, call.function.arguments)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )
            trace.log(
                "tool_result",
                agent=agent,
                message=call.function.name,
                chars=len(result),
            )


def load_prompt(path: Path) -> str:
    """Read a prompt file and exit with a clear error when missing."""
    if not path.exists():
        raise SystemExit(f"[error] missing prompt file: {path}")
    return path.read_text("utf-8").strip()
