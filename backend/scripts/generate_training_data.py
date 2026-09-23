"""
Generates training_prompts.json — ~360 labelled prompts across 6 categories.

Label convention:
  1 = small model sufficient
  0 = large model needed

Run once: python scripts/generate_training_data.py
"""
import json
import sys
from pathlib import Path

# Categories and representative prompts
# Source: synthetic prompts following Dolly/Alpaca-style templates.
# Note: These are synthetically authored prompts designed to cover the
# classification boundary faithfully. No real user data is included.

PROMPTS: list[dict] = []

# ── CATEGORY 1: Arithmetic / unit / date  ────────────────────────────────────
# (Negative controls — should never reach classifier; label=1 anyway)
arithmetic = [
    "What is 27 × 43?", "Calculate 1024 * 1024", "(450 * 12) / (3.5 + 2.5)",
    "What is 15% of 240?", "Compute 999 - 437", "What is 2 to the power of 10?",
    "How much is 3.14 * 2 * 5?", "Divide 144 by 12", "What is 8 factorial?",
    "Calculate the square root of 196", "What is 7 * 8 * 9?",
    "Convert 120 miles per hour to km/h", "100 degrees Fahrenheit in Celsius",
    "Convert 5 kilograms to pounds", "How many days between 2026-01-01 and 2026-09-19?",
    "How many hours is 3.5 days?", "Convert 500 grams to ounces",
    "What is 256 / 16?", "Calculate 2.718 ^ 2", "What is 0.1 + 0.2?",
]
for p in arithmetic:
    PROMPTS.append({"prompt": p, "label": 1, "category": "arithmetic"})

# ── CATEGORY 2: Stable factual (short) ───────────────────────────────────────
# Small model is sufficient: label=1
stable_factual_small = [
    "What is the capital of France?",
    "What is the boiling point of water?",
    "What is the speed of light in a vacuum?",
    "Who wrote Hamlet?",
    "What year did World War II end?",
    "What is the atomic number of carbon?",
    "What is the chemical formula for water?",
    "How many planets are in the solar system?",
    "What language is spoken in Brazil?",
    "What is the tallest mountain on Earth?",
    "What is the currency of Japan?",
    "Who painted the Mona Lisa?",
    "What is the largest ocean on Earth?",
    "What does HTTP stand for?",
    "What is the default port for HTTPS?",
    "What is the time complexity of binary search?",
    "What does CPU stand for?",
    "What is the SI unit of electric current?",
    "What is the freezing point of water in Celsius?",
    "How many bytes are in a megabyte?",
    "What is the output of print('hello world') in Python?",
    "Summarize the main purpose of HTTP status code 429 in one sentence.",
    "What does DNS stand for?",
    "What is IPv4?",
    "What is the purpose of a firewall?",
    "What is the main use of the git stash command?",
    "What does REST stand for?",
    "What is a pointer in C?",
    "What is the difference between TCP and UDP in one sentence?",
    "What is the purpose of the WHERE clause in SQL?",
    "What is a foreign key in databases?",
    "What does SOLID stand for in software design?",
    "What is the purpose of a constructor in OOP?",
    "What is idempotency in REST APIs?",
    "What is a hash table?",
    "What is the difference between == and === in JavaScript?",
    "What is the purpose of the useEffect hook in React?",
    "What does async/await do in JavaScript?",
    "What is a closure in JavaScript?",
    "What is tail recursion?",
]
for p in stable_factual_small:
    PROMPTS.append({"prompt": p, "label": 1, "category": "stable_factual"})

# ── CATEGORY 3: Short generative (rewrite / tone / summary / translate) ──────
# Small model sufficient: label=1
short_gen = [
    "Rewrite this in a professional tone: 'hey can u send me that file asap thx'",
    "Translate 'Good morning, how may I help you?' into Spanish.",
    "Generate a short commit message for fixing a CSS overflow bug.",
    "Write a one-line description for a Python function that sorts a list.",
    "Summarize this in one sentence: The quick brown fox jumps over the lazy dog.",
    "Convert this list to bullet points: apples, oranges, bananas, grapes.",
    "Write a subject line for an email about a delayed shipment.",
    "Translate 'Thank you for your patience' into French.",
    "Rewrite this error message to be more user-friendly: 'Error 500 internal server error'",
    "Draft a polite follow-up email after a job interview.",
    "Write a TypeScript interface for a user with id, email, and role fields.",
    "Generate a function name for a method that validates email addresses.",
    "Write a git tag message for version 2.1.0 release.",
    "Translate 'Please enter your password' into German.",
    "Write a one-sentence product description for a task management app.",
    "Rewrite this in active voice: 'The report was submitted by the team.'",
    "Create a short README description for a weather CLI tool.",
    "Convert this JSON to a bullet list: {name: 'Alice', age: 30, city: 'Paris'}",
    "Write a one-line docstring for a function that calculates compound interest.",
    "Generate a CSS class name for a primary call-to-action button.",
    "Write a polite decline email for a meeting request.",
    "Summarize the concept of recursion in one sentence.",
    "Write a short description for a REST API endpoint that creates users.",
    "Rewrite this variable name to be more descriptive: 'var d = new Date()'",
    "Write a brief onboarding message for a new team member.",
    "Translate 'Loading, please wait...' into Japanese.",
    "Generate a commit message for adding dark mode support.",
    "Write a one-liner description of what a load balancer does.",
    "Format this list as a Markdown table: Name, Age: Alice 30, Bob 25, Carol 35.",
    "Write a toast notification message for a successful file upload.",
]
for p in short_gen:
    PROMPTS.append({"prompt": p, "label": 1, "category": "short_generative"})

