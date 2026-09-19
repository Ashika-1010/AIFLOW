# AIFlow — The Minimum-Compute Layer for AI Applications

> **Global Innovation Hackathon 2026** · *“Innovate Without Borders”*  
> Tagline: *Use the smallest amount of compute that still answers the question — and prove it.*

AIFlow is a developer-facing middleware layer that sits between client applications and AI model providers. For each incoming query, AIFlow determines the minimum viable computational pathway (Tier 0 Deterministic AST/regex tools → Tier 0.5 Exact/Semantic Cache → Tier 1 Local Vector Retrieval → Tier 2 8B-class Small Model → Tier 3 70B+ Frontier Model), verifies responses against a strict quality gate, and emits an auditable **Energy Receipt**.

Its distinguishing principle is **honest self-accounting**: it charges itself for its own router overhead and bills itself for wasted energy when a cheap attempt fails and escalates (*escalation regret*).

---

## 🚀 Key Features

1. **Tier-0 Deterministic Tools**: Evaluates pure arithmetic, unit conversions, and date calculations without triggering LLM inference (~0.000 Wh).
2. **Verify-and-Escalate Cascade**: Runs small models first, checks confidence and structural gates, and escalates to large models only on failure while accounting for wasted energy.
3. **Uncertainty-Banded Energy Receipts**: Reports every energy claim as a range (Low / Central / High) backed by peer-reviewed published benchmark coefficients (`ML.ENERGY Benchmark v3.0`, Google Gemini inference methodology).
4. **Live Regional Grid Carbon Intensity**: Calculates grams of CO₂ equivalent live using real regional grid emissions factors (e.g., India: 713 gCO₂e/kWh, France: 56 gCO₂e/kWh).
5. **Pessimistic-Assumptions Sensitivity Toggle**: Interactive switch on `/audit` that recomputes all savings with worst-case PUE and high-bound coefficients (42% → 31%), demonstrating that efficiency claims survive rigorous adversarial cross-examination.

---

## 🛠️ Tech Stack & Constraints

- **Architecture**: 100% Frontend-only (No backend, no server, no external API keys, zero SDK leaks).
- **Core**: React 18 + Vite + TypeScript (Strict Mode).
- **Styling**: Tailwind CSS v3 with dark technical instrumentation tokens.
- **Typography**: Google Fonts `Sora` (headings/UI) & `JetBrains Mono` (labels, IDs, numbers, telemetry).
- **Visualizations**: Recharts.
- **Icons**: Lucide React.
- **State Management**: React Context (`AppContext`).

---

## 🎨 Design System Tokens (`tailwind.config.js`)

| Token | Hex / Value | Usage |
|---|---|---|
| `bg` | `#08080A` | App background |
| `surface` | `#0D0D10` | Primary cards and panels |
| `surface2` | `#111116` | Nested elements, table stripes |
| `border` | `#1E1E24` | 1px structural borders |
| `border2` | `#2A2A32` | Hover & focus borders |
| `text` | `#F4F4F5` | Primary text |
| `muted` | `#8A8A94` | Secondary labels, descriptions |
| `dim` | `#5A5A64` | Tertiary footnotes, grid axes |
| `accent` | `#FF2D78` | AIFlow signature pink (primary actions, active nav) |
| `accentDim` | `#B01F55` | Accent shades |
| `accentBg` | `rgba(255,45,120,0.08)` | Active navigation & banner tints |
| `deterministic` | `#22C55E` | Tier 0 green |
| `cache` | `#A855F7` | Tier 0.5 purple |
| `retrieval` | `#6366F1` | Tier 1 indigo |
| `smallModel` | `#FF2D78` | Tier 2 pink |
| `largeModel` | `#F59E0B` | Tier 3 amber |
| `escalated` | `#EF4444` | Escalation penalty red |

---

## 🔌 How to Swap the Mock Layer for a Real REST API

All data reads and simulations are isolated in [`src/mock/`](./src/mock/):

```
src/mock/
├── types.ts         # TypeScript interfaces (Receipt, EnergyBand, AuditSummary, Region)
├── regions.ts       # Electricity Maps grid intensity values
├── methodology.ts   # Disclosed formulas and coefficient bounds
├── data.ts          # 24 hand-authored fixture receipts & assumptions table
└── api.ts           # Async REST API functions (runRequest, listReceipts, getReceipt, getAuditSummary, getAnalytics)
```

To connect a production FastAPI / Node backend:
1. Replace `src/mock/api.ts` with real `fetch()` calls targeting your backend API endpoints:
   ```ts
   export async function runRequest(query: string, qualityFloor: number): Promise<Receipt> {
     const res = await fetch('/v1/complete', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ prompt: query, quality_floor: qualityFloor })
     });
     return res.json();
   }
   ```
2. No components or pages will require modification because all interfaces strictly adhere to the `Receipt` contract.

---

## 💻 Running the Application

### 1. Install Dependencies
```bash
npm install
```

### 2. Run Local Development Server
```bash
npm run dev
```

### 3. Production Build & Type Check
```bash
npm run build
```
*(Builds with zero TypeScript errors and zero warnings)*
