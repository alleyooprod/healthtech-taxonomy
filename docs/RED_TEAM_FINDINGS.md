# Red-Team Analysis — Agentic Workbench Approach

> **Created:** 2026-02-21 (Session 30)
> **Purpose:** Critical analysis of the proposed agentic architecture, quality scoring, and feature roadmap. Every finding includes severity, description, failure mode, and recommended mitigation. These findings directly shaped the final `IMPLEMENTATION_PLAN_V2.md`.
> **Referenced by:** `IMPLEMENTATION_PLAN_V2.md`, `docs/AGENTIC_ARCHITECTURE.md`

---

## Summary

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | LLM confidence scores unreliable — auto-accept dangerous | CRITICAL | Mitigated: smart-sort review, not auto-accept |
| 2 | Quality score creates false precision | HIGH | Mitigated: three separate bars, not composite |
| 3 | Agent-proposed scope expansion is runaway train | HIGH | Mitigated: entity budgets, explicit amendments |
| 4 | Cost is unaddressed elephant | CRITICAL | Mitigated: pre-run estimates, budget caps, model tiering |
| 5 | Playwright at scale is fragile | HIGH | Mitigated: concurrency limits, per-domain rate limiting |
| 6 | Solo analyst paradox — configuration overhead | MEDIUM-HIGH | Mitigated: defaults for everything, progressive disclosure |
| 7 | Project forking is over-engineered | MEDIUM | Mitigated: simple duplication first |
| 8 | Citation following is a money pit | MEDIUM | Mitigated: present list, user cherry-picks |
| 9 | SQLite concurrent write pressure | MEDIUM | Mitigated: batch writes per worker |
| 10 | 18 months of work designed | HIGH (strategic) | Mitigated: ship Phase 8+9 first, learn, iterate |

---

## Finding 1: LLM Confidence Scores Are Unreliable — Auto-Accept Is Dangerous

**Severity:** CRITICAL

**Description:** The original proposal auto-accepted 60-70% of extractions at 0.9+ confidence. LLM self-reported confidence and actual accuracy are weakly correlated. LLMs are overconfident — they report high confidence even on wrong answers.

**Failure mode:** Agent extracts "£29/month" from a pricing page at 0.93 confidence. Auto-accepted. But the page actually said "from £29/month" for a specific age band — full price is £47/month. Wrong value flows into competitive matrix, pricing landscape, and board report. Nobody catches it because it was auto-accepted. Once in the system, it's "verified" data — green indicators, included in reports.

**Recommendation:** Don't auto-accept at launch. Instead:
- **Smart-sort the review queue** — high confidence at top for quick 2-second confirmation, low confidence at bottom with highlighted ambiguity
- **Build empirical calibration** — track sample-audited values per confidence band; after 500+ extractions with measured accuracy, THEN consider auto-accept with proven thresholds
- **Never auto-accept pricing, features, or regulatory data** — only truly mechanical fields (company name, URL, app store rating)

**Status:** Incorporated into implementation plan. Smart-sort review is the default. Auto-accept is a future enhancement gated on calibration data.

---

## Finding 2: Quality Score Creates False Precision

**Severity:** HIGH

**Description:** A "72/100" project quality score is a single number that obscures more than it reveals. The 0.4/0.3/0.3 weighting (accuracy/relevance/freshness) is arbitrary with no empirical basis. The composite changes significantly with different weights.

**Additional problems:**
- **Relevance is circular** — "attributes that feed active lenses = high relevance," but which lenses activate depends on what data exists
- **Freshness half-lives are guesses** — UK insurance pricing changes annually, but a 90-day half-life marks year-old (but current) data as stale
- **The number invites gaming** — optimising for score rather than research quality

**Recommendation:** Show three separate dimension bars (accuracy, relevance, freshness) per entity. Let the human synthesise. Use quality gates (pass/fail) for report generation, not a continuous composite score.

**Status:** Incorporated. Three separate bars in dashboard. No composite score. Quality gates use per-dimension thresholds.

---

## Finding 3: Agent-Proposed Scope Expansion Is a Runaway Train

**Severity:** HIGH

**Description:** Agent finds Thanksben referenced alongside EAP providers. Proposes adding. Thanksben's pages mention Yulife. Yulife mentions Ben. Each "yes" adds 5 pages to capture, 10+ extractions to review. User clicks "yes" five times → scope creeps from 25 to 48 entities without a conscious decision.

**Failure mode:** Each expansion is individually reasonable but cumulatively overwhelming. Agent spends LLM budget on entities the user barely cares about. Competitive matrix is cluttered. Research question drifts.

**Recommendation:**
- **Entity budget per project** — hard cap, agent shows impact of adding: "At 38/40. Adding 4 would exceed — which should be deprioritised?"
- **Scope expansion requires explicit brief amendment** — not one-click confirm. 30 seconds of deliberate action.
- **Show cumulative cost** — "Adding these 4: ~20 captures, ~40 extractions, est. £3 LLM cost, ~15 new review items"

**Status:** Incorporated. Entity budgets, explicit amendments, cumulative cost display.

---

## Finding 4: Cost Is the Unaddressed Elephant

**Severity:** CRITICAL

**Description:** A 50-entity market scan involves ~740 LLM calls. Estimated cost: $55-75 per full scan. Monthly re-scans at 30% = ~$20/month/project. With 3-4 active projects: $80/month in LLM costs. The current manual workflow costs $0 (CLI subscription).

**Recommendation:**
- **Pre-run cost estimate** before every agent run: "Estimated cost: £55-75. Proceed?"
- **Budget caps per project** — agent pauses when reached
- **Model tiering** — Haiku for classification/triage ($0.01/call), Sonnet for extraction/analysis ($0.08/call)
- **Cache aggressively** — if page content hash unchanged, skip re-extraction entirely
- **Incremental re-scans** — only re-process entities where monitoring detected changes (~$5-15 vs $60)

