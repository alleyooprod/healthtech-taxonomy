# Feature Roadmap — Research Taxonomy Library

Updated 2026-02-19. Based on deep research of 35+ SaaS tools across 9 categories.

---

## Current Feature Inventory (70+ features)

| Area | Count | Key Features |
|------|-------|-------------|
| Companies | 14 | List, detail, edit, star, relationship tracking, re-research, notes, events, versions, trash, duplicates, comparison, bulk select + bulk actions, quick-add API |
| Taxonomy | 7 | Tree view, graph view (Cytoscape), AI review, apply changes, quality dashboard, change history, category color coding |
| Market Map | 5 | Drag-drop kanban, geographic map (Leaflet), company comparison, auto-layout (Cytoscape compound nodes), PNG export |
| Research | 5 | AI market reports, deep dive (scoped LLM research), templates, saved results, markdown/PDF export |
| Canvas | 4 | Cytoscape workspace, drag-drop companies, note nodes, edge drawing, auto-save |
| Processing | 5 | AI discovery, URL triage, batch pipeline, recent batches, retry |
| Navigation | 3 | Linked record navigation, breadcrumbs, category detail view |
| Filtering | 2 | Active filter chips, saved views |
| Tags | 2 | Tag manager (rename/merge/delete), tag filtering |
| Analytics | 2 | Dashboard charts (ECharts/Chart.js), project statistics |
| Export/Import | 6 | JSON, Markdown, CSV, Excel, PDF, CSV import |
| Sharing | 2 | Share links, read-only shared view |
| Notifications | 3 | In-app SSE panel, Slack integration, activity log |
| AI Chat | 2 | Data Q&A widget, find similar companies |
| UX | 3 | Keyboard shortcuts, shortcuts overlay, product tour |
| Theme | 1 | Dark/light toggle with Material Symbols icons |
| Desktop | 4 | Native window, macOS menu, notifications, git sync |

---

## Competitive Landscape Summary

| Tool | Taxonomy | Discovery | AI Research | Map Viz | Enrichment | Canvas |
|------|----------|-----------|-------------|---------|------------|--------|
| CB Insights | Partial | Yes | No | **Best** | Partial | No |
| Crunchbase | No | **Best** | No | No | Partial | No |
| Tracxn | **Best** | Yes | No | Partial | Manual | No |
| PoolParty | **Best** | No | No | Partial | No | No |
| Notion | Partial | No | Yes | No | No | No |
| Airtable | Partial | No | No | No | No | No |
| Perplexity | No | No | **Best** | No | No | No |
| Clay | No | No | No | No | **Best** | No |
| **This App** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

**Key insight**: No single tool combines all six columns. This app occupies a unique position in the market.

---

## Recently Built (Feb 2026)

These features were just implemented:

| Feature | Status | Description |
|---------|--------|-------------|
| Category Color Coding | Built | Color pickers in taxonomy, color dots in table/map/taxonomy tree |
| Bulk Select + Bulk Actions | Built | Checkbox column, floating action bar, assign/tag/relationship/delete |
| Linked Record Navigation | Built | Breadcrumbs, category detail view, clickable entity links |
| Deep Dive Research | Built | Scoped LLM research with web search, templates, saved library |
| Research Canvas | Built | Cytoscape.js workspace with drag-drop, notes, edges, auto-save |
| Auto-Build Market Map | Built | Cytoscape compound node layout, category-grouped, PNG export |
| E2E Test Suite | Built | 125 Playwright tests across 22 spec files |

---

## Existing Roadmap — Not Yet Built

### Tier 1: High Impact

#### 1. Cross-Project Portfolio Dashboard
**Inspired by**: Asana Portfolios, Monday.com dashboards, Airtable Interface Designer
**What**: Overview across all taxonomy projects — completion metrics, coverage gaps, recent activity, cross-project company overlap detection.
**Complexity**: Medium

#### 2. AI Research Plan Display + Streaming
**Inspired by**: Perplexity Deep Research, ChatGPT streaming
**What**: Show research plan before execution, stream results as they arrive, allow cancellation mid-research. Progressive rendering for all AI operations.
**Complexity**: High

