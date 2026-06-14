"""Local Ollama chat: a native tool-call loop, then a structured final reply.

Two phases, because Ollama's grammar-constrained `format=` forces JSON tokens
from the first one and so suppresses tool calls -- they can't share a call:
  1. act   -- loop with `tools`, running each tool call until the model stops.
  2. speak -- one `format=schema` call coerces the answer into JSON, e.g.
              {"response": "hi", "emotion": "happy"}.
With no `schema` it behaves like a plain chat and returns the reply text.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("robot.llm")
_client = None
_OPTS = {"num_ctx": 8192, "temperature": 0.7}
MODEL = os.getenv("ROBOT_MODEL", "qwen3.5:4b")

def _get_client():
    global _client
    if _client is None:
        from ollama import Client
        host = os.getenv("OLLAMA_HOST")
        _client = Client(host=host, timeout=60.0) if host else Client(timeout=60.0)
    return _client


def response(messages, *, tools=None, schema=None, history=None, max_steps=6):
    """Run the tool loop, then return a dict matching `schema` (or reply text).

    messages: a list of message dicts, or a plain string treated as the user turn.
    schema: a Pydantic model class or JSON schema dict; the final answer is
            grammar-constrained to it.
    """
    client = _get_client()
    msgs = [{"role": "user", "content": messages}] if isinstance(messages, str) else list(messages)
    fns = {t.__name__: t for t in tools} if tools else {}
    user = next((m["content"] for m in reversed(msgs)
                 if isinstance(m, dict) and m.get("role") == "user"), "")

    # phase 1 -- let the model act with tools until it stops calling them
    content = ""
    for _ in range(max_steps):
        try:
            msg = client.chat(model=MODEL, messages=msgs, tools=tools, options=_OPTS).message
        except Exception as e:
            return _shape(f"Error: {e}", schema)
        if not msg.tool_calls:
            content = msg.content or ""
            break
        msgs.append(msg)  # assistant turn carrying the tool_calls
        for tc in msg.tool_calls:
            msgs.append({"role": "tool", "tool_name": tc.function.name,
                         "content": str(_call(fns, tc))})

    # phase 2 -- coerce the final answer into the schema (grammar-constrained)
    reply = _structured(client, MODEL, msgs, schema, content) if schema else content

    if history is not None:
        text = reply.get("response", "") if isinstance(reply, dict) else reply
        history += [{"role": "user", "content": user},
                    {"role": "assistant", "content": text}]
    return reply


def _structured(client, model, msgs, schema, fallback):
    """Force the final answer to match `schema`, then parse it to a dict."""
    # a Pydantic model class carries its own JSON schema; a dict is used as-is
    fmt = schema.model_json_schema() if hasattr(schema, "model_json_schema") else schema
    try:
        out = client.chat(model=model, messages=msgs, format=fmt,
                          options={**_OPTS, "temperature": 0.3}).message
        return json.loads(out.content or "{}")
    except Exception as e:
        log.warning("structured reply failed: %s", e)
        return _shape(fallback or "...", schema)


def _shape(text, schema):
    """A bare reply in the right shape: a dict when a schema is in play, else text."""
    return {"response": text} if schema else text


def _call(fns, tc):
    fn = fns.get(tc.function.name)
    if not fn:
        return f"unknown tool: {tc.function.name}"
    args = tc.function.arguments
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except (json.JSONDecodeError, ValueError):
            args = {}
    log.info("tool %s(%s)", tc.function.name, args)
    try:
        return fn(**(args or {}))
    except Exception as e:
        return f"error: {e}"


# MARK: Test
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # emoji-safe on Windows
    from pydantic import BaseModel
    class Nums(BaseModel):
        n: list[int]

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    print(f"Ollama | {MODEL}")
    print("\n--- Basic ---")
    print(response("Say hi briefly"))
    print("\n--- Schema ---")
    print(response("Numbers 1-3", schema=Nums))
    print("\n--- Tools ---")
    print(response("What is 2+3?", tools=[add]))