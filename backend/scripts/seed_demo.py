"""
Seed the AIFlow database with 24 representative receipts matching the
pitch-deck fixture set (AF-0261 to AF-0284).

Run from the backend/ directory:
  python scripts/seed_demo.py

This bypasses the live pipeline and inserts the fixtures directly so
the frontend shows real, inspectable data immediately after startup.
"""
import json
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from db import init_db, SessionLocal, ReceiptORM, CacheEntryORM
import hashlib, re

FIXTURES = [
    {
        "id": "AF-0284", "timestamp": "2026-09-19T09:42:15Z",
        "query": "What is 27 × 43?", "pathway": "deterministic",
        "pathway_steps": ["Request","Analysis","Deterministic Gate","AST Safe Eval","Response"],
        "reason": "Arithmetic expression detected", "complexity_score": 0.02,
        "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 8, "output_tokens": 5, "latency_ms": 2,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.0000005, "central": 0.000001, "high": 0.000003},
        "baseline_energy_wh": 0.081, "router_overhead_wh": 0.0000004,
        "escalation_regret_wh": 0.0, "response": "What is 27 × 43 = 1161",
        "region": "IN",
    },
    {
        "id": "AF-0283", "timestamp": "2026-09-19T09:40:02Z",
        "query": "Rewrite this paragraph in a professional tone while preserving the original meaning.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Verification","Response"],
        "reason": "Routed to small model: p_small=0.87 ≥ floor 0.60; no document attached; 34 prompt tokens",
        "complexity_score": 0.21, "quality_floor": 0.60, "predicted_sufficiency": 0.87,
        "verification": "passed", "escalated": False,
        "input_tokens": 184, "output_tokens": 96, "latency_ms": 421,
        "provider_cost_usd": 0.0008,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.081, "router_overhead_wh": 0.0000012,
        "escalation_regret_wh": 0.0,
        "response": "Here is the revised paragraph: \"Please find attached the updated quarterly performance report. Should you require further clarification regarding the financial telemetry or projections, please feel free to reach out.\"",
        "region": "IN",
    },
    {
        "id": "AF-0282", "timestamp": "2026-09-19T09:37:44Z",
        "query": "What is the capital of France?", "pathway": "cache",
        "pathway_steps": ["Request","Analysis","Semantic Cache","Response"],
        "reason": "Semantic cache hit, cosine 0.96",
        "complexity_score": 0.04, "quality_floor": 0.60, "predicted_sufficiency": 0.99,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 7, "output_tokens": 6, "latency_ms": 8,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.000012, "central": 0.000020, "high": 0.000040},
        "baseline_energy_wh": 0.065, "router_overhead_wh": 0.0000008,
        "escalation_regret_wh": 0.0, "response": "The capital of France is Paris.",
        "region": "IN",
    },
    {
        "id": "AF-0281", "timestamp": "2026-09-19T09:35:10Z",
        "query": "Analyze this technical document and summarize the trade-offs between Raft and Paxos consensus algorithms.",
        "pathway": "large_model",
        "pathway_steps": ["Request","Analysis","Complexity Router","Large Model (70B+)","Response"],
        "reason": "Routed to large model: technical document analysis requested; complexity score 0.89 > threshold",
        "complexity_score": 0.89, "quality_floor": 0.60, "predicted_sufficiency": 0.32,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 1420, "output_tokens": 610, "latency_ms": 2450,
        "provider_cost_usd": 0.0182,
        "energy_wh": {"low": 0.310, "central": 0.580, "high": 1.100},
        "baseline_energy_wh": 0.580, "router_overhead_wh": 0.0000024,
        "escalation_regret_wh": 0.0,
        "response": "Summary of Consensus Trade-offs:\n1. Understandability: Raft decomposes consensus into leader election, log replication, and safety, making state transitions formal and auditable.\n2. Performance: Multi-Paxos allows pipelining under asymmetric network partitions with fewer round-trips when leadership is stable.\n3. Implementation Complexity: Multi-Paxos corner cases in log compaction and view changes introduce significant subtle failure states compared to Raft.",
        "region": "IN",
    },
    {
        "id": "AF-0280", "timestamp": "2026-09-19T09:31:55Z",
        "query": "Explain quantum entanglement simply with formal mathematical wave function collapse equations.",
        "pathway": "escalated",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Quality Verification","Escalate → Large Model (70B+)","Response"],
        "reason": "Self-reported confidence 41% below threshold; mathematical notation check failed on small tier",
        "complexity_score": 0.72, "quality_floor": 0.60, "predicted_sufficiency": 0.54,
        "verification": "failed", "escalated": True,
        "input_tokens": 410, "output_tokens": 380, "latency_ms": 3120,
        "provider_cost_usd": 0.0145,
        "energy_wh": {"low": 0.310, "central": 0.580, "high": 1.100},
        "baseline_energy_wh": 0.580, "router_overhead_wh": 0.0000020,
        "escalation_regret_wh": 0.0180,
        "response": "Quantum entanglement occurs when two particles become entangled such that the state of one cannot be described independently of the other:\n|ψ⟩ = (1/√2)(|00⟩ + |11⟩)\nUpon measurement of the first qubit in the computational basis, the composite wave function collapses instantly, correlating the second qubit with probability 1.",
        "region": "IN",
    },
    {
        "id": "AF-0279", "timestamp": "2026-09-19T09:28:40Z",
        "query": "Convert 120 miles per hour to kilometers per hour", "pathway": "deterministic",
        "pathway_steps": ["Request","Analysis","Deterministic Gate","Pint Unit Converter","Response"],
        "reason": "Unit conversion detected", "complexity_score": 0.01,
        "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 10, "output_tokens": 7, "latency_ms": 3,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.0000005, "central": 0.000001, "high": 0.000003},
        "baseline_energy_wh": 0.072, "router_overhead_wh": 0.0000004,
        "escalation_regret_wh": 0.0, "response": "120 mph = 193.121 km/h",
        "region": "IN",
    },
    {
        "id": "AF-0278", "timestamp": "2026-09-19T09:24:18Z",
        "query": "Draft a polite follow-up email after a job interview for a frontend developer role.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Verification","Response"],
        "reason": "Routed to small model: p_small=0.91 ≥ floor 0.60; standard template generation",
        "complexity_score": 0.18, "quality_floor": 0.60, "predicted_sufficiency": 0.91,
        "verification": "passed", "escalated": False,
        "input_tokens": 68, "output_tokens": 142, "latency_ms": 380,
        "provider_cost_usd": 0.0009,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.115, "router_overhead_wh": 0.0000010,
        "escalation_regret_wh": 0.0,
        "response": "Subject: Thank You - Frontend Developer Interview\n\nDear Team,\nThank you for the opportunity to speak with you today regarding the Frontend Developer position. I enjoyed learning more about your engineering roadmap and feel confident my background in React and design systems aligns well with your goals.\n\nBest regards,\nCandidate",
        "region": "IN",
    },
    {
        "id": "AF-0277", "timestamp": "2026-09-19T09:20:00Z",
        "query": "What is the speed of light in a vacuum?", "pathway": "cache",
        "pathway_steps": ["Request","Analysis","Semantic Cache","Response"],
        "reason": "Semantic cache hit, cosine 0.98",
        "complexity_score": 0.02, "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 9, "output_tokens": 8, "latency_ms": 6,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.000010, "central": 0.000020, "high": 0.000038},
        "baseline_energy_wh": 0.068, "router_overhead_wh": 0.0000006,
        "escalation_regret_wh": 0.0,
        "response": "The speed of light in a vacuum is exactly 299,792,458 meters per second (~3.00 × 10⁸ m/s).",
        "region": "IN",
    },
    {
        "id": "AF-0276", "timestamp": "2026-09-19T09:16:32Z",
        "query": "What is our internal policy on API rate limits for free-tier users?",
        "pathway": "retrieval",
        "pathway_steps": ["Request","Analysis","Local Corpus Vector Search","Corpus Grounding","Response"],
        "reason": "Internal documentation lookup matched local policy corpus (cosine 0.94)",
        "complexity_score": 0.15, "quality_floor": 0.60, "predicted_sufficiency": 0.95,
        "verification": "passed", "escalated": False,
        "input_tokens": 48, "output_tokens": 32, "latency_ms": 84,
        "provider_cost_usd": 0.0001,
        "energy_wh": {"low": 0.00012, "central": 0.00030, "high": 0.00062},
        "baseline_energy_wh": 0.075, "router_overhead_wh": 0.0000011,
        "escalation_regret_wh": 0.0,
        "response": "According to the internal API Developer Policy (§4.2), free-tier keys are limited to 60 requests/minute and 10,000 requests/day.",
        "region": "IN",
    },
    {
        "id": "AF-0275", "timestamp": "2026-09-19T09:12:10Z",
        "query": "Format this list of names into a clean Markdown table with columns First Name and Last Name.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","JSON/Markdown Structural Check","Response"],
        "reason": "Routed to small model: p_small=0.94 ≥ floor 0.60; structural transformation task",
        "complexity_score": 0.12, "quality_floor": 0.60, "predicted_sufficiency": 0.94,
        "verification": "passed", "escalated": False,
        "input_tokens": 52, "output_tokens": 48, "latency_ms": 340,
        "provider_cost_usd": 0.0005,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.078, "router_overhead_wh": 0.0000009,
        "escalation_regret_wh": 0.0,
        "response": "| First Name | Last Name |\n|---|---|\n| Ada | Lovelace |\n| Alan | Turing |\n| Claude | Shannon |",
        "region": "IN",
    },
    {
        "id": "AF-0274", "timestamp": "2026-09-19T09:07:05Z",
        "query": "How many days between 2026-01-01 and 2026-09-19?", "pathway": "deterministic",
        "pathway_steps": ["Request","Analysis","Deterministic Gate","Dateutil Engine","Response"],
        "reason": "Date arithmetic detected", "complexity_score": 0.03,
        "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 14, "output_tokens": 6, "latency_ms": 4,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.0000005, "central": 0.000001, "high": 0.000003},
        "baseline_energy_wh": 0.068, "router_overhead_wh": 0.0000004,
        "escalation_regret_wh": 0.0, "response": "261 days",
        "region": "IN",
    },
    {
        "id": "AF-0273", "timestamp": "2026-09-19T09:02:40Z",
        "query": "Critique the philosophical viability of modal realism as proposed by David Lewis against ersatz modal realism.",
        "pathway": "large_model",
        "pathway_steps": ["Request","Analysis","Complexity Router","Large Model (70B+)","Response"],
        "reason": "Routed to large model: complex abstract philosophical reasoning, low small-model sufficiency (0.24)",
        "complexity_score": 0.94, "quality_floor": 0.60, "predicted_sufficiency": 0.24,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 210, "output_tokens": 480, "latency_ms": 2980,
        "provider_cost_usd": 0.0152,
        "energy_wh": {"low": 0.310, "central": 0.580, "high": 1.100},
        "baseline_energy_wh": 0.580, "router_overhead_wh": 0.0000022,
        "escalation_regret_wh": 0.0,
        "response": "David Lewis's genuine modal realism posits that possible worlds are concrete spatiotemporal entities physically isolated from our own. Ersatzism treats possible worlds as abstract linguistic or set-theoretic representations. While Lewis avoids circular definitions of modality, ersatzism aligns more naturally with standard epistemological intuitions.",
        "region": "IN",
    },
    {
        "id": "AF-0272", "timestamp": "2026-09-19T08:58:12Z",
        "query": "Explain the difference between let, const, and var in modern JavaScript in three bullet points.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Verification","Response"],
        "reason": "Routed to small model: p_small=0.88 ≥ floor 0.60; concise technical overview",
        "complexity_score": 0.25, "quality_floor": 0.60, "predicted_sufficiency": 0.88,
        "verification": "passed", "escalated": False,
        "input_tokens": 38, "output_tokens": 110, "latency_ms": 440,
        "provider_cost_usd": 0.0007,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.092, "router_overhead_wh": 0.0000010,
        "escalation_regret_wh": 0.0,
        "response": "• var: Function-scoped, hoisted with undefined initialization, allows re-declaration.\n• let: Block-scoped, temporal dead zone applies, re-assignable but cannot be re-declared in same scope.\n• const: Block-scoped, cannot be re-assigned or re-declared, requires immediate initializer.",
        "region": "IN",
    },
    {
        "id": "AF-0271", "timestamp": "2026-09-19T08:52:19Z",
        "query": "What is the boiling point of water at standard atmospheric pressure?",
        "pathway": "cache",
        "pathway_steps": ["Request","Analysis","Exact Cache Hit","Response"],
        "reason": "Exact SHA-256 cache match, sub-millisecond hash resolution",
        "complexity_score": 0.01, "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 12, "output_tokens": 8, "latency_ms": 4,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.000010, "central": 0.000020, "high": 0.000035},
        "baseline_energy_wh": 0.065, "router_overhead_wh": 0.0000005,
        "escalation_regret_wh": 0.0,
        "response": "100 °C (212 °F / 373.15 K) at 1 atmosphere of pressure.",
        "region": "IN",
    },
    {
        "id": "AF-0270", "timestamp": "2026-09-19T08:48:44Z",
        "query": "Translate \"Good morning, how may I help you with your account today?\" into Spanish.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Entity & Fluency Verification","Response"],
        "reason": "Routed to small model: p_small=0.92 ≥ floor 0.60; common bilingual phrase translation",
        "complexity_score": 0.14, "quality_floor": 0.60, "predicted_sufficiency": 0.92,
        "verification": "passed", "escalated": False,
        "input_tokens": 26, "output_tokens": 22, "latency_ms": 310,
        "provider_cost_usd": 0.0004,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.071, "router_overhead_wh": 0.0000008,
        "escalation_regret_wh": 0.0,
        "response": '"Buenos días, ¿cómo puedo ayudarle con su cuenta hoy?"',
        "region": "IN",
    },
    {
        "id": "AF-0269", "timestamp": "2026-09-19T08:44:00Z",
        "query": "What are the on-call escalation steps when database connection latency exceeds 500ms?",
        "pathway": "retrieval",
        "pathway_steps": ["Request","Analysis","Local Corpus Vector Search","Runbook Extraction","Response"],
        "reason": "Runbook query matched local engineering runbook corpus (cosine 0.92)",
        "complexity_score": 0.19, "quality_floor": 0.60, "predicted_sufficiency": 0.90,
        "verification": "passed", "escalated": False,
        "input_tokens": 62, "output_tokens": 55, "latency_ms": 95,
        "provider_cost_usd": 0.0002,
        "energy_wh": {"low": 0.00014, "central": 0.00030, "high": 0.00065},
        "baseline_energy_wh": 0.082, "router_overhead_wh": 0.0000012,
        "escalation_regret_wh": 0.0,
        "response": "Runbook Step 1: Check Read Replica connection pool saturation in Grafana.\nStep 2: If pool > 95%, initiate scale-up script.\nStep 3: If latency persists > 3 min, page the primary database engineer.",
        "region": "IN",
    },
    {
        "id": "AF-0268", "timestamp": "2026-09-19T08:39:10Z",
        "query": "Calculate (450 * 12) / (3.5 + 2.5)", "pathway": "deterministic",
        "pathway_steps": ["Request","Analysis","Deterministic Gate","Safe AST Evaluator","Response"],
        "reason": "Arithmetic expression detected", "complexity_score": 0.02,
        "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 16, "output_tokens": 4, "latency_ms": 1,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.0000005, "central": 0.000001, "high": 0.000003},
        "baseline_energy_wh": 0.066, "router_overhead_wh": 0.0000004,
        "escalation_regret_wh": 0.0, "response": "900",
        "region": "IN",
    },
    {
        "id": "AF-0267", "timestamp": "2026-09-19T08:34:25Z",
        "query": "Generate a short commit message for fixing a CSS flexbox overflow on mobile screens.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Conventional Commit Check","Response"],
        "reason": "Routed to small model: p_small=0.95 ≥ floor 0.60; conventional commit convention matcher",
        "complexity_score": 0.10, "quality_floor": 0.60, "predicted_sufficiency": 0.95,
        "verification": "passed", "escalated": False,
        "input_tokens": 32, "output_tokens": 16, "latency_ms": 320,
        "provider_cost_usd": 0.0003,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.070, "router_overhead_wh": 0.0000008,
        "escalation_regret_wh": 0.0,
        "response": "fix(ui): prevent flexbox container overflow on mobile viewport",
        "region": "IN",
    },
    {
        "id": "AF-0266", "timestamp": "2026-09-19T08:29:10Z",
        "query": "Analyze this complex distributed systems post-mortem and identify subtle race conditions in the two-phase commit coordinator failure handler.",
        "pathway": "large_model",
        "pathway_steps": ["Request","Analysis","Complexity Router","Large Model (70B+)","Response"],
        "reason": "Routed to large model: multi-step distributed causality reasoning, low small-model sufficiency (0.28)",
        "complexity_score": 0.92, "quality_floor": 0.60, "predicted_sufficiency": 0.28,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 1850, "output_tokens": 720, "latency_ms": 3650,
        "provider_cost_usd": 0.0215,
        "energy_wh": {"low": 0.310, "central": 0.580, "high": 1.100},
        "baseline_energy_wh": 0.580, "router_overhead_wh": 0.0000028,
        "escalation_regret_wh": 0.0,
        "response": "Root cause analysis reveals that when the coordinator crashed between preparing cohorts and writing the commit log to durable storage, recovery protocol erroneously assumed abort without querying epoch numbers on cohorts, creating a split-brain state.",
        "region": "IN",
    },
    {
        "id": "AF-0265", "timestamp": "2026-09-19T08:22:15Z",
        "query": "Verify whether this cryptographic signature verification code is vulnerable to timing attacks and rewrite with constant-time equality.",
        "pathway": "escalated",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Security Verifier","Escalate → Large Model (70B+)","Response"],
        "reason": "Security verifier rejected small model output: failed constant-time byte iteration check",
        "complexity_score": 0.81, "quality_floor": 0.60, "predicted_sufficiency": 0.48,
        "verification": "failed", "escalated": True,
        "input_tokens": 380, "output_tokens": 290, "latency_ms": 2890,
        "provider_cost_usd": 0.0138,
        "energy_wh": {"low": 0.310, "central": 0.580, "high": 1.100},
        "baseline_energy_wh": 0.580, "router_overhead_wh": 0.0000019,
        "escalation_regret_wh": 0.0180,
        "response": "The original comparison `a == b` early-exits on the first mismatch, leaking timing information. Here is the constant-time implementation:\n```ts\nfunction constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {\n  if (a.length !== b.length) return false;\n  let diff = 0;\n  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];\n  return diff === 0;\n}\n```",
        "region": "IN",
    },
    {
        "id": "AF-0264", "timestamp": "2026-09-19T08:16:40Z",
        "query": "Write a TypeScript interface for a user profile with id, email, role, and optional avatar URL.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","TypeScript Syntax Verification","Response"],
        "reason": "Routed to small model: p_small=0.96 ≥ floor 0.60; standard type declaration",
        "complexity_score": 0.09, "quality_floor": 0.60, "predicted_sufficiency": 0.96,
        "verification": "passed", "escalated": False,
        "input_tokens": 42, "output_tokens": 46, "latency_ms": 310,
        "provider_cost_usd": 0.0004,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.076, "router_overhead_wh": 0.0000009,
        "escalation_regret_wh": 0.0,
        "response": "```ts\nexport interface UserProfile {\n  id: string;\n  email: string;\n  role: 'admin' | 'member' | 'viewer';\n  avatarUrl?: string;\n}\n```",
        "region": "IN",
    },
    {
        "id": "AF-0263", "timestamp": "2026-09-19T08:11:02Z",
        "query": "What is 1024 * 1024?", "pathway": "deterministic",
        "pathway_steps": ["Request","Analysis","Deterministic Gate","Safe AST Evaluator","Response"],
        "reason": "Arithmetic expression detected", "complexity_score": 0.01,
        "quality_floor": 0.60, "predicted_sufficiency": 1.00,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 7, "output_tokens": 4, "latency_ms": 2,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.0000005, "central": 0.000001, "high": 0.000003},
        "baseline_energy_wh": 0.065, "router_overhead_wh": 0.0000004,
        "escalation_regret_wh": 0.0, "response": "1048576",
        "region": "IN",
    },
    {
        "id": "AF-0262", "timestamp": "2026-09-19T08:05:15Z",
        "query": "Summarize the main purpose of HTTP status code 429.",
        "pathway": "small_model",
        "pathway_steps": ["Request","Analysis","Small Model (8B)","Factual Verification","Response"],
        "reason": "Routed to small model: p_small=0.93 ≥ floor 0.60; standard RFC standard definition",
        "complexity_score": 0.11, "quality_floor": 0.60, "predicted_sufficiency": 0.93,
        "verification": "passed", "escalated": False,
        "input_tokens": 24, "output_tokens": 38, "latency_ms": 330,
        "provider_cost_usd": 0.0004,
        "energy_wh": {"low": 0.012, "central": 0.018, "high": 0.031},
        "baseline_energy_wh": 0.074, "router_overhead_wh": 0.0000008,
        "escalation_regret_wh": 0.0,
        "response": "HTTP status code 429 \"Too Many Requests\" indicates that the user has sent too many requests in a given amount of time (rate limited by the server).",
        "region": "IN",
    },
    {
        "id": "AF-0261", "timestamp": "2026-09-19T08:00:00Z",
        "query": "Explain quantum entanglement simply", "pathway": "cache",
        "pathway_steps": ["Request","Analysis","Semantic Cache Hit","Response"],
        "reason": "Semantic cache hit, cosine 0.97",
        "complexity_score": 0.35, "quality_floor": 0.60, "predicted_sufficiency": 0.88,
        "verification": "not_applicable", "escalated": False,
        "input_tokens": 14, "output_tokens": 75, "latency_ms": 12,
        "provider_cost_usd": 0.0,
        "energy_wh": {"low": 0.000015, "central": 0.000020, "high": 0.000040},
        "baseline_energy_wh": 0.095, "router_overhead_wh": 0.0000007,
        "escalation_regret_wh": 0.0,
        "response": "Quantum entanglement is a physical phenomenon where two or more particles become connected so that the physical state of one instantly dictates the state of the other, no matter how far apart they are.",
        "region": "IN",
    },
]