#### 3. Waterfall Company Enrichment
**Inspired by**: Clay (100+ providers), Apollo (waterfall), Clearbit (auto-refresh)
**What**: Systematically fill company data gaps by trying multiple sources in sequence. Bulk enrichment for companies below completeness threshold.
**Complexity**: Medium

#### 4. Auto-Generated Comparison Tables
**Inspired by**: Elicit (paper comparison), G2 (product comparison), CB Insights
**What**: AI generates structured comparison tables for all companies in a category, with custom dimensions. Export as standalone report.
**Complexity**: Medium

### Tier 2: Clear Value

#### 5. Multiple Taxonomy Views (Gallery/Timeline/Matrix)
**Inspired by**: Airtable, Notion database views
**What**: Gallery cards with logos, timeline by founding year/funding, 2D matrix with categories vs. geography/stage.
**Complexity**: Medium

#### 6. Smart Alerts & Change Detection
**Inspired by**: Browse AI, Apollo (job change alerts), ZoomInfo
**What**: Periodic web check for tracked companies, detect funding/pivots/shutdowns, alert via notification + Slack.
**Complexity**: High

#### 7. Report Templates & Brand Kit
**Inspired by**: Beautiful.ai, Gamma, Canva brand kit
**What**: Upload logo, set brand colors, create reusable report templates. PDF export uses brand kit automatically.
**Complexity**: Medium

#### 8. Company Scoring / Signal System
**Inspired by**: CB Insights Mosaic Score, ZoomInfo intent signals
**What**: Composite score per company based on completeness, relevance, funding momentum, category fit. Visual indicators + sorting.
**Complexity**: Low

### Tier 3: Future Differentiation

#### 9. Automation Recipes
**Inspired by**: Monday.com, Airtable automations, Zapier
**What**: Trigger-action automations (e.g., auto-enrich on add, suggest subcategories when category exceeds 15 companies).
**Complexity**: High

#### 10. Multi-User Collaboration
**Inspired by**: Notion multiplayer, Miro real-time
**What**: Auth system, WebSocket presence, comments, assignment. Major architectural change.
**Complexity**: Very High

#### 11. API & Integrations Hub
**Inspired by**: Airtable API, Miro app marketplace
**What**: REST API for external integrations + connectors (Slack, Notion, Google Sheets, Airtable).
**Complexity**: Medium

#### 12. AI-Powered Taxonomy Suggestions
**Inspired by**: Semaphore, Tana supertags, PoolParty concept extraction
**What**: AI monitors incoming companies and suggests new categories/subcategories when it detects clusters.
**Complexity**: Medium

#### 13. Knowledge Graph Visualization
**Inspired by**: Obsidian graph view, PoolParty, Neo4j
**What**: Interactive graph of all relationships: companies, categories, tags, funding, geography — all as connected nodes.
**Complexity**: High

#### 14. Presentation Mode
**Inspired by**: Miro frame presentations, CB Insights, Gamma
**What**: Turn market map or report into a walkable presentation. Full-screen, category-as-slide navigation.
**Complexity**: Medium

#### 15. Customer Journey Mapping
**Inspired by**: UXPressia, Smaply, Miro journey templates
**What**: Template-based journey canvas for deep dives. AI-generated from website/product analysis.
**Complexity**: Medium

#### 16. Competitive Intelligence Feed
**Inspired by**: Crayon, Klue, Contify
**What**: Aggregated news/signal feed for tracked companies. Filterable by company, category, signal type. AI "morning brief" generation.
**Complexity**: High

---

## New Feature Ideas (Feb 2026 Research)

### High Impact, Lower Effort

#### N1. Taxonomy Concept Definitions & Scope Notes
**Inspired by**: SKOS standard (TopBraid, Semaphore), PoolParty concept scheme editor
**What**: Add structured metadata to each category: formal definition, inclusion/exclusion criteria, related concept links. Feed scope notes into classifier LLM prompt to improve classification accuracy by 15-25%.
**Why it matters**: Currently the classifier only gets category names. Precise scope notes dramatically improve `confidence_score`.
**Complexity**: Low

