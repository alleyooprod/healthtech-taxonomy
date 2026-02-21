# Competitive Landscape Research — February 2026

> **Researched:** 2026-02-21 (Session 30)
> **Purpose:** Deep web research into tools comparable to the Research Workbench, covering competitors, pricing, founding dates, and best-in-class across the space and adjacent spaces.
> **Referenced by:** `FEATURE_ROADMAP.md`, `IMPLEMENTATION_PLAN_V2.md`

---

## Key Finding

**Nothing exists that does exactly what this app does.** It sits at a unique intersection of:
- Flexible entity schema (like Airtable) +
- Evidence capture and archival (like Crayon) +
- AI extraction with human review (like AlphaSense) +
- Analysis lenses (like Klue) +
- Local-first desktop app (like nobody)

The competitive landscape is fragmented across 7 categories, each covering part of the problem.

---

## Category 1: Enterprise Competitive Intelligence Platforms

These are the closest competitors in spirit — they monitor competitors, gather intelligence, and generate analysis. But they're enterprise SaaS priced for teams of 10+.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Crayon** | 2014 | $20-40K/yr | Automated monitoring, battlecards, 100+ data sources, AI Compete Agent | Enterprise-only, no flexible schema, no evidence archival, no solo-analyst mode |
| **Klue** | 2015 | $15-40K/yr | Sales enablement, win/loss analysis, Compete Agent AI, CRM integration | Sales-focused (not research), no entity hierarchy, no evidence capture |
| **AlphaSense** | 2011 | $10-100K+/yr | Semantic search across 10,000+ sources, Smart Summaries, financial focus | Financial/IR focus, not product research, no entity schema, read-only |
| **Contify** | 2012 | Custom pricing | 1M+ curated sources, AI-powered tagging, market intelligence feeds | Monitoring-focused, no analysis lenses, no evidence capture |
| **Valona Intelligence** (fka M-Brain) | 2000 | Custom pricing | Global CI, multi-language, analyst services | Legacy platform, consulting-heavy, not self-service |
| **Kompyte** (Semrush) | 2014 | Part of Semrush ($100-500/mo) | Acquired by Semrush, competitor tracking, SEO overlap | SEO-centric, limited analysis, no custom schema |

**Best in class:** AlphaSense (for depth of sources and semantic search), Crayon (for automated monitoring).

**What they all lack:** Flexible per-project entity schemas, evidence-grounded provenance, local-first operation, solo-analyst pricing.

---

## Category 2: AI-Native Competitor Analysis (New Wave)

Founded 2022-2025, using LLMs as core engine. Cheaper, faster, less depth.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Competely** | 2023 | $9-99/mo | AI competitor analysis, 100+ data points per competitor, fast | Shallow (marketing page only), no evidence storage, no temporal tracking |
| **RivalSense** | 2024 | Custom (founder-focused) | 80+ sources, automated monitoring, founder/startup focus | Early stage, limited analysis, no schema flexibility |
| **Unkover** | 2023 | Free-$49/mo | Real-time ad + positioning tracking | Ad-focused, not product research |

**Best in class:** Competely (for speed and breadth of automated extraction).

**What they all lack:** Evidence archival, human review workflow, entity hierarchies, temporal analysis.

---

## Category 3: Web Scraping & Data Collection

Tools that automate data gathering but provide no analysis layer.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Browse AI** | 2021 | Free-$249/mo | No-code web scraping, scheduled extraction, 2M+ users | Extraction only — no analysis, no entity model, no reporting |
| **Apify** | 2015 | Free-$49+/mo | 1,600+ pre-built scrapers, serverless, developer-focused | Technical (code-required), no analysis layer |
| **Firecrawl** | 2024 | Free-$500/mo | LLM-ready web crawling, markdown output, API-first | Infrastructure tool, no analysis, no UI |
| **Kadoa** | 2023 | Custom | AI-powered web scraping, no selectors needed | Extraction tool only |

**Best in class:** Browse AI (for ease), Firecrawl (for LLM integration).

**Relevant insight:** These tools solve capture but not analysis. Our app does both.

---

## Category 4: UI/Design Research Platforms

Curated libraries of product screenshots and design patterns.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Mobbin** | 2018 | ~$130/yr | 300K+ screens, 1,100+ iOS/Android/Web apps, flow recordings | View-only library, no custom research, no extraction |
| **Screenlane** | 2020 | $99/yr | Real user flow recordings, timestamped | Paywalled, no analysis, no custom entities |
| **Refero** | 2019 | Free-$50/yr | 60K+ screenshots, page-type categorisation | Smaller library, no custom analysis |
| **Pageflows** | 2018 | ~$99/yr | User flow recordings with annotations | Niche (flows only), no structured data |

**Best in class:** Mobbin (depth and categorisation).

**Relevant insight:** These are SOURCES for our app (we already scrape from galleries), not competitors. None offers structured analysis or comparison.

---

## Category 5: User Research Repositories

Tools for storing and analysing qualitative research (interviews, usability tests). Adjacent, not competitive.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Dovetail** | 2017 | Free-$29+/user/mo | Qualitative data analysis, AI-powered coding, team collaboration | Qualitative-focused, no market/competitive research |
| **Notably** | 2020 | Custom | AI-powered research synthesis, auto-tagging | Small, qualitative only |
| **Condens** | 2019 | €19+/user/mo | Research repository, tag-based analysis | Team tool, no competitive intelligence |

