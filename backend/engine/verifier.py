"""
Stage 6 — Response Verifier

Structural checks + confidence extraction.
Run only on small_model attempts.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Refusal phrases that indicate the model declined
_REFUSAL_PHRASES = [
    "i cannot", "i'm unable", "i am unable", "i can't",
    "as an ai", "as a language model", "i don't have access",
    "i'm not able", "i am not able", "i must decline",
    "i apologize, but i cannot",
]

# Degenerate repetition: same 5-gram repeated >= 3 times
def _has_degenerate_repetition(text: str) -> bool:
    words = text.lower().split()
    if len(words) < 15:
        return False
    fivegrams = [tuple(words[i:i+5]) for i in range(len(words)-4)]
    counts: dict[tuple, int] = {}
    for g in fivegrams:
        counts[g] = counts.get(g, 0) + 1
        if counts[g] >= 3:
            return True
    return False


# Words that appear at the start of questions or instructions but carry no
# information about what the *response* should contain.  Matching them as
# required entities in the response causes false rejections for concise,
# paraphrased, or differently-structured correct answers.
#
# Sentence-starter question words:
_QUESTION_WORDS = frozenset({
    "what", "where", "when", "who", "whom", "whose",
    "which", "why", "how",
})

# Common instruction/imperative verbs that open prompts.  A valid response
# to "Give a short answer" is never required to contain the word "give".
_INSTRUCTION_VERBS = frozenset({
    "give", "explain", "write", "list", "describe", "translate",
    "summarize", "summarise", "analyze", "analyse", "compare",
    "find", "show", "tell", "define", "calculate", "compute",
    "create", "generate", "provide", "state", "identify",
    "evaluate", "assess", "critique", "review", "rewrite",
    "paraphrase", "convert", "format", "draft", "outline",
})

# Combined stopword set for entity extraction
_ENTITY_STOPWORDS = _QUESTION_WORDS | _INSTRUCTION_VERBS


def _extract_entities(query: str) -> list[str]:
    """
    Extract meaningful subject-domain entities from a query.

    Matches capitalised proper-noun-style words and 3+-digit numbers, then
    filters out sentence-starter question words (What, Where, How, …) and
    common instruction verbs (Give, Explain, Write, …).  These are capitalised
    only because of their sentence position, not because they name a domain
    concept.  Requiring them in the response causes false rejections for
    concise or paraphrased correct answers.

    Returns up to 5 entities (lower-cased).
    """
    tokens = re.findall(r"\b[A-Z][a-z]+\b|\b\d{3,}\b", query)
    entities = [
        t.lower() for t in tokens
        if t.lower() not in _ENTITY_STOPWORDS
    ]
    return entities[:5]


class VerificationResult:
    __slots__ = ("passed", "reason", "confidence")

    def __init__(self, passed: bool, reason: str = "", confidence: Optional[int] = None):
        self.passed     = passed
        self.reason     = reason
        self.confidence = confidence


def verify_response(
    query: str,
    response: str,
    requested_json: bool = False,
) -> VerificationResult:
    """
    Structural verification for small-model responses.
    Returns VerificationResult(passed=False, reason=...) on any failure.
    """
    # 1. Empty or too short
    if not response or len(response.strip()) < 5:
        return VerificationResult(False, "Empty or truncated response")

    # 2. Truncation heuristic (ends mid-sentence without any punctuation)
    stripped = response.strip()
    if len(stripped) > 100 and not re.search(r"[.!?»)\]`\"]$", stripped[-3:]):
        if not stripped.endswith("```") and not stripped.endswith("---"):
            logger.debug("Verifier: possible truncation for %r", stripped[-30:])
            # soft fail only — don't hard-fail on truncation alone

    # 3. Refusal phrases
    lower = response.lower()
    for phrase in _REFUSAL_PHRASES:
        if phrase in lower:
            return VerificationResult(False, f"Response contains refusal phrase: '{phrase}'")

    # 4. Requested JSON but failed to parse
    if requested_json:
        # strip markdown code fence if present
        content = re.sub(r"```(?:json)?\s*", "", response).strip().rstrip("`")
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            return VerificationResult(False, f"Requested JSON but parse failed: {exc}")

    # 5. Missing key entities that appeared in the query
    entities = _extract_entities(query)
    if entities:
        missing = [e for e in entities if e not in lower]
        # Allow up to 40% missing (loose check — entities may be paraphrased)
        if len(missing) > 0.6 * len(entities) and len(entities) >= 3:
            return VerificationResult(
                False,
                f"Response appears unrelated to query: missing entities {missing[:3]}",
            )

    # 6. Degenerate repetition
    if _has_degenerate_repetition(response):
        return VerificationResult(False, "Degenerate repetition detected in response")

    # 7. Confidence extraction from structured response
    confidence_match = re.search(r"confidence[:\s]+(\d{1,3})", response, re.I)
    confidence: Optional[int] = None
    if confidence_match:
        confidence = int(confidence_match.group(1))
        if confidence < 60:
            return VerificationResult(
                False,
                f"Self-reported confidence {confidence}% below threshold (60%)",
                confidence=confidence,
            )

    return VerificationResult(True, "All structural checks passed", confidence=confidence)