#### N2. Data Freshness Dashboard
**Inspired by**: Crayon data staleness alerts, Apollo accuracy scoring, Clay last-enriched tracking
**What**: Project-level dashboard showing data freshness per company and category. Staleness indicators based on `last_verified_at` age. Prioritized re-research queue with one-click batch re-research for stale records.
**Why it matters**: Already store `last_verified_at` but don't expose it as a decision tool. Makes the difference between a live intelligence system and a static database.
**Complexity**: Low

#### N3. Inline LLM Field Suggestions
**Inspired by**: Notion AI inline, GitHub Copilot, Clay's AI field filling
**What**: "AI suggest" button next to each company field in edit mode. Uses other known fields as context to generate a suggestion for empty fields. Accept, edit, or dismiss inline without a full research workflow.
**Why it matters**: Full research pipeline is heavy. For quick data entry after CSV import or manual add, inline suggestions provide just-in-time enrichment.
**Complexity**: Low

#### N4. Research Question Library (Reusable Prompts)
**Inspired by**: Elicit's structured workflows, Clay's AI agent templates
**What**: Library of parameterized research question templates with variables (e.g., "Compare pricing models of companies in {category_name}"). One-click apply to any scope. Includes suggested models and output formats.
**Why it matters**: 80% of research questions fall into patterns. Templates speed up research and ensure consistency.
**Complexity**: Low

#### N5. Source-Specific Importers (Crunchbase/PitchBook/Dealroom)
**Inspired by**: Clay's 75+ integrations, Apollo's list import
**What**: Import company lists from Crunchbase, PitchBook, Dealroom, CB Insights CSV exports with pre-built column mappings. Preview with field mapping before committing.
**Why it matters**: Current CSV import is generic. Source-specific importers reduce import friction from 15 minutes to one click.
**Complexity**: Low

#### N6. Taxonomy SKOS/JSON-LD Export
**Inspired by**: PoolParty SKOS export, TopBraid interchange, Semaphore
**What**: Export/import taxonomy in standard SKOS RDF/XML or JSON-LD format for interoperability with enterprise taxonomy tools and knowledge graphs.
**Why it matters**: Standard interchange format enables taxonomy reuse beyond this tool.
**Complexity**: Low

### High Impact, Medium Effort

#### N7. Category Playbook Pages (Battlecards)
**Inspired by**: Klue's battlecards, Crayon's competitive battlecard builder, Notion-style wiki
**What**: Each category gets a rich wiki-style page: definition, auto-generated report, curated bullet points (trends, risks, opportunities), quick stats header, pinned companies, embedded research results. Becomes THE reference document for a market segment.
**Why it matters**: Battlecard/playbook pages are the #1 feature request in competitive intelligence platforms. Transforms category detail from a company list into a stakeholder deliverable.
**Complexity**: Medium

#### N8. Funding Round Timeline (Cross-Company)
**Inspired by**: Harmonic.ai funding signals, Dealroom funding timeline, Crunchbase visualization
**What**: Aggregate all funding events across companies into a single interactive swimlane timeline. Filter by category, stage, amount, date range. Spot patterns like "Series B clustering in Q3 2025 in RPM."
**Why it matters**: Funding patterns are the strongest signals of market momentum. Leverages existing `company_events` table.
**Complexity**: Medium

#### N9. Source Provenance Chain
**Inspired by**: Elicit's claim provenance, AlphaSense's document annotation
**What**: For each company field, store and display provenance: which URL, which LLM, when, what prompt. Click any value to see "Extracted from [URL] on [date] by [model]." Stale facts flagged by age.
**Why it matters**: "Where did this number come from?" is the #1 stakeholder question. Makes every claim auditable.
**Complexity**: Medium

