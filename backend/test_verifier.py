"""
Tests for the response verifier — engine/verifier.py

Covers:
  1. AF-0330 regression — "What is the difference between a list and a tuple
     in Python? Give a short answer." must not be rejected due to missing
     stopwords 'what' or 'give'.
  2. Stopword filtering — question words and instruction verbs are excluded
     from required-entity matching.
  3. Valid answer formats — concise, paraphrased, Markdown, and table answers
     that do not echo the query verbatim must still pass.
  4. Genuine rejections — refusal phrases, empty responses, and degenerate
     repetition must still be caught.
  5. Multi-entity rejection — queries with 3+ subject-domain entities should
     still reject clearly unrelated responses.
  6. _extract_entities — correct output for representative queries.

Run from backend/:  .venv/Scripts/python.exe test_verifier.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engine.verifier import verify_response, _extract_entities, _ENTITY_STOPWORDS

# ── helpers ────────────────────────────────────────────────────────────────────
all_pass = True


def check(label: str, cond: bool, detail: str = "") -> bool:
    global all_pass
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}]  {label}" + (f"  —  {detail}" if detail else ""))
    if not cond:
        all_pass = False
    return cond


def passes(query: str, response: str) -> bool:
    return verify_response(query, response).passed


def rejects(query: str, response: str) -> bool:
    return not verify_response(query, response).passed


def reason(query: str, response: str) -> str:
    return verify_response(query, response).reason


# ══════════════════════════════════════════════════════════════════════════════
print("\n══════════════════════════════════════════════════════════════")
print("  Response Verifier Tests")
print("══════════════════════════════════════════════════════════════\n")

AF0330_QUERY = (
    "What is the difference between a list and a tuple in Python? "
    "Give a short answer."
)

# ── 1. AF-0330 regression ─────────────────────────────────────────────────────
print("① AF-0330 regression — stopwords must not be required entities")

entities = _extract_entities(AF0330_QUERY)
check("'what' excluded from entities",  "what" not in entities,  str(entities))
check("'give' excluded from entities",  "give" not in entities,  str(entities))
check("'python' retained as entity",    "python" in entities,    str(entities))
check("entity list has exactly 1 item", len(entities) == 1,      str(entities))

# Concise paraphrased answer — does not echo 'what', 'give', or 'python'
CONCISE = (
    "Lists are mutable sequences; tuples are immutable. "
    "Use a list when you need to modify the collection, a tuple when data should remain fixed."
)
check("concise paraphrased answer passes",
      passes(AF0330_QUERY, CONCISE), reason(AF0330_QUERY, CONCISE))

# ── 2. Valid answer formats ────────────────────────────────────────────────────
print("\n② Valid answer formats must not be rejected")

MARKDOWN_TABLE = (
    "| Feature | List | Tuple |\n"
    "|---------|------|-------|\n"
    "| Mutable | Yes  | No    |\n"
    "| Syntax  | []   | ()    |\n"
    "| Hashable| No   | Yes   |"
)
check("Markdown table answer passes",
      passes(AF0330_QUERY, MARKDOWN_TABLE), reason(AF0330_QUERY, MARKDOWN_TABLE))

BULLET_WITH_PYTHON = (
    "- **List**: mutable, defined with `[]`, supports `append`/`remove`\n"
    "- **Tuple**: immutable, defined with `()`, hashable — usable as dict keys\n"
    "Both are ordered sequences in Python."
)
check("Bullet-point answer (mentions Python) passes",
      passes(AF0330_QUERY, BULLET_WITH_PYTHON))

SHORT_NO_PYTHON = (
    "A list can be changed after creation (mutable); a tuple cannot (immutable). "
    "Tuples are faster and can serve as dictionary keys."
)
check("Short answer without the word 'python' passes",
      passes(AF0330_QUERY, SHORT_NO_PYTHON), reason(AF0330_QUERY, SHORT_NO_PYTHON))

ONE_LINER = "Lists are mutable; tuples are immutable."
check("One-liner answer (≥ 5 chars) passes", passes(AF0330_QUERY, ONE_LINER))

# ── 3. Stopword set — spot-checks ─────────────────────────────────────────────
print("\n③ Stopword filtering")

# Question words
for word in ("what", "where", "when", "who", "whom", "whose", "which", "why", "how"):
    check(f"'{word}' in _ENTITY_STOPWORDS", word in _ENTITY_STOPWORDS)

# Instruction verbs
for word in ("give", "explain", "write", "list", "describe", "translate",
             "summarize", "analyze", "compare", "generate"):
    check(f"'{word}' in _ENTITY_STOPWORDS", word in _ENTITY_STOPWORDS)

# ── 4. _extract_entities — representative queries ─────────────────────────────
print("\n④ _extract_entities output")

check("'Explain the Raft consensus algorithm' → ['raft']",
      _extract_entities("Explain the Raft consensus algorithm.") == ["raft"])

check("'Compare Django, Flask, and FastAPI' → ['django','flask'] (FastAPI/REST not matched by regex)",
      _extract_entities("Compare Django, Flask, and FastAPI for REST APIs.") == ["django", "flask"])

check("'What is 27 × 43?' → [] (only 'What', which is a stopword)",
      _extract_entities("What is 27 × 43?") == [])

check("'How does the Bitcoin blockchain work?' → ['bitcoin']",
      _extract_entities("How does the Bitcoin blockchain work?") == ["bitcoin"])

check("'Write a Python function using Pandas' → ['python', 'pandas']",
      _extract_entities("Write a Python function using Pandas.") == ["python", "pandas"])

# Multi-sentence with both instruction verb and subject nouns
check("'List differences between SQL and NoSQL' → [] (SQL/NoSQL all-caps not matched; 'List' filtered as instruction verb)",
      _extract_entities("List the differences between SQL and NoSQL databases.") == [])
check("'list' instruction verb filtered; all-caps SQL not matched by regex",
      "list" not in _extract_entities("List the differences between SQL and NoSQL databases.")
      and "sql" not in _extract_entities("List the differences between SQL and NoSQL databases."))

# ── 5. Genuine rejections still fire ──────────────────────────────────────────
print("\n⑤ Genuine rejections — quality safeguards preserved")

check("Empty string rejected",
      rejects(AF0330_QUERY, ""))

check("Single word rejected (< 5 chars)",
      rejects(AF0330_QUERY, "Yes"))

check("'i cannot' refusal rejected",
      rejects(AF0330_QUERY, "I cannot answer questions about Python data structures."))

check("'as an ai' refusal rejected",
      rejects(AF0330_QUERY, "As an AI, I am unable to provide a comparison here."))

check("Degenerate repetition rejected",
      rejects(
          AF0330_QUERY,
          ("Lists are mutable sequences in Python. " * 8),
      ))

# ── 6. Multi-entity query rejects unrelated responses ────────────────────────
print("\n⑥ Multi-entity queries — unrelated responses still rejected")

MULTI_Q = "Compare Django, Flask, and FastAPI for building REST APIs in Python."
multi_entities = _extract_entities(MULTI_Q)
check("Multi-entity query has ≥ 3 entities (activates check)",
      len(multi_entities) >= 3, str(multi_entities))

check("Unrelated response (capital city) rejected for multi-entity query",
      rejects(MULTI_Q,
              "The capital of France is Paris. It is known for the Eiffel Tower "
              "and world-famous cuisine and attracts millions of tourists every year."))

check("Correct framework comparison passes",
      passes(MULTI_Q,
             "Django is a full-stack framework suited for complex applications. "
             "Flask is lightweight and minimalist. FastAPI is the fastest, with "
             "automatic OpenAPI docs and async support, ideal for modern Python APIs."))

# Second multi-entity query
SECURITY_Q = "How does the SSL handshake work between a Client and a Server?"
sec_entities = _extract_entities(SECURITY_Q)
check("SSL query entities exclude 'how'", "how" not in sec_entities)
check("SSL query entities: 'Client' and 'Server' retained (SSL all-caps not matched by regex)",
      "client" in sec_entities and "server" in sec_entities, str(sec_entities))

check("Completely unrelated answer rejected (3 domain entities: django, flask, python)",
      rejects(
          "Compare Django, Flask, and FastAPI for building REST APIs in Python.",
          "Cats are mammals. They have four legs and are known for being independent pets."
          " Domestic cats are one of the most popular pets in the world worldwide.",
      ))

# ── 7. Entity check requires ≥ 3 entities to fire ─────────────────────────────
print("\n⑦ Entity check gate — requires ≥ 3 entities")

# AF-0330 has only 1 entity after filtering; the check should not fire for
# a response that is topically unrelated but structurally valid.  This is
# intentional conservative behaviour: with only 1 entity there is insufficient
# signal for reliable entity matching.
UNRELATED_BUT_VALID = (
    "The capital of France is Paris. It has a population of about 2 million "
    "people and is famous for the Eiffel Tower and its world-class museums."
)
result_unrelated = verify_response(AF0330_QUERY, UNRELATED_BUT_VALID)
check("1-entity query: entity check does NOT fire for unrelated (≥3 gate)",
      "missing entities" not in (result_unrelated.reason or ""),
      f"reason: {result_unrelated.reason}")

# (The response still passes other checks because it's structurally fine —
#  this is acceptable; the entity check was never the sole defence.)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
if all_pass:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED — see above")
print("══════════════════════════════════════════════════════════════\n")
sys.exit(0 if all_pass else 1)
