"""
Groq API client — uses the OpenAI-compatible endpoint.
Models:
  Tier 2 (small): openai/gpt-oss-20b
  Tier 3 (large): openai/gpt-oss-120b

Previous model IDs (llama-3.1-8b-instant, llama-3.3-70b-versatile) were
moved to Enterprise-only ("Contact Sales") on 16 August 2026 and return
HTTP 404 on developer/free keys. The replacements are the current
production models on the developer tier as of the Groq models page.

Falls back to the simulator if GROQ_API_KEY is not set.

Reasoning-model notes (gpt-oss-20b / gpt-oss-120b):
  - Both are reasoning models that spend completion tokens on an internal
    chain-of-thought (CoT) before writing any visible output.
  - With max_completion_tokens=1024 the CoT can exhaust the entire budget,
    leaving message.content = "". The budget is raised to 2048.
  - include_reasoning=False (Groq-specific, passed via extra_body) tells
    the API to omit the CoT from the response, saving output tokens and
    preventing the raw <think> block from reaching the verifier.
  - reasoning_effort="low" (also Groq-specific, via extra_body) caps the
    number of reasoning tokens the model spends, giving more of the budget
    to actual content. Supported values for gpt-oss: low / medium / high.
  - reasoning_format is NOT supported for gpt-oss models on Groq; do not
    send it or the request will be rejected with HTTP 400.
  - The Groq docs recommend avoiding system prompts for gpt-oss models;
    all instructions should be in the user message. The system-message slot
    is still populated here (the API accepts it) but it is kept minimal.
"""
from __future__ import annotations
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Published per-token list prices (USD) — groq.com/pricing, Sep 2026.
# openai/gpt-oss-20b:  $0.075 input / $0.30 output  per 1M tokens
# openai/gpt-oss-120b: $0.15  input / $0.60 output  per 1M tokens
_PRICES = {
    "openai/gpt-oss-20b":  {"prompt": 0.075e-6, "completion": 0.30e-6},
    "openai/gpt-oss-120b": {"prompt": 0.15e-6,  "completion": 0.60e-6},
}

SMALL_MODEL = "openai/gpt-oss-20b"
LARGE_MODEL = "openai/gpt-oss-120b"

# Maximum tokens the model may produce (reasoning + content combined).
# Raised from 1024 → 2048 because gpt-oss reasoning models spend completion
# tokens on an internal chain-of-thought before any visible content is
# written. At 1024 the CoT can exhaust the budget entirely, yielding an
# empty message.content and a spurious verifier failure.
_MAX_COMPLETION_TOKENS = 2048

_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "When uncertain, include a confidence field at the end of your response like: confidence: 75. "
    "Be concise and accurate."
)

# Groq-specific extra-body fields sent for gpt-oss reasoning models.
# These keys are not in the openai SDK's typed interface (v1.57.2) so they
# must be forwarded via extra_body, which the SDK merges into the raw JSON
# request body before sending.
#   include_reasoning=False  — omit the CoT block from the response; only
#                              the final answer is returned in message.content.
#   reasoning_effort="low"   — cap reasoning tokens to a low level, leaving
#                              more of the 2048-token budget for content.
#                              Supported by gpt-oss-20b and gpt-oss-120b.
#                              NOT supported by Qwen; safe to send to both
#                              gpt-oss tiers.
_GROQ_REASONING_EXTRA_BODY = {
    "include_reasoning": False,
    "reasoning_effort":  "low",
}


def _has_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def _compute_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    prices = _PRICES.get(model, {"prompt": 0.0, "completion": 0.0})
    return in_tokens * prices["prompt"] + out_tokens * prices["completion"]


def call_small(query: str, system_prompt: str = _SYSTEM_PROMPT):
    if not _has_key():
        logger.debug("No GROQ_API_KEY — using simulator for small model")
        from clients.simulator import call_small as sim
        return sim(query, system_prompt)
    return _call(SMALL_MODEL, query, system_prompt)


def call_large(query: str, system_prompt: str = _SYSTEM_PROMPT):
    if not _has_key():
        logger.debug("No GROQ_API_KEY — using simulator for large model")
        from clients.simulator import call_large as sim
        return sim(query, system_prompt)
    return _call(LARGE_MODEL, query, system_prompt)


def _call(model: str, query: str, system_prompt: str):
    from clients.simulator import ModelResponse
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        t0 = time.time()
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": query},
            ],
            temperature=0.3,
            max_completion_tokens=_MAX_COMPLETION_TOKENS,
            extra_body=_GROQ_REASONING_EXTRA_BODY,
        )
        latency_ms = int((time.time() - t0) * 1000)
        content    = completion.choices[0].message.content or ""

        # ── Diagnostic logging ────────────────────────────────────────────
        finish_reason = completion.choices[0].finish_reason
        in_tokens  = completion.usage.prompt_tokens     if completion.usage else 0
        out_tokens = completion.usage.completion_tokens if completion.usage else 0

        # reasoning_tokens lives inside completion_tokens_details, which
        # is populated by Groq for gpt-oss models when include_reasoning
        # is True (or omitted). With include_reasoning=False, Groq may
        # still report reasoning_tokens in usage so we read it defensively.
        reasoning_tokens: Optional[int] = None
        if completion.usage and completion.usage.completion_tokens_details:
            reasoning_tokens = completion.usage.completion_tokens_details.reasoning_tokens

        logger.info(
            "Groq %s: finish_reason=%s in=%d out=%d"
            " (reasoning=%s) budget=%d cost=$%.6f latency=%dms",
            model,
            finish_reason,
            in_tokens,
            out_tokens,
            reasoning_tokens if reasoning_tokens is not None else "n/a",
            _MAX_COMPLETION_TOKENS,
            _compute_cost(model, in_tokens, out_tokens),
            latency_ms,
        )

        if finish_reason == "length":
            logger.warning(
                "Groq %s hit token budget (%d tokens). "
                "content_len=%d reasoning_tokens=%s. "
                "Response may be empty or truncated.",
                model,
                _MAX_COMPLETION_TOKENS,
                len(content),
                reasoning_tokens if reasoning_tokens is not None else "n/a",
            )
        # ── End diagnostic logging ────────────────────────────────────────

        cost = _compute_cost(model, in_tokens, out_tokens)
        return ModelResponse(
            content=content,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_ms,
            provider_cost_usd=cost,
            cost_source="groq_list_price",
        )
    except Exception as exc:
        logger.error("Groq API call failed: %s — falling back to simulator", exc)
        from clients.simulator import call_small, call_large
        if model == SMALL_MODEL:
            return call_small(query, system_prompt)
        return call_large(query, system_prompt)