**Best in class:** Dovetail (market leader in user research repositories).

**Relevant insight:** Dovetail's evidence-tagging and synthesis model is relevant for our evidence library design, but they don't do market/competitive research.

---

## Category 6: DIY Platforms (Flexible Databases)

General-purpose tools that CAN be used for competitive research with heavy configuration.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Airtable** | 2012 | Free-$20+/user/mo | Flexible schema, 250K+ templates, interfaces | General-purpose (not research-optimised), no capture, no extraction, no AI analysis |
| **Notion** | 2013 | Free-$8+/user/mo | Wiki + database + docs, CI templates exist | Too generic, no automation, no evidence handling |
| **Coda** | 2014 | Free-$10+/user/mo | Doc-database hybrid, AI assist | No capture or extraction pipeline |

**Best in class:** Airtable (for schema flexibility).

**Relevant insight:** Airtable is what people USE today for manual competitive research. They'd switch to our app if it automated the capture/extraction/analysis cycle.

---

## Category 7: Data Visualisation & Reporting

Tools for creating publication-quality charts and reports from existing data.

| Tool | Founded | Pricing | Key Strengths | Key Gaps |
|------|---------|---------|---------------|----------|
| **Flourish** (Canva) | 2016 | Free-$69+/mo | Interactive charts, storytelling, embeddable | Visualisation only, no data gathering |
| **Datawrapper** | 2012 | Free-$599/mo | Fast chart creation, responsive, newsroom-standard | Chart tool only |
| **Observable** | 2019 | Free-$35+/user/mo | Notebook-style analysis, D3.js, data exploration | Technical (code-required) |

**Best in class:** Flourish (for interactive storytelling output).

**Relevant insight:** These set the bar for output quality. Our interactive HTML reports should aim for Flourish-level polish.

---

## Insurance/Sector-Specific Tools

| Tool | Type | Relevance |
|------|------|-----------|
| **Prisync** | E-commerce price monitoring ($99+/mo) | Price tracking concept relevant, but e-commerce only |
| **Insurance Comparison APIs** (GoCompare, MoneySupermarket) | Consumer comparison | Consumer-facing, not analyst tools |
| **BIBA / ABI databases** | Industry body data | Data sources, not tools |
| **Oxbow Partners** | Insurance consultancy | Publish reports we'd consume, not a tool |

---

## Market Size & Trends

- **CI tools market:** $0.56B (2024) → $1.62B (2033), 12.5% CAGR (Fortune Business Insights)
- **Agentic browser market:** $4.5B (2025) → $76.8B (2034) (NohacksPod)
- **Key trend 2025-2026:** AI agents capable of autonomous web browsing hitting production (Google Chrome auto-browse, OpenAI Atlas, Salesforce Agentforce)
- **NL2SQL accuracy:** Now 96%+ on standard benchmarks (specialist models)
- **Multimodal extraction:** Vision-language models replacing traditional OCR for document understanding

---

## The Gap This App Fills

| Capability | Enterprise CI (Crayon/Klue) | AI-Native (Competely) | DIY (Airtable) | **Research Workbench** |
|---|---|---|---|---|
| Flexible entity schema | No | No | Yes | **Yes, AI-guided** |
| Evidence capture + archival | Partial | No | No | **Yes, 8 sources** |
| AI extraction + human review | No | Partial (no review) | No | **Yes, full pipeline** |
| Analysis lenses | Partial | No | No | **Yes, 6 lenses** |
| Temporal tracking | Partial | No | No | **Yes, per-attribute** |
| Local-first / desktop | No | No | No | **Yes** |
| Solo analyst pricing | No ($15-40K) | Partial ($9-99) | Partial ($20/mo) | **Free (self-hosted)** |
| Evidence provenance chain | No | No | No | **Yes, full chain** |
| Domain-agnostic | No (CI only) | No (CI only) | Yes | **Yes** |

---

## Sources

- [Crayon](https://www.crayon.co/) — Enterprise CI platform
- [Klue](https://klue.com/) — Sales enablement CI
- [AlphaSense](https://www.alpha-sense.com/) — Financial intelligence
- [Contify](https://www.contify.com/) — AI market intelligence
- [Competely](https://competely.ai/) — AI competitor analysis
- [RivalSense](https://rivalsense.co/) — Founder-focused CI
- [Browse AI](https://www.browse.ai/) — No-code web scraping
- [Firecrawl](https://firecrawl.dev/) — LLM-ready web crawling
- [Mobbin](https://mobbin.com/) — UI design library
- [Dovetail](https://dovetail.com/) — User research repository
- [Airtable](https://www.airtable.com/) — Flexible database
- [Flourish](https://flourish.studio/) — Interactive data visualisation
- [Fortune Business Insights](https://www.fortunebusinessinsights.com/competitive-intelligence-tools-market-104522) — CI market sizing
- [NohacksPod](https://www.nohackspod.com/blog/agentic-browser-landscape-2026) — Agentic browser landscape
