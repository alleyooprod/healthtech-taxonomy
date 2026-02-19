# Feature Roadmap — Research Taxonomy Library

Generated 2026-02-18 based on deep research of 35+ SaaS tools across 9 categories.

---

## Current Feature Inventory (58+ features)

| Area | Count | Key Features |
|------|-------|-------------|
| Companies | 12 | List, detail, edit, star, relationship tracking, re-research, notes, events, versions, trash, duplicates, comparison |
| Taxonomy | 6 | Tree view, graph view (Cytoscape), AI review, apply changes, quality dashboard, change history |
| Market Map | 3 | Drag-drop kanban map, geographic map (Leaflet), company comparison |
| Reports | 3 | AI market report generation, saved reports, markdown export |
| Processing | 5 | AI discovery, URL triage, batch pipeline, recent batches, retry |
| Filtering | 2 | Active filter chips, saved views |
| Tags | 2 | Tag manager (rename/merge/delete), tag filtering |
| Analytics | 2 | Dashboard charts (ECharts/Chart.js), project statistics |
| Export/Import | 6 | JSON, Markdown, CSV, Excel, PDF, CSV import |
| Sharing | 2 | Share links, read-only shared view |
| Notifications | 3 | In-app SSE panel, Slack integration, activity log |
| AI Chat | 2 | Data Q&A widget, find similar companies |
| UX | 3 | Keyboard shortcuts, shortcuts overlay, product tour |
| Theme | 1 | Dark/light toggle |
| Desktop | 4 | Native window, macOS menu, notifications, git sync |

---

## Competitive Landscape Summary

| Tool | Taxonomy | Discovery | AI Research | Map Viz | Enrichment |
|------|----------|-----------|-------------|---------|------------|
| CB Insights | Partial | Yes | No | **Best** | Partial |
| Crunchbase | No | **Best** | No | No | Partial |
| Tracxn | **Best** | Yes | No | Partial | Manual |
| PoolParty | **Best** | No | No | Partial | No |
| Notion | Partial | No | Yes | No | No |
| Airtable | Partial | No | No | No | No |
| Perplexity | No | No | **Best** | No | No |
| Clay | No | No | No | No | **Best** |
| **This App** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

**Key insight**: No single tool combines all five columns. This app already occupies a unique position.

---

## Feature Ideas — Organized by Impact

### Tier 1: High Impact, High Differentiation

#### 1. Company Deep Dive Mode
**Inspired by**: CB Insights company profiles, Perplexity Deep Research, Crunchbase
**What**: Dedicated deep-research view for a single company — AI generates a comprehensive profile including product analysis, customer journeys, UX/aesthetic review, competitive positioning, tech stack, leadership team, and recent news.
**Why**: You mentioned wanting to "do a deep-dive into their product, the customer journeys, experience, aesthetics." This is the natural extension of re-research.
**Implementation**:
- New "Deep Dive" button on company detail panel
- Multi-step AI research: product pages, reviews (G2/Capterra), Glassdoor, LinkedIn, press
- Structured output: product teardown, customer journey map (Mermaid), UX screenshots analysis
- Saved as a company-level report (alongside market reports)

#### 2. Auto-Build Market Map Visualization
**Inspired by**: CB Insights Market Map Maker (bin-packing algorithm), Beautiful.ai (auto-layout)
**What**: One-click generates a polished, exportable market landscape image from your taxonomy data. Company logos auto-positioned within category sections. Hover shows key metrics.
**Why**: Current market map is functional (drag-drop kanban) but not presentation-ready. CB Insights charges thousands for this.
**Implementation**:
- Canvas/SVG renderer using existing taxonomy + company data
- Layout algorithm: grid within sections, sized by company count
- Company logos as tiles (already have Clearbit logos)
- Export as high-res PNG/SVG for presentations
- Optional: include funding/confidence as visual indicators (size, color)

#### 3. Cross-Project Portfolio Dashboard
**Inspired by**: Asana Portfolios, Monday.com dashboards, Airtable Interface Designer
**What**: Overview across all taxonomy projects — completion metrics, coverage gaps, recent activity, cross-project company overlap detection.
**Why**: With multiple projects, you need a bird's-eye view. Which projects need attention? Where are there overlapping companies?
**Implementation**:
- New "Portfolio" view on project selection screen
- Cards per project: company count, category count, last activity, completion %
- Cross-project duplicate detection
- Aggregated activity timeline
- Charts: companies per project, total research coverage

#### 4. AI Research Plan Display + Streaming
**Inspired by**: Perplexity Deep Research (shows plan before executing), ChatGPT streaming
**What**: Before AI starts researching, show the plan ("I will search for X, analyze Y, compare Z"). Stream results as they arrive rather than waiting for completion.
**Why**: Current AI operations are black-box with just a progress bar. Users want transparency.
**Implementation**:
- SSE streaming for all AI operations (discovery, re-research, reports, reviews)
- Show research plan as expandable section before execution
- Progressive rendering: show partial results as they arrive
- Allow cancellation mid-research