#### N10. Company Lifecycle State Machine
**Inspired by**: Dealroom status tracking, PitchBook deal flow
**What**: Configurable state machine per project (Active -> Acquired -> Integrated, Active -> Pivoted -> Renamed). Each transition logged with date, notes, optional triggers. Visual timeline of transitions per company.
**Why it matters**: In insurance/healthtech, companies get acquired constantly. A proper state machine captures these transitions as first-class data.
**Complexity**: Medium

#### N11. Market Sizing Calculator
**Inspired by**: Dealroom market sizing, PitchBook TAM/SAM/SOM, Gartner methodology
**What**: Per category, aggregate funding, employee counts, stated TAMs into bottom-up market size estimate. Allow top-down inputs from analyst reports. AI cross-references with web-searched market data. Export as market sizing slide.
**Why it matters**: Every market research project needs "how big is this market." Structured calculator rolls up across categories — the core deliverable for investment/strategy research.
**Complexity**: Medium

#### N12. AI Taxonomy Gap Finder
**Inspired by**: Contify signal analysis, Semantic Scholar gap detection, PoolParty consistency checker
**What**: AI analyzes taxonomy vs. company data to find: (a) missing categories based on keyword clusters, (b) companies straddling two categories that indicate needed splits, (c) categories with too-heterogeneous members. Presents actionable suggestions.
**Why it matters**: Goes beyond existing taxonomy review (structure critique) by using actual company data as evidence. Data-driven taxonomy maintenance.
**Complexity**: Medium

#### N13. Evidence Notebook (Structured Annotations)
**Inspired by**: Sentieo's document annotation, Roam Research bidirectional linking
**What**: Per-project notebook of structured "evidence cards": a claim, source (linked to company/research), confidence level, tags. Cards link bidirectionally to companies and categories. Reports pull relevant evidence cards as citations.
**Why it matters**: Current notes are per-company. Market findings often span companies ("3 companies pivoted to B2B2C in 2025"). Evidence notebook captures cross-cutting insights.
**Complexity**: Medium

#### N14. Cohort Analysis View
**Inspired by**: Harmonic.ai cohorts, PitchBook peer benchmarking, Observable notebooks
**What**: Select companies by category/tag/stage/geography and see aggregate stats: founding year distribution, funding breakdown, geographic heat map, common tags. Save cohorts for comparison.
**Why it matters**: The power of a taxonomy tool is in aggregate views. "What does the average Series B telehealth company look like?" can't be answered without this.
**Complexity**: Medium

#### N15. Research Session Branching (Follow-Up Chains)
**Inspired by**: Perplexity follow-up threads, ChatGPT branching, Elicit iterative refinement
**What**: After a deep dive, system suggests 3-5 follow-up questions. Users click to start linked follow-up sessions. Sessions form a navigable tree capturing the research trail.
**Why it matters**: Research is iterative — one finding raises new questions. Branching preserves the chain of reasoning.
**Complexity**: Medium

#### N16. Snapshot & Diff (Point-in-Time Comparison)
**Inspired by**: Wayback Machine concept, Klue change tracking, git diff for data
**What**: Take named snapshots of project state. Diff two snapshots: companies added/removed, category changes, funding stage changes. Structured changelog with visual indicators.
**Why it matters**: Market landscapes change quarterly. "What changed since last time?" is unanswerable without point-in-time comparison.
**Complexity**: Medium

#### N17. Relationship Web Visualization
**Inspired by**: Crunchbase acquisition graph, Dealroom investor-company network, Neo4j
**What**: Network graph showing inter-company relationships: partnerships, acquisitions, shared investors, shared customers. Users add relationships manually or AI extracts from research. Click edges for details.
**Why it matters**: In insurance/healthtech, the partnership/acquisition graph IS the market structure. Reveals dynamics that a flat list never will.
**Complexity**: Medium

#### N18. Thesis Builder (Investment Memo Generator)
**Inspired by**: PitchBook investment thesis templates, Harmonic.ai deal memo assistant
**What**: Select a category + companies and generate a structured investment thesis: market overview, competitive dynamics, white space analysis, key risks, potential winners, summary thesis statement. Specialized LLM prompt for investment memo format.
**Why it matters**: The end product of much market research is an investment thesis or partnership recommendation. Different from general market reports.
**Complexity**: Medium

