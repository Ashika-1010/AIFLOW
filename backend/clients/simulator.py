"""
Fallback simulator — used when no API key is configured.
Produces realistic token counts and latency without any external calls.
Cost is reported as 0.0 with cost_source: "simulated" (in audit only).
"""
from __future__ import annotations
import random
import re
import time
from dataclasses import dataclass


@dataclass
class ModelResponse:
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    provider_cost_usd: float
    cost_source: str = "simulated"


def _count_tokens(text: str) -> int:
    """Approximate token count via tiktoken."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text.split()))


_SMALL_TEMPLATES = [
    "Here is a concise answer to your question: {topic}. "
    "The key points to consider are the context and scope of the request. "
    "AIFlow processed this via the small model pathway with high confidence.",

    "Regarding {topic}: this is handled efficiently by the 8B-class model. "
    "The response meets all quality thresholds and structural verification checks.",

    "To address your request about {topic}: "
    "The answer is derived from the model's training data. "
    "This pathway was selected because the complexity score was within small-model range.",
]

_LARGE_TEMPLATES = [
    "Comprehensive analysis of {topic}:\n\n"
    "1. Core consideration: The fundamental principles involve multi-layered reasoning "
    "across several interconnected domains.\n"
    "2. Trade-offs: While the primary approach offers efficiency, edge cases require "
    "careful handling to maintain correctness.\n"
    "3. Recommendation: Based on the available context, the optimal strategy balances "
    "computational cost with output fidelity.\n\n"
    "This analysis was performed by the large 70B-class model due to high complexity.",

    "Detailed response for {topic}:\n\n"
    "The question requires synthesising information from multiple frameworks. "
    "Key factors include the specific constraints, the operational context, and "
    "the desired outcome fidelity. The large model tier was selected because the "
    "complexity classifier assigned a sufficiency score below the quality floor.",
]


def _extract_topic(query: str) -> str:
    """Extract a short topic fragment from the query."""
    q = re.sub(r"^(what is|explain|describe|analyze|write|generate|"
               r"summarize|list|compare|translate|rewrite)\s+", "", query, flags=re.I)
    words = q.split()
    return " ".join(words[:6]) if words else query[:40]


def call_small(query: str, system_prompt: str = "") -> ModelResponse:
    """Simulate a small-model (8B) response."""
    latency_ms = int(random.uniform(300, 700))
    time.sleep(latency_ms / 1000.0)

    topic    = _extract_topic(query)
    template = random.choice(_SMALL_TEMPLATES)
    content  = template.format(topic=topic)

    in_tokens  = _count_tokens((system_prompt + "\n" + query).strip())
    out_tokens = _count_tokens(content)

    return ModelResponse(
        content=content,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        latency_ms=latency_ms,
        provider_cost_usd=0.0,
        cost_source="simulated",
    )


def call_large(query: str, system_prompt: str = "") -> ModelResponse:
    """Simulate a large-model (70B) response."""
    latency_ms = int(random.uniform(1400, 4200))
    time.sleep(latency_ms / 1000.0)

    topic    = _extract_topic(query)
    template = random.choice(_LARGE_TEMPLATES)
    content  = template.format(topic=topic)

    in_tokens  = _count_tokens((system_prompt + "\n" + query).strip())
    out_tokens = _count_tokens(content)

    return ModelResponse(
        content=content,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        latency_ms=latency_ms,
        provider_cost_usd=0.0,
        cost_source="simulated",
    )