#### 5. Waterfall Company Enrichment
**Inspired by**: Clay (100+ enrichment providers), Apollo (waterfall), Clearbit (auto-refresh)
**What**: Systematically fill company data gaps by trying multiple sources in sequence: AI extraction from URL, then Crunchbase search, then LinkedIn, then web search.
**Why**: Current enrichment relies on a single AI pass. Many fields stay empty.
**Implementation**:
- Data completeness score per company (already exists as `completeness`)
- "Enrich" button that runs multi-source waterfall
- Configurable source priority: AI > web search > LinkedIn scrape > manual
- Scheduled auto-enrichment for stale data (>30 days old)
- Bulk enrichment for all companies below completeness threshold

#### 6. Comparison Tables (Auto-Generated)
**Inspired by**: Elicit (paper comparison tables), G2 (product comparison), CB Insights
**What**: Auto-generate structured comparison tables for companies in a category. AI fills in standardized comparison dimensions.
**Why**: Current comparison panel is manual and limited to 4 companies. Analysts need quick category-level comparisons.
**Implementation**:
- "Compare All in Category" button on taxonomy view
- AI generates comparison dimensions based on category context
- Table view with companies as columns, dimensions as rows
- Export as standalone report or embed in market report
- Interactive: sort by any dimension, highlight best-in-class

---

### Tier 2: Medium Impact, Clear Value

#### 7. Multiple Taxonomy Views (Board/Gallery/Timeline)
**Inspired by**: Airtable (Grid/Kanban/Gallery/Calendar), Notion (database views)
**What**: Same company data viewable in multiple ways beyond table + kanban + geo.
**Options**:
- **Gallery view**: Company cards with logo, description, key metrics (like Crunchbase search results)
- **Timeline view**: Companies on a timeline by founding year or last funding
- **Matrix view**: 2D grid with categories on one axis, another dimension (geography, stage) on the other

#### 8. Linked Record Navigation
**Inspired by**: Airtable (linked records), Notion (relational databases), Obsidian (backlinks)
**What**: Click-through navigation: Project > Category > Subcategory > Company > Research Notes. Every entity links bidirectionally.
**Why**: Currently you jump between tabs. Linked navigation creates a more fluid research experience.
**Implementation**:
- Breadcrumb navigation at top of detail panels
- Category cards link to filtered company list
- Company detail shows related companies in same category
- Backlinks: "Also appears in" for cross-referenced entities

#### 9. Smart Alerts & Change Detection
**Inspired by**: Browse AI (monitoring), Apollo (job change alerts), ZoomInfo (intent signals)
**What**: Monitor company websites for changes. Alert when a company raises funding, pivots, launches new products, or goes down.
**Why**: Market research goes stale. Automated monitoring keeps it current.
**Implementation**:
- Periodic web check for tracked companies (configurable: daily/weekly/monthly)
- Detect: site down, major content changes, new funding announcements
- Alert via in-app notification + optional Slack
- Dashboard showing recently changed companies

#### 10. Report Templates & Brand Kit
**Inspired by**: Beautiful.ai (brand consistency), Gamma (card-based), Canva (brand kit)
**What**: Customizable report templates with your logo, colors, and standard sections. Consistent professional output every time.
**Implementation**:
- Upload logo and set brand colors in project settings
- Report template builder: choose sections, ordering, formatting
- PDF export uses brand kit automatically
- Reusable templates across projects

#### 11. Research Workspace / Canvas
**Inspired by**: Heptabase (infinite canvas), Miro (whiteboard), FigJam
**What**: Freeform canvas where you drag company cards, category nodes, and research notes. Draw connections, annotate clusters, zoom for context.
**Why**: Sometimes you need spatial thinking to see market structure.
**Implementation**:
- Infinite canvas (could use Excalidraw or custom Canvas API)
- Drag entities from sidebar onto canvas
- Connection lines between entities
- Freehand annotation, text blocks, grouping
- Save/load canvas state per project

#### 12. Company Scoring / Signal System
**Inspired by**: CB Insights Mosaic Score, ZoomInfo intent signals, Monday.com battery indicators
**What**: Computed composite score per company based on: data completeness, market relevance, funding momentum, category fit confidence.
**Why**: Helps prioritize which companies to research deeper.
**Implementation**:
- Scoring algorithm combining existing fields
- Visual indicators: colored badge, progress ring, or battery icon
- Sortable/filterable by score
- Score breakdown tooltip

---

### Tier 3: Nice-to-Have, Future Differentiation

#### 13. Automation Recipes
**Inspired by**: Monday.com (200+ automation recipes), Airtable (automations), Zapier
**What**: Trigger-action automations for repetitive workflows.
**Examples**:
- "When a new company is added, auto-enrich from URL"
- "When a category has 15+ companies, suggest subcategories"
- "When research completes, generate a summary report"
- "When company data is >30 days old, schedule re-enrichment"

