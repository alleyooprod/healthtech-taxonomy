"""Export taxonomy data to JSON, Markdown, and CSV."""
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from config import DATA_DIR


def export_json(db, output_path=None, project_id=None):
    """Export full taxonomy to JSON."""
    output_path = output_path or (DATA_DIR / "taxonomy_data.json")
    companies = db.get_companies(project_id=project_id)
    categories = db.get_categories(project_id=project_id)
    stats = db.get_stats(project_id=project_id)

    data = {
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "total_companies": stats["total_companies"],
            "total_categories": stats["total_categories"],
            "exported_at": datetime.now().isoformat(),
        },
        "categories": categories,
        "companies": companies,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return output_path


def export_markdown(db, output_path=None, project_id=None):
    """Export taxonomy as LLM-optimized markdown for Claude/FigJam."""
    output_path = output_path or (DATA_DIR / "taxonomy_master.md")
    companies = db.get_companies(project_id=project_id)
    stats = db.get_stats(project_id=project_id)
    category_stats = db.get_category_stats(project_id=project_id)

    lines = []

    # === Section 1: Metadata Header ===
    lines.append("---")
    lines.append("document_type: healthtech_taxonomy")
    lines.append(f"last_updated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"total_companies: {stats['total_companies']}")
    lines.append(f"total_categories: {stats['total_categories']}")
    lines.append("format_version: 2.0")
    lines.append("purpose: Market taxonomy for healthtech, wellness, fitness, and health insurance companies")
    lines.append("---")
    lines.append("")

    # === Section 2: Title ===
    lines.append("# Healthtech Market Taxonomy")
    lines.append("")
    lines.append(
        f"> **{stats['total_companies']} companies** across "
        f"**{stats['total_categories']} categories** | "
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    lines.append("")

    # === Section 3: Taxonomy Tree ===
    lines.append("## Taxonomy Tree")
    lines.append("")
    lines.append("```")
    top_level = sorted(
        [c for c in category_stats if c["parent_id"] is None],
        key=lambda x: x["name"],
    )
    subcategories = [c for c in category_stats if c["parent_id"] is not None]

    for cat in top_level:
        lines.append(f"+-- {cat['name']} ({cat['company_count']})")
        subs = sorted(
            [s for s in subcategories if s["parent_id"] == cat["id"]],
            key=lambda x: x["name"],
        )
        for i, sub in enumerate(subs):
            connector = "|   +--" if i < len(subs) - 1 else "    +--"
            lines.append(f"{connector} {sub['name']} ({sub['company_count']})")
    lines.append("```")
    lines.append("")

    # === Section 4: Summary Statistics ===
    lines.append("## Summary Statistics")
    lines.append("")

    # Category distribution table
    lines.append("### Category Distribution")
    lines.append("")
    lines.append("| Category | Companies | % of Total |")
    lines.append("|----------|----------:|-----------:|")
    total = max(stats["total_companies"], 1)
    for cat in sorted(top_level, key=lambda x: -x["company_count"]):
        pct = (cat["company_count"] / total) * 100
        lines.append(f"| {cat['name']} | {cat['company_count']} | {pct:.0f}% |")
    lines.append("")

    # Tag distribution
    all_tags = []
    for c in companies:
        tags = c.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)
        all_tags.extend(tags)

    if all_tags:
        tag_counts = Counter(all_tags)
        lines.append("### Tag Distribution")
        lines.append("")
        lines.append("| Tag | Count |")
        lines.append("|-----|------:|")
        for tag, count in tag_counts.most_common():
            lines.append(f"| {tag} | {count} |")
        lines.append("")

    # === Section 5: Company Cards by Category ===
    lines.append("## Companies by Category")
    lines.append("")

    by_category = {}
    for company in companies:
        cat = company.get("category_name") or "Uncategorized"
        by_category.setdefault(cat, []).append(company)

    for category in sorted(by_category.keys()):
        cat_companies = sorted(by_category[category], key=lambda x: x["name"])
        lines.append(f"### {category} ({len(cat_companies)} companies)")
        lines.append("")

        for company in cat_companies:
            tags = company.get("tags", [])
            if isinstance(tags, str):
                tags = json.loads(tags)
            tag_str = ", ".join(tags) if tags else "none"
            confidence = (
                f"{company['confidence_score'] * 100:.0f}%"
                if company.get("confidence_score") is not None
                else "N/A"
            )

            lines.append(f"#### {company['name']}")
            lines.append("")
            lines.append(f"- **URL**: {company['url']}")
            lines.append(
                f"- **Category**: {company.get('category_name', 'N/A')}"
                f" > {company.get('subcategory_name', 'N/A')}"
            )
            lines.append(f"- **Tags**: {tag_str}")
            lines.append(f"- **Confidence**: {confidence}")
            lines.append(f"- **What**: {company.get('what', 'N/A')}")
            lines.append(f"- **Target**: {company.get('target', 'N/A')}")
            lines.append(f"- **Products**: {company.get('products', 'N/A')}")
            lines.append(f"- **Funding**: {company.get('funding', 'N/A')}")
            lines.append(f"- **Geography**: {company.get('geography', 'N/A')}")
            lines.append(f"- **TAM**: {company.get('tam', 'N/A')}")
            lines.append(f"- **Processed**: {company.get('processed_at', 'N/A')}")
            lines.append("")

    # === Section 6: Visualization Instructions ===
    lines.append("---")
    lines.append("")
    lines.append("## Visualization Instructions")
    lines.append("")
    lines.append("To create a FigJam board from this data, use these prompts with Claude:")
    lines.append("")
    lines.append(
        '1. **Taxonomy Map**: "Create a FigJam board showing the taxonomy tree '
        'with category nodes and company cards underneath each category"'
    )
    lines.append(
        '2. **2x2 Matrix**: "Create a 2x2 grid plotting companies by '
        '[B2B vs B2C] x [Preventive vs Reactive]"'
    )
    lines.append(
        '3. **Competitive Landscape**: "Create a FigJam board grouping '
        'companies by their tags (competitor, partner, infrastructure)"'
    )
    lines.append(
        '4. **Funding Landscape**: "Visualize companies by funding stage '
        'across categories"'
    )
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return output_path


def export_csv(db, output_path=None, project_id=None):
    """Export taxonomy as CSV."""
    output_path = output_path or (DATA_DIR / "taxonomy_export.csv")
    companies = db.get_companies(project_id=project_id)

    fieldnames = [
        "name", "url", "category_name", "subcategory_name", "what", "target",
        "products", "funding", "geography", "tam", "tags", "confidence_score",
        "employee_range", "founded_year", "funding_stage", "total_funding_usd",
        "hq_city", "hq_country", "linkedin_url", "is_starred", "completeness",
        "processed_at",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for company in companies:
            row = dict(company)
            row["tags"] = ", ".join(row.get("tags", []))
            writer.writerow(row)
    return output_path