# ── CATEGORY 4: Reasoning / multi-step ───────────────────────────────────────
# Borderline: small might pass, large is safer. Mix of label=0 and label=1.
reasoning_large = [
    "Explain the CAP theorem and its implications for distributed database design.",
    "Compare and contrast dependency injection and service locator patterns.",
    "Analyze the trade-offs between microservices and monolithic architecture for a startup.",
    "Critique the philosophical viability of modal realism against ersatz modal realism.",
    "Explain why the double-slit experiment challenges classical physics intuitions.",
    "Analyze Kant's categorical imperative and its weaknesses as a moral framework.",
    "Compare merge sort and quicksort in terms of best/average/worst-case complexity.",
    "Explain the Byzantine Generals problem and how Practical BFT solves it.",
    "Analyze the trade-offs between CQRS and traditional CRUD architectures.",
    "Explain the difference between optimistic and pessimistic concurrency control.",
    "Discuss why eventual consistency is difficult to reason about in distributed systems.",
    "Analyze the trade-offs between GraphQL and REST for a mobile-first product.",
    "Explain why mutable shared state is the root of most concurrency bugs.",
    "Compare structural typing versus nominal typing in programming languages.",
    "Explain the implications of Gödel's incompleteness theorems for formal systems.",
    "Analyze the trade-offs between eager and lazy evaluation strategies.",
    "Explain why tail-call optimization matters for functional programming.",
    "Compare forward-chaining and backward-chaining in inference engines.",
    "Analyze the security implications of JWT versus opaque session tokens.",
    "Explain why lock-free data structures are hard to implement correctly.",
]
for p in reasoning_large:
    PROMPTS.append({"prompt": p, "label": 0, "category": "reasoning_complex"})

reasoning_small = [
    "Explain the difference between let, const, and var in JavaScript.",
    "What is the difference between a stack and a queue?",
    "Explain how a binary search tree works.",
    "What is the difference between shallow copy and deep copy?",
    "Explain what a race condition is in concurrent programming.",
    "What is the difference between authentication and authorization?",
    "Explain what memoization is and give a simple example.",
    "What is the difference between SQL and NoSQL databases?",
    "Explain what a webhook is and how it differs from polling.",
    "What is the difference between a process and a thread?",
    "Explain what CORS is and why browsers enforce it.",
    "What is the difference between a left join and an inner join in SQL?",
    "Explain what an API gateway does.",
    "What is the difference between synchronous and asynchronous programming?",
    "Explain what a virtual DOM is in React.",
    "What is the difference between encryption and hashing?",
    "Explain what a deadlock is and how to prevent it.",
    "What is the Observer pattern?",
    "Explain what a CDN is and why it improves performance.",
    "What is the difference between unit testing and integration testing?",
]
for p in reasoning_small:
    PROMPTS.append({"prompt": p, "label": 1, "category": "reasoning_simple"})

# ── CATEGORY 5: Long-document / deep analysis (label=0) ──────────────────────
long_doc = [
    "Analyze this technical document and summarize the trade-offs between Raft and Paxos consensus algorithms.",
    "Review this distributed systems post-mortem and identify the root cause of the split-brain failure.",
    "Analyze the following research paper abstract and critique its methodology.",
    "Review this 500-line Python module and identify potential performance bottlenecks.",
    "Analyze this architectural design document and identify single points of failure.",
    "Review this database schema with 20 tables and suggest normalization improvements.",
    "Analyze this security audit report and prioritize the findings by CVSS score.",
    "Review this API specification and identify inconsistencies in the error handling contract.",
    "Analyze this incident post-mortem and identify systemic process improvements.",
    "Review this pull request with 300 lines of changes and provide a thorough code review.",
    "Analyze this technical specification and identify gaps in the requirements.",
    "Review this machine learning training pipeline and identify data leakage risks.",
    "Analyze this microservices communication diagram and identify potential bottlenecks.",
    "Review this Terraform infrastructure code and identify security misconfigurations.",
    "Analyze this legal contract for software licensing and identify problematic clauses.",
    "Verify whether this cryptographic signature code is vulnerable to timing attacks.",
    "Analyze this complex financial model and identify the key assumptions and risks.",
    "Review this React component tree for prop drilling issues and suggest refactoring.",
    "Analyze this network trace and identify the root cause of the latency spike.",
    "Review this data pipeline and identify potential data quality issues.",
]
for p in long_doc:
    PROMPTS.append({"prompt": p, "label": 0, "category": "long_document"})