#### N19. Multi-Axis Scatter Plot Builder
**Inspired by**: Dealroom dynamic scatter plots, Flourish chart builder, Observable Plot
**What**: Pick X-axis, Y-axis, bubble size, and color from numeric/categorical company fields. Interactive scatter/bubble plot with hover detail and click-to-open. Save chart configurations.
**Why it matters**: Quantitative analysis requires scatter plots. Plotting any two dimensions against each other is core to investment research and pattern recognition.
**Complexity**: Medium

#### N20. Sankey Diagram Builder
**Inspired by**: Flourish Sankey templates, Observable flow diagrams, Datawrapper
**What**: Generate interactive Sankey diagrams showing flows between any two dimensions: Funding Stage -> Category, Geography -> Category, Business Model -> Stage. Users pick source and target from dropdowns.
**Why it matters**: Understanding distribution across multiple dimensions simultaneously is impossible from a flat table. Sankey reveals allocation patterns instantly.
**Complexity**: Medium

#### N21. Taxonomy Diff & Merge Across Projects
**Inspired by**: PoolParty taxonomy alignment, git merge concepts applied to ontologies
**What**: Side-by-side diff of two project taxonomies, highlighting overlapping categories. Selectively merge or align categories across projects with drag-and-drop reconciliation.
**Why it matters**: Parallel projects evolve independently — without cross-project reconciliation, knowledge silos form.
**Complexity**: Medium

#### N22. AI Field Extraction from URLs (One-Click Enrich)
**Inspired by**: Clay's Claygent, Diffbot auto-extraction, Firecrawl
**What**: Click "Enrich from Website" to extract specific missing fields (employee range, pricing model, product names) without full re-research. Field-targeted extraction is 10x faster and cheaper.
**Why it matters**: Current pipeline is all-or-nothing. Often you just need 2-3 missing fields on an already-categorized company.
**Complexity**: Medium

### Ambitious / High Effort

#### N23. Semantic Search (Embedding-Based)
**Inspired by**: AlphaSense semantic search, Perplexity natural language, Consensus claim-level search
**What**: Generate text embeddings for company descriptions, store in SQLite virtual table (sqlite-vss). Enable natural language queries like "companies using AI to reduce claims processing time" with cosine similarity ranking.
**Why it matters**: Current search is SQL LIKE-based. Semantic search catches companies described differently but doing the same thing. Single biggest leap in research UX.
**Complexity**: High

#### N24. Watchlist with Web Monitoring Triggers
**Inspired by**: Contify company monitoring, Crayon competitive monitoring, Feedly AI
**What**: Mark companies/categories as "watched." Configure triggers for news about acquisitions/funding/launches. Periodic LLM web searches surface new findings with one-click "Add to events."
**Why it matters**: Turns the tool from a point-in-time snapshot into a living intelligence system.
**Complexity**: High

#### N25. Company Similarity Heatmap
**Inspired by**: Sentieo peer comparison matrix, AlphaSense similarity scoring
**What**: NxN heatmap showing similarity scores between all companies (based on tags, descriptions, category, funding, geography). Reveals clusters and outliers. Sortable and filterable.
**Why it matters**: Comparison panel shows up to 4 companies. Understanding full competitive landscape structure requires seeing all pairwise relationships.
**Complexity**: Medium

---

## Quick Wins (< 1 day each)

| # | Feature | Status |
|---|---------|--------|
| 1 | Bulk select + bulk actions | **Built** |
| 2 | Column visibility toggle | Not started |
| 3 | Keyboard shortcut for star (s on highlighted row) | Not started |
| 4 | Category color coding | **Built** |
| 5 | Export filtered results only | Not started |
| 6 | Inline editing (double-click table cell) | Not started |
| 7 | Company count badges on tab labels | Not started |
| 8 | Last-viewed breadcrumb | **Built** (linked navigation) |
| 9 | Drag-to-reorder categories in taxonomy tree | Not started |
| 10 | Confidence threshold slider filter | Not started |
| 11 | URL deduplication on paste | Not started |
| 12 | Batch progress notifications (non-desktop) | Not started |
| 13 | Search within detail panel | Not started |
| 14 | Export market map as SVG | Not started |
| 15 | Copy company data as JSON/Markdown | Not started |

