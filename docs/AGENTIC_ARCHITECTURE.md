# Agentic Architecture — Vision & Design Decisions

> **Created:** 2026-02-21 (Session 30)
> **Purpose:** Captures the "why" behind every major agentic design decision, including directions explored, rejected, and the evolution of thinking through conversation and red-team challenge.
> **Referenced by:** `IMPLEMENTATION_PLAN_V2.md`
> **Related:** `docs/RED_TEAM_FINDINGS.md` (red-team analysis that shaped final decisions)

---

## What "Agentic" Means for This App

**Not:** A chatbot. Not an AI assistant you talk to. Not an autonomous system that runs unsupervised.

**Is:** An orchestration layer that executes multi-step research workflows autonomously, with the human defining the mission at the start and reviewing output at the end. The agent handles the mechanical middle — discovery, capture, extraction, analysis — that currently requires hours of manual initiation.

### The Operating Model Shift

```
CURRENT (human-orchestrated):
  You → discover entities → You → capture pages → You → extract data →
  You → review ALL results → You → navigate to analysis → You → generate report

AGENTIC (agent-orchestrated):
  You → define mission + confirm entities
    Agent → capture → extract → analyse → draft report
  You → review flagged items (~15%) + approve report
```

**Active time for 50-entity project:**
- Current: ~14-24 hours (user initiates every step)
- Agentic: ~2-3 hours (define mission, review flagged items, approve output)

The time savings come from eliminating orchestration overhead, not from removing quality checks.

---

## Architecture Options Evaluated

### Option A: ReAct (Reasoning + Acting)

**Pattern:** Single LLM loop — reason about what to do next, act, observe result, repeat.

```
while not done:
    thought = llm("Given context, what should I do next?")
    action = execute(thought)
    observation = observe(action)
    context += observation
```

**Pros:** Simple, flexible, handles unexpected situations gracefully.
**Cons:** Token cost explodes (full context passed every iteration), no parallelism (one action at a time), LLM makes every decision (expensive).

**Verdict:** Rejected. Too expensive and too slow for 50-entity research with 250+ page captures.

### Option B: Supervisor-Worker

**Pattern:** A supervisor dispatches work to specialised workers that run in parallel. Workers are existing Python functions, not LLM agents.

```
supervisor → [capture_worker_1, capture_worker_2, ..., capture_worker_N]
          → wait for all
          → [extract_worker_1, extract_worker_2, ..., extract_worker_N]
```

**Pros:** Parallelism, workers are cheap (no LLM per worker), scales to many entities.
**Cons:** No high-level planning — supervisor needs to know the workflow structure upfront.

### Option C: Plan-and-Execute

**Pattern:** LLM creates a plan (sequence of stages), then a simple executor runs each stage.

```
plan = llm("Given research brief, create a multi-stage plan")
for stage in plan:
    execute_stage(stage)
    if checkpoint: await_approval()
    replan_if_needed()
```

**Pros:** LLM called once for planning (cheap), deterministic execution, supports checkpoints.
**Cons:** No parallelism within stages.

### Decision: Hybrid B+C

**Chosen architecture:** Plan-and-Execute for macro-level sequential stages, Supervisor-Worker for micro-level parallel execution within each stage.

**Why the user challenged the original C-only recommendation:** "Why can't we combine Option B + C?" — valid challenge. The stages ARE sequential (must discover before capturing), but WITHIN each stage, work is embarrassingly parallel (capture 50 entities simultaneously).

```
PLANNER (LLM, called once)
  → Stage 1: Discover entities
      SUPERVISOR → [search_worker_1, search_worker_2, ...]
  → Stage 2: Capture evidence
      SUPERVISOR → [capture_worker_1, capture_worker_2, ...] (max 3 concurrent)
  → Stage 3: Extract structured data
      SUPERVISOR → [extract_worker_1, extract_worker_2, ...]
  → Stage 4: Analyse + Report
      SUPERVISOR → [lens_compute, report_draft, quality_check]
  → NOTIFY: "Research ready for review"
```

**Key insight:** Workers are NOT LLM-powered agents. They're existing Python functions (`capture_website()`, `extract_from_evidence()`, `enrich_entity()`). Only the planner needs LLM. This keeps costs predictable.

**Quantified benefit:** Sequential processing of 50 entities × 5 pages = 250 serial captures at ~3s each = 750s (12.5 min). With 3 parallel workers = ~250s (4 min). LLM cost stays the same (one planning call).

---

## The Automation Model

### Human at the Edges, Agent in the Middle

The user challenged the original conservative model ("why can't Discovery, Extraction, Analysis, Monitoring, and Reporting be fully automated?"). After discussion, the agreed model is:

**Human input point 1 — Define the mission:**
- Research question, schema (or template), initial entity list confirmation
- ~5 minutes, once per project

**Human input point 2 — Review the output:**
- Flagged extraction items (low confidence, contradictions) — ~15% of total
- Report approval before sharing
- ~1-2 hours per full scan