def _normalise(query: str) -> str:
    import re
    return re.sub(r"\s+", " ", query.strip().lower())


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def seed():
    init_db()
    db = SessionLocal()
    try:
        seeded = 0
        cache_seeded = 0
        for fix in FIXTURES:
            existing = db.query(ReceiptORM).filter(ReceiptORM.id == fix["id"]).first()
            if existing:
                logger.info("Receipt %s already exists — skipping", fix["id"])
                continue

            orm = ReceiptORM(
                id=fix["id"],
                timestamp=fix["timestamp"],
                query=fix["query"],
                pathway=fix["pathway"],
                pathway_steps=json.dumps(fix["pathway_steps"]),
                reason=fix["reason"],
                complexity_score=fix["complexity_score"],
                quality_floor=fix["quality_floor"],
                predicted_sufficiency=fix["predicted_sufficiency"],
                verification=fix["verification"],
                escalated=fix["escalated"],
                input_tokens=fix["input_tokens"],
                output_tokens=fix["output_tokens"],
                latency_ms=fix["latency_ms"],
                provider_cost_usd=fix["provider_cost_usd"],
                energy_wh=json.dumps(fix["energy_wh"]),
                baseline_energy_wh=fix["baseline_energy_wh"],
                router_overhead_wh=fix["router_overhead_wh"],
                escalation_regret_wh=fix["escalation_regret_wh"],
                response=fix["response"],
                region=fix.get("region", "IN"),
                # IMPORTANT: always mark seed fixtures as demo so they are
                # never included in audit/analytics metric calculations.
                is_demo=True,
                created_at=datetime.fromisoformat(fix["timestamp"].replace("Z", "+00:00")),
            )
            db.add(orm)
            seeded += 1

            # Seed cache for cache-pathway fixtures
            if fix["pathway"] in ("cache", "small_model", "large_model", "retrieval"):
                norm = _normalise(fix["query"])
                h = _sha256(norm)
                existing_cache = db.query(CacheEntryORM).filter(CacheEntryORM.hash == h).first()
                if not existing_cache:
                    cache_row = CacheEntryORM(
                        hash=h,
                        query=fix["query"],
                        response=fix["response"],
                        embedding=None,  # will be populated when server starts
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(cache_row)
                    cache_seeded += 1

        db.commit()
        logger.info("Seeded %d receipts and %d cache entries", seeded, cache_seeded)
        print(f"\n✓ Seeded {seeded} receipts, {cache_seeded} cache entries into aiflow.db")
        print("  Run 'uvicorn main:app --reload' to start the server.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