---

## Prioritization Framework

| Factor | Weight | Description |
|--------|--------|-------------|
| User Impact | 40% | How much does this improve the daily research workflow? |
| Differentiation | 25% | Does this set the tool apart from competitors? |
| Implementation Effort | 20% | How long to build? Prefer quick wins. |
| Extensibility | 15% | Does this create a foundation for future features? |

### Suggested Implementation Order

**Phase 1 — Next Sprint**
- N1. Taxonomy Scope Notes (low effort, improves classification)
- N2. Data Freshness Dashboard (low effort, leverages existing data)
- N3. Inline LLM Field Suggestions (low effort, big UX win)
- N4. Research Question Library (low effort, speeds up research)
- 8. Company Scoring / Signal System (low effort, adds prioritization)
- Quick wins: #2 Column toggle, #5 Export filtered, #6 Inline editing

**Phase 2 — Near-Term**
- N7. Category Playbook Pages (stakeholder deliverable)
- N8. Funding Round Timeline (leverages existing data)
- 4. Auto-Generated Comparison Tables
- 2. AI Research Plan Display + Streaming
- N18. Thesis Builder (investment memo generator)
- Quick wins: #9, #10, #11, #14

**Phase 3 — Medium-Term**
- 1. Cross-Project Portfolio Dashboard
- 3. Waterfall Company Enrichment
- N12. AI Taxonomy Gap Finder
- N14. Cohort Analysis View
- N16. Snapshot & Diff
- N19. Multi-Axis Scatter Plot Builder

**Phase 4 — Longer-Term**
- N23. Semantic Search
- N17. Relationship Web Visualization
- N24. Watchlist with Monitoring
- 14. Presentation Mode
- 15. Customer Journey Mapping
- 13. Knowledge Graph Visualization

---

## Sources

- CB Insights Market Map Maker — auto-build, bin-packing, hover previews, Mosaic Score
- Crunchbase — faceted search, company profiles, saved searches
- Tracxn — analyst-curated taxonomy (2,900+ feeds), sector reports
- PoolParty — SKOS taxonomy, color-coded relationships, graph views
- Notion — linked databases, multiple views, AI agents, frontier model selection
- Obsidian — bidirectional linking, graph view, Dataview plugin
- Heptabase — infinite canvas, card-to-edit transitions, zoom levels
- Miro — auto-layout, frame presentations, 130+ integrations
- Lucidchart — data-linked shapes, live data refresh
- Clay — waterfall enrichment, spreadsheet-as-workflow, Claygent AI
- Perplexity — Deep Research, research plan display, streaming citations
- Elicit — comparison tables, evidence extraction, systematic reviews
- Beautiful.ai — auto-layout constraints, brand consistency
- Gamma — card-based presentations, AI content restructuring
- Airtable — Interface Designer, linked records, multiple views, automations
- Monday.com — 200+ automation recipes, color-coded statuses, dashboards
- Apollo — waterfall enrichment, job change alerts, bi-directional CRM sync
- ZoomInfo — Mosaic-like scoring, intent signals, 260M+ profiles
- AlphaSense — semantic search, document annotation, peer comparison
- Sentieo — notebook system, structured annotations, similarity heatmaps
- Dealroom — market sizing, dynamic scatter plots, funding timelines
- PitchBook — investment thesis templates, deal flow tracking, cohort analysis
- Harmonic.ai — funding signals, cohort analysis, deal memos
- Contify — company monitoring, configurable alerts, signal analysis
- Crayon — competitive monitoring, data staleness tracking, battlecards
- Klue — battlecard builder, competitive intelligence, change tracking
- Flourish — Sankey diagrams, interactive charts, data storytelling
- Semaphore — auto-classification, SKOS, taxonomy consistency
- TopBraid — taxonomy interchange, concept definitions, SKOS export