**Status:** Incorporated. Cost estimation, budget caps, model tiering, and cache-first re-processing all in plan.

---

## Finding 5: Playwright at Scale Is Fragile

**Severity:** HIGH

**Description:** The capture engine works for manual one-at-a-time captures. An agent running 250 captures autonomously hits: cookie consent banners (~60% of EU/UK sites), JavaScript SPAs needing hydration time, rate limiting / bot detection from same-domain rapid access, high RAM consumption (~100-200MB per instance).

**Failure rate projection:** ~15% of automated captures will fail (cookie banner, bot block, timeout, SPA not loaded) = 37 failures out of 250.

**Recommendation:**
- **Concurrency limit: 3 parallel Playwright instances** (not the optimistic 5-10)
- **Per-domain rate limiting** — minimum 3s between requests to same domain
- **Cookie consent auto-dismissal** — stealth plugin or common button pattern detection
- **Adaptive wait** — DOM stability check rather than fixed timeout
- **Capture quality check** — after capture, verify page isn't empty/challenge page; retry with different strategy
- **Realistic throughput** — 50 entities × 5 pages at 3 concurrent with 3s delays = ~4-5 minutes, not 21 seconds

**Status:** Incorporated. 3 concurrent workers, per-domain rate limiting, capture quality validation.

---

## Finding 6: Solo Analyst Paradox — Configuration Overhead

**Severity:** MEDIUM-HIGH

**Description:** The system requires understanding and configuring: source quality tiers, freshness half-lives, quality score weights, auto-accept thresholds, entity tags, research brief amendments, agent budget caps, capture concurrency, whitepaper discovery depth, playbook quality thresholds. That's 15+ configuration dimensions before the agent runs.

**The irony:** Building a tool for one person with the configuration surface area of an enterprise platform. The vision doc says "simple over clever."

**Recommendation:**
- **Sensible defaults for EVERYTHING** — user starts a project, adds entities, agent runs with zero configuration
- **Progressive disclosure** — show quality score; user clicks in IF they want to tune
- **Domain playbook packs do the configuration** — pick "UK Insurance" and all half-lives, tier rules, thresholds are pre-set
- **Configuration exists for power users** — the default path is: pick template → add entities → agent runs → review output

**Status:** Incorporated. All configuration has defaults. Playbook packs pre-configure domains. Progressive disclosure throughout.

---

## Finding 7: Project Forking Is Over-Engineered

**Severity:** MEDIUM

**Description:** Git-style forking with lineage tracking, selective sync, divergence detection, and cross-fork comparison was proposed. Problems: evidence file sharing creates hidden coupling, selective sync is merge-conflict territory, schema divergence breaks cross-fork comparison.

**Recommendation:** Build "Duplicate Project" first — copy all data to independent project, evidence records reference same physical files (reference counting for cleanup), no lineage tracking, no sync. Covers 90% of use cases. Add lineage later if proven necessary.

**Status:** Incorporated as "Project Duplication" not "Project Forking."

---

## Finding 8: Whitepaper Citation Following Is a Money Pit

**Severity:** MEDIUM

**Description:** Auto-following citations 2 levels deep: Level 0 = 1 whitepaper, Level 1 = 20 sources, Level 2 = 300 sources. Even filtered, 50-100 documents to capture. 60-70% of citations are paywalled/inaccessible. Agent spends time and LLM budget classifying documents it can't access.

**Recommendation:** Don't auto-follow citations. Extract citation list from captured whitepapers, present to user: "This report references 18 sources. 4 are publicly accessible and relevant. Capture them?" User cherry-picks the 3-5 valuable ones.

**Status:** Incorporated. Citation list extraction + user selection, not auto-following.

---

## Finding 9: SQLite Concurrent Write Pressure

**Severity:** MEDIUM

**Description:** Agent runs parallel workers, each writing evidence records, extraction results, attribute updates, change feed entries. With 3 parallel workers: potentially 60+ writes in rapid succession. SQLite WAL mode handles concurrent reads but serialises writes.

**Assessment:** Won't break anything — SQLite queues writes gracefully. But adds latency, reducing the parallelism speed benefit. Acceptable at <200 entities per project. Would need attention at 500+.

**Recommendation:** Batch writes within each worker — collect results, write in one transaction at end of each entity processing. Existing `_get_conn()` pattern supports this.

**Status:** Incorporated as implementation detail in worker design.

---

## Finding 10: We've Designed 18 Months of Work

**Severity:** HIGH (strategic)

**Description:** Phases 8-14 contain ~30 distinct features, each requiring design, implementation, testing, and integration. At ~1 feature per session, that's 30+ sessions (60-90 hours). Risk: build Phase 8 and 9, then realise Phase 11 needs to change based on learnings. Classic waterfall risk disguised as a phased plan.

**Recommendation:**
- **Cut ruthlessly** — minimum set for agentic value: Phase 8 (quality foundation) + Phase 9 (agent core)
- **Build the agent loop first**, then add quality scoring around it based on real failure data
- **Ship and learn** — run the agent on one real project. See what actually breaks. THEN build mitigation for things that actually broke, not theorised failures
- **Mark a clear "ship and learn" checkpoint** after core phases

**Status:** Incorporated. Plan front-loads Phase 8 + 9 with a "Ship & Learn" checkpoint. Phases 10-14 are planned but explicitly contingent on learnings from real usage.

---

## Meta-Observation

The biggest risk across all findings is **designing a system that's more fun to plan than to build.** The strongest version of this tool ships Phase 8 + 9 in ~9 sessions, runs against a real research project (UK EAP market), and lets real usage drive everything else. Theory is useful; empirical data from real use is better.