**Everything between is automated.** The agent:
1. Discovers entities from registries and web search
2. Captures key pages per entity (standard paths + sitemap + link analysis)
3. Downloads whitepapers and reports from entity sites and market searches
4. Extracts structured data against project schema
5. Computes analysis lenses
6. Drafts standardised reports
7. Notifies the user: "Ready for review"

### Why Full Automation Works Here

The user's key insight: **"Extraction from websites is largely copy-paste of existing structured data."** When a pricing page says "£29/month," the AI isn't hallucinating — it's reading what's written. High-confidence extractions don't need human confirmation.

This is true for:
- Explicit pricing (numbers on page)
- Feature lists (bullet points on product pages)
- Company identity (name, URL, description from About page)
- App store metadata (ratings, version, screenshots — structured API data)
- Regulatory data (FCA register, Companies House — authoritative sources)

It's less true for:
- Marketing copy interpretation (is "AI-powered wellness" a feature or a tagline?)
- Cross-company terminology mapping (is "24/7 GP access" the same as "Virtual doctor consultations"?)
- Complex pricing (age-banded, excess-dependent, postcode-varying)

The review queue handles the latter category. Smart-sort puts ambiguous items first. The user reviews the hard 15%, trusts the easy 85%.

---

## Research Brief as Living Document

### The Problem It Solves

Research evolves. You start with "UK EAP market" and discover adjacent entities (Thanksben in employee benefits) that reshape your understanding. The system must accommodate mid-project scope evolution without restarting.

### How It Works

The Research Brief is a structured, versioned, mutable document stored per project:

```json
{
  "version": "1.2",
  "question": "UK EAP market landscape and best-in-class analysis",
  "scope_rules": [
    {"type": "core", "criteria": "UK-registered EAP providers", "source": "FCA + web search"},
    {"type": "adjacent", "criteria": "Employee benefits platforms with EAP overlap",
     "added": "2026-02-22", "trigger": "User observation during research"}
  ],
  "benchmark_entities": ["Spectrum.life"],
  "schema_version": "1.1",
  "entity_budget": 40,
  "amendments": [
    {"date": "2026-02-22", "type": "scope_expansion",
     "description": "Added adjacent employee benefits platforms",
     "rationale": "Thanksben encountered during research, relevant UX and feature overlap"}
  ]
}
```

### Three Ways Scope Evolves

1. **User tells the agent:** "Add Thanksben as adjacent — employee benefits but relevant for comparison." Agent creates entity, queues capture, updates brief. ~10 seconds of user time.

2. **Agent proposes expansion:** During capture, the agent reads pages that reference companies outside current scope. It proposes: "Found 3 employee benefits platforms mentioned alongside your EAP providers. Add as adjacent?" User confirms or ignores.

3. **Schema adapts:** If new entities have attributes that don't fit the current schema, the agent proposes additions. Uses existing `POST /api/entity-types/sync`. Additive only — never removes attributes. Existing entities unaffected.

### Scope Creep Mitigation (from Red-Team)

- **Entity budget per project.** Hard cap (configurable). Agent shows: "At 38/40 entity budget. Adding 4 would exceed — which existing entities should be deprioritised?"
- **Scope expansion requires explicit amendment.** Not one-click confirm — the user writes a brief reason. This forces conscious decision-making.
- **Cumulative cost shown:** "Adding these 4 entities: ~20 captures, ~40 extractions, estimated £3 LLM cost, ~15 new review items."

---

## Entity Tagging System

Rather than rigid schema types for scope management, entities carry research-context tags:

| Tag | Meaning | Analysis treatment |
|-----|---------|-------------------|
| `core` | Primary research scope | Included in all lenses and reports by default |
| `adjacent` | Related but outside strict scope | Included in comparison views, excluded from core metrics by default |
| `benchmark` | Best-in-class reference point | Highlighted in analysis, used as comparison baseline |
| `peripheral` | Tangentially related, noted for completeness | Excluded from analysis by default, available on toggle |
| `archived` | Was relevant, no longer in scope | Hidden, data preserved |

Tags are filterable everywhere — lenses, reports, matrices, exports. No schema changes required.

---

## Whitepaper & Report Discovery

### Three Discovery Channels

**Channel A — Entity Website Crawl:** Extend page discovery to check `/resources`, `/reports`, `/research`, `/whitepapers`, `/insights`, `/case-studies`. Download PDFs. Extract key findings, data points, methodology.

**Channel B — Market-Wide Search:** Search MCP sources (DuckDuckGo, Brave) for published research about the market: `"employee assistance programme" report 2025`, `"EAP market" whitepaper UK`. Prioritise government publications, consultancies, industry bodies. Link market-level evidence to project, not individual entities.

**Channel C — Citation Presentation (not auto-following):** When a whitepaper cites other reports, extract the citation list and present it to the user: "This report references 18 sources. 4 are publicly accessible and relevant to your research. Capture them?" User cherry-picks. No automatic citation chain traversal (red-team finding: cost and noise far outweigh value).

### Whitepaper Extractor

New extractor following existing pattern (`ipid.py`, `press_release.py`):
- Classification: PDF format, methodology/summary sections, data tables, citations
- Extraction: title, authors, publication date, executive summary, key findings (with page references), data points (metric + value + population), methodology description, entities mentioned
- Source tier: industry body → Tier 1-2, consultancy → Tier 2, entity's own report → Tier 2-3