#### 14. Multi-User Collaboration
**Inspired by**: Notion (multiplayer), Miro (real-time), Google Docs
**What**: Multiple users can research simultaneously with presence indicators, comments, and assignment.
**Implementation**: Would require auth system, WebSocket for real-time, and conflict resolution. Major architectural change.

#### 15. API & Integrations Hub
**Inspired by**: Airtable API, Miro app marketplace, Clay integrations
**What**: REST API for external integrations + pre-built connectors (Slack, Notion, Google Sheets, Airtable).
**Why**: Let the taxonomy data flow into other tools.

#### 16. AI-Powered Taxonomy Suggestions
**Inspired by**: Semaphore (auto-classification), Tana (supertags), PoolParty (concept extraction)
**What**: AI monitors incoming companies and suggests new categories or subcategories when it detects clusters that don't fit existing taxonomy.
**Why**: Taxonomy should evolve as market understanding deepens.

#### 17. Knowledge Graph Visualization
**Inspired by**: Obsidian graph view, PoolParty concept neighborhoods, Neo4j
**What**: Interactive graph showing all relationships: companies, categories, tags, funding rounds, geography clusters, research notes — all as connected nodes.
**Why**: Reveals hidden patterns and connections in the research.

#### 18. Presentation Mode
**Inspired by**: Miro (frame-based presentations), CB Insights (presentation mode), Gamma
**What**: Turn your market map or report into a walkable presentation. Click through categories and companies in a storytelling flow.
**Implementation**:
- "Present" button on market map or report
- Full-screen mode with navigation controls
- Each category/section as a "slide"
- Presenter notes optional

#### 19. Customer Journey Mapping
**Inspired by**: UXPressia, Smaply, Miro journey templates
**What**: For deep-dive mode — map out a company's customer journey from discovery to activation to retention.
**Implementation**:
- Template-based journey canvas
- Stages: Awareness, Consideration, Purchase, Onboarding, Engagement, Advocacy
- Touchpoints, pain points, opportunities per stage
- AI-generated from website/product analysis

#### 20. Competitive Intelligence Feed
**Inspired by**: Crayon, Klue, Contify
**What**: Aggregated news/signal feed for tracked companies. Shows recent funding, leadership changes, product launches, press mentions.
**Implementation**:
- Web scraping + news API aggregation
- Filterable by company, category, signal type
- "Morning brief" summary generation via AI

---

## Quick Wins (< 1 day each)

These are small improvements that would make an immediate difference:

1. **Bulk select + bulk actions** on company table (delete, tag, re-categorize, star multiple)
2. **Column visibility toggle** — let users choose which table columns to show/hide
3. **Keyboard shortcut for star** — press `s` on highlighted row
4. **Category color coding** — assign colors to categories, show in table and map
5. **Export filtered results** — export only the current filtered view, not everything
6. **Inline editing** — double-click a table cell to edit without opening modal
7. **Company count badges** on tab labels (e.g., "Companies (47)")
8. **Last-viewed breadcrumb** — "Back to [last company]" after navigating away
9. **Drag-to-reorder categories** in taxonomy tree
10. **Confidence threshold filter** — slider to filter by minimum confidence score
11. **URL deduplication on paste** — warn/skip if URL already exists in project
12. **Batch progress notifications** — desktop notification when batch completes (non-desktop mode)
13. **Search within detail panel** — Cmd+F scoped to the detail content
14. **Export market map as SVG** — in addition to PNG, for scalable graphics
15. **Copy company data as JSON/Markdown** — quick copy for sharing

---

## Prioritization Framework

| Factor | Weight | Description |
|--------|--------|-------------|
| User Impact | 40% | How much does this improve the daily research workflow? |
| Differentiation | 25% | Does this set the tool apart from competitors? |
| Implementation Effort | 20% | How long to build? Prefer quick wins. |
| Extensibility | 15% | Does this create a foundation for future features? |

### Suggested Implementation Order

**Phase 1 — Immediate (this week)**
- Company Deep Dive Mode (#1)
- Bulk select + bulk actions (QW #1)
- Category color coding (QW #4)
- Column visibility toggle (QW #2)

**Phase 2 — Near-term (next 2 weeks)**
- Auto-Build Market Map (#2)
- AI Research Plan Display + Streaming (#4)
- Comparison Tables (#6)
- Quick wins #5, #7, #9, #11

**Phase 3 — Medium-term (next month)**
- Cross-Project Portfolio Dashboard (#3)
- Waterfall Enrichment (#5)
- Multiple Taxonomy Views (#7)
- Smart Alerts (#9)

**Phase 4 — Longer-term**
- Research Workspace Canvas (#11)
- Presentation Mode (#18)
- Customer Journey Mapping (#19)
- Knowledge Graph (#17)

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