# ── CATEGORY 6: Ambiguous / conversational ────────────────────────────────────
# Mixed labels — some are simple enough for small model
ambiguous = [
    "What do you think about TypeScript?",
    "Can you help me with my code?",
    "I'm having trouble with my React app.",
    "Tell me something interesting about Python.",
    "What's the best way to learn programming?",
    "How do I get started with machine learning?",
    "What should I use for my next project?",
    "Is JavaScript a good language?",
    "How do I improve my coding skills?",
    "What's the difference between a good and bad engineer?",
]
for p in ambiguous[:5]:
    PROMPTS.append({"prompt": p, "label": 1, "category": "ambiguous"})
for p in ambiguous[5:]:
    PROMPTS.append({"prompt": p, "label": 0, "category": "ambiguous"})

# ── More complex / multi-step reasoning (label=0) ────────────────────────────
more_complex = [
    "Explain quantum entanglement with formal wave function collapse equations.",
    "Analyze the trade-offs between Lamport clocks and vector clocks for distributed tracing.",
    "Explain the formal proof of the pumping lemma for context-free languages.",
    "Analyze how consistent hashing minimises key remapping in distributed hash tables.",
    "Explain the security implications of prototype pollution in JavaScript.",
    "Compare the computational complexity of NP-complete problems and give examples.",
    "Analyze the memory layout of a C++ virtual function table (vtable).",
    "Explain why floating-point arithmetic is not associative with a concrete example.",
    "Analyze the CAP theorem proof and explain which systems sacrifice which guarantee.",
    "Explain the formal semantics of Hoare logic and its use in program verification.",
    "Analyze the space-time trade-off in the Bloom filter data structure.",
    "Explain why the halting problem is undecidable using a diagonal argument.",
    "Compare B-trees and LSM-trees for write-heavy versus read-heavy workloads.",
    "Analyze the security properties of TLS 1.3 handshake versus TLS 1.2.",
    "Explain the formal definition of a monad in category theory and Haskell.",
    "Analyze the correctness of the two-generals problem and its implications.",
    "Explain how garbage collection mark-and-sweep differs from reference counting.",
    "Analyze the Paxos made simple paper and identify the protocol's liveness conditions.",
    "Explain why epsilon-delta proofs are needed for rigorous limit definitions.",
    "Analyze the implications of the no-free-lunch theorem for machine learning.",
    "Explain what post-quantum cryptography algorithms are being standardized by NIST.",
    "Analyze the relationship between information theory entropy and compression.",
    "Explain how kernel-level scheduling differs from user-space cooperative scheduling.",
    "Analyze the correctness guarantees of snapshot isolation in databases.",
    "Explain the formal definition of linearizability in concurrent systems.",
    "Analyze the memory consistency models of x86 vs ARM architectures.",
    "Explain how Diffie-Hellman key exchange achieves forward secrecy.",
    "Analyze the trade-offs in using eventual consistency for a social media feed.",
    "Explain the computational complexity of the knapsack problem and its approximations.",
    "Analyze why the Singleton pattern is considered an anti-pattern in modern design.",
]
for p in more_complex:
    PROMPTS.append({"prompt": p, "label": 0, "category": "reasoning_complex"})

# ── More short/simple (label=1) ───────────────────────────────────────────────
more_simple = [
    "Explain what Git is in one paragraph.",
    "Write a Python function that reverses a string.",
    "What is a REST API?",
    "Explain what a variable is in programming.",
    "Write a hello world program in Python.",
    "What is a for loop?",
    "Explain what an if statement does.",
    "Write a CSS rule to make text red.",
    "What is npm?",
    "Explain what a package manager does.",
    "Write a SQL query to select all rows from a users table.",
    "What is the purpose of the HTML head element?",
    "Explain what a boolean is.",
    "Write a function that checks if a number is even.",
    "What is an array in programming?",
    "Explain what JSON stands for.",
    "Write a regex to match an email address.",
    "What is the purpose of the return statement?",
    "Explain what a null value represents.",
    "Write a function to calculate factorial recursively.",
    "What is version control?",
    "Explain what a merge conflict is.",
    "Write a function that finds the maximum value in a list.",
    "What is the purpose of the .gitignore file?",
    "Explain what a pull request is.",
    "Write a bash command to list all files in a directory.",
    "What is Docker?",
    "Explain what a container is.",
    "Write a function that counts words in a string.",
    "What is the difference between a library and a framework?",
]
for p in more_simple:
    PROMPTS.append({"prompt": p, "label": 1, "category": "short_generative"})

print(f"Total prompts generated: {len(PROMPTS)}")

# Count by label
n_small = sum(1 for p in PROMPTS if p["label"] == 1)
n_large = sum(1 for p in PROMPTS if p["label"] == 0)
print(f"  Label=1 (small sufficient): {n_small}")
print(f"  Label=0 (large needed):     {n_large}")

out_path = Path(__file__).parent.parent / "data" / "training_prompts.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    json.dump(PROMPTS, f, indent=2, ensure_ascii=False)

print(f"Written to {out_path}")