---

## Project Duplication (Not Forking)

### The Use Case

Start from "UK EAP Market" (25 entities, 200 evidence items, 800 attributes) and diverge:
- Copy A: "EAP → Employee Wellbeing Convergence" (expand scope)
- Copy B: "EAP for Tech Companies" (narrow scope)

### Decision: Simple Duplication First

The red-team found that git-style forking (lineage tracking, selective sync, divergence detection) is over-engineered for a solo analyst. Build "Duplicate Project" first:

- Copy all data to a new, independent project
- Evidence records reference same physical files (no disk duplication)
- Reference counting on files (only delete from disk when zero records point to it)
- No lineage tracking, no sync, no merge
- User can delete entities from the copy to narrow scope
- If fork-with-lineage proves necessary later, add it as an enhancement

---

## Cost Model

### Estimated Costs Per Market Scan (50 entities)

| Operation | Calls | Model | Cost/call | Total |
|-----------|-------|-------|-----------|-------|
| Planning/reasoning | ~10 | Sonnet | $0.05 | $0.50 |
| Page classification | ~250 | Haiku | $0.01 | $2.50 |
| HTML extraction | ~250 | Sonnet | $0.08 | $20.00 |
| Screenshot extraction | ~200 | Sonnet (vision) | $0.15 | $30.00 |
| Whitepaper extraction | ~30 | Sonnet | $0.20 | $6.00 |
| Report drafting | ~3 | Sonnet | $0.50 | $1.50 |
| **Total** | | | | **~$60** |

### Cost Controls

- **Pre-run estimate:** "This scan will make ~740 LLM calls. Estimated cost: $55-70. Proceed?"
- **Budget cap per project:** Agent pauses when budget reached
- **Model tiering:** Haiku for classification/triage (cheap), Sonnet for extraction/analysis (capable)
- **Cache-first:** If page content hash hasn't changed since last capture, skip re-extraction entirely
- **Incremental re-scans:** Only re-process entities where monitoring detected changes (~$5-15 per refresh vs $60 full scan)

---

## Directions NOT Taken

### Rejected: ReAct Single-Agent Loop
Too expensive (full context every iteration), too slow (no parallelism). See Option A above.

### Rejected: LangChain / CrewAI / External Agent Frameworks
Adds heavy dependencies, opinionated patterns that fight the existing Flask architecture, and versioning headaches. The hybrid B+C is implementable with plain Python + threading + one LLM planning call.

### Rejected: Computer Use (Anthropic's Computer Use API)
Massive overhead for UI navigation when structured data extraction achieves the same result. Computer Use is for when there's no API or no structured HTML — not the common case for marketing/product pages.

### Rejected: Always-On Background Agent
An agent that runs continuously, monitoring and capturing without prompts. Too expensive, too noisy, too likely to accumulate irrelevant data. Agent runs are user-initiated (or scheduled at explicit intervals), never perpetual.

### Rejected: Auto-Accept High-Confidence Extractions (at launch)
Red-team finding: LLM confidence scores are poorly calibrated. Auto-accepting based on self-reported confidence creates invisible errors. Build smart-sort review queue first, calibrate with empirical data, then enable auto-accept with proven thresholds.

### Rejected: Automatic Citation Chain Following
Red-team finding: exponential document growth, 60-70% of citations are paywalled/inaccessible, high LLM cost for low yield. Present citation list to user instead, let them cherry-pick.

### Rejected: Git-Style Project Forking
Red-team finding: selective sync between forks is merge-conflict territory, evidence file sharing creates hidden coupling, over-engineered for solo analyst. Build simple project duplication first.

### Rejected: Single Composite Quality Score
Red-team finding: false precision. A "72/100" obscures whether the problem is accuracy, relevance, or freshness. Show three separate dimension bars instead.

---

## How This Maps to Existing Infrastructure

The agentic layer is **additive**, not disruptive. Almost everything it needs already exists:

| Agent capability | Existing infrastructure | What's new |
|---|---|---|
| Entity discovery | AI Discovery + MCP enrichment (11 adapters) | Agent orchestration + auto-queueing |
| Page capture | `core/capture.py` + Playwright | Sitemap parsing + page discovery logic |
| Document capture | `capture_document()` | Whitepaper extractor + market-wide search |
| Data extraction | `core/extraction.py` + 7 extractors | Smart-sort review queue + batch triggering |
| Feature mapping | `canonical_features` + resolve/merge | Auto-mapping with confidence threshold |
| Analysis | 6 lenses + framework | Auto-computation on data change |
| Reporting | 5 templates + AI generation | Auto-draft when quality gates pass |
| Monitoring | 8 check types + change feed | Scheduled re-capture from freshness triggers |
| Cost tracking | `llm_calls` table + budget system | Per-agent-run cost aggregation |
| Background jobs | `web/async_jobs.py` | Enhanced with supervisor/worker dispatch |

The agent is a thin orchestration layer on top of a mature execution layer.
