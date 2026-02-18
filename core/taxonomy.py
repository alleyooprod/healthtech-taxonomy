"""Taxonomy evolution: reviews and restructures categories after each batch."""
import json
import subprocess

from config import (
    CLAUDE_BIN, CLAUDE_COMMON_FLAGS, PROMPTS_DIR,
    EVOLVE_TIMEOUT,
)
from core.classifier import build_taxonomy_tree_string

REVIEW_TIMEOUT = 180  # Full review is more complex, allow 3 minutes


def evolve_taxonomy(db, batch_id, model="claude-opus-4-6", project_id=None):
    """Review and evolve taxonomy after a batch completes.

    Calls Claude to analyze the current taxonomy state and propose changes.
    Applies approved changes to the database.
    """
    taxonomy_tree = build_taxonomy_tree_string(db, project_id=project_id)
    batch_companies = db.get_batch_companies(batch_id)
    stats = db.get_stats(project_id=project_id)

    if not batch_companies:
        print("  No companies in batch to analyze for taxonomy evolution.")
        return []

    # Build summary of new companies
    company_summaries = []
    for c in batch_companies:
        tags = json.loads(c["tags"]) if isinstance(c["tags"], str) else c.get("tags", [])
        company_summaries.append(
            f"- {c['name']}: {(c.get('what') or '')[:150]}"
        )
    new_companies_text = "\n".join(company_summaries)

    prompt_template = (PROMPTS_DIR / "evolve_taxonomy.txt").read_text()
    prompt = prompt_template.format(
        taxonomy_tree=taxonomy_tree,
        new_companies=new_companies_text,
        total_companies=stats["total_companies"],
    )

    schema = (PROMPTS_DIR / "schemas" / "taxonomy_evolution.json").read_text()

    cmd = [
        CLAUDE_BIN,
        "-p", prompt,
        *CLAUDE_COMMON_FLAGS,
        "--json-schema", schema,
        "--tools", "",
        "--model", model,
        "--no-session-persistence",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=EVOLVE_TIMEOUT,
    )

    if result.returncode != 0:
        print(f"  Warning: Taxonomy evolution failed: {result.stderr[:300] if result.stderr else 'unknown'}")
        return []

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  Warning: Could not parse taxonomy evolution output")
        return []

    structured = response.get("structured_output")
    if not structured:
        raw = response.get("result", "")
        try:
            structured = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            print(f"  Warning: No structured taxonomy evolution output")
            return []

    print(f"  Taxonomy analysis: {structured.get('analysis', '')[:200]}")

    if structured.get("no_changes_needed"):
        print("  No taxonomy changes needed.")
        return []

    changes = structured.get("changes", [])
    applied = []

    for change in changes:
        change_type = change.get("type")
        reason = change.get("reason", "")

        try:
            if change_type == "add":
                name = change.get("category_name")
                if name:
                    cat_id = db.add_category(name, project_id=project_id)
                    if cat_id:
                        db.log_taxonomy_change("add", {"name": name}, reason, [cat_id],
                                               project_id=project_id)
                        print(f"  + Added category: {name}")
                        applied.append(change)

            elif change_type == "merge":
                source = change.get("category_name")
                target = change.get("merge_into")
                if source and target:
                    success = db.merge_categories(source, target, reason,
                                                  project_id=project_id)
                    if success:
                        print(f"  ~ Merged '{source}' into '{target}'")
                        applied.append(change)

            elif change_type == "rename":
                old_name = change.get("category_name")
                new_name = change.get("new_name")
                if old_name and new_name:
                    success = db.rename_category(old_name, new_name, reason,
                                                 project_id=project_id)
                    if success:
                        print(f"  ~ Renamed '{old_name}' to '{new_name}'")
                        applied.append(change)

            elif change_type == "add_subcategory":
                name = change.get("category_name")
                parent_name = change.get("parent_category")
                if name and parent_name:
                    parent = db.get_category_by_name(parent_name, project_id=project_id)
                    if parent:
                        cat_id = db.add_category(name, parent_id=parent["id"],
                                                 project_id=project_id)
                        if cat_id:
                            db.log_taxonomy_change(
                                "add_subcategory",
                                {"name": name, "parent": parent_name},
                                reason, [cat_id], project_id=project_id,
                            )
                            print(f"  + Added subcategory: {name} (under {parent_name})")
                            applied.append(change)

            elif change_type == "split":
                source = change.get("category_name")
                new_cats = change.get("split_into", [])
                if source and new_cats:
                    for new_name in new_cats:
                        db.add_category(new_name, project_id=project_id)
                    db.log_taxonomy_change(
                        "split",
                        {"from": source, "into": new_cats},
                        reason, project_id=project_id,
                    )
                    print(f"  / Split '{source}' into {new_cats}")
                    applied.append(change)

        except Exception as e:
            print(f"  Warning: Failed to apply {change_type} change: {e}")

    return applied


def review_taxonomy(db, model="claude-opus-4-6", project_id=None, observations=""):
    """Full taxonomy review — proposes changes but does NOT apply them.

    Returns dict with 'analysis' and 'changes' for user confirmation.
    """
    taxonomy_tree = build_taxonomy_tree_string(db, project_id=project_id)
    companies = db.get_companies(project_id=project_id)
    stats = db.get_stats(project_id=project_id)

    if not companies:
        return {"analysis": "No companies in taxonomy to review.", "changes": []}

    # Build full company list summary
    company_lines = []
    for c in companies:
        cat = c.get("category_name", "Uncategorized")
        company_lines.append(
            f"- [{cat}] {c['name']}: {(c.get('what') or '')[:120]}"
        )
    all_companies_text = "\n".join(company_lines)

    prompt_template = (PROMPTS_DIR / "review_taxonomy.txt").read_text()
    prompt = prompt_template.format(
        taxonomy_tree=taxonomy_tree,
        all_companies=all_companies_text,
        total_companies=stats["total_companies"],
    )

    # Append user observations if provided
    if observations:
        prompt += f"\n\nUSER OBSERVATIONS (prioritize these):\n{observations}"

    schema = (PROMPTS_DIR / "schemas" / "taxonomy_evolution.json").read_text()

    cmd = [
        CLAUDE_BIN,
        "-p", prompt,
        *CLAUDE_COMMON_FLAGS,
        "--json-schema", schema,
        "--tools", "",
        "--model", model,
        "--no-session-persistence",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=REVIEW_TIMEOUT,
    )

    if result.returncode != 0:
        stderr = result.stderr[:300] if result.stderr else "unknown"
        return {"error": f"Review failed: {stderr}", "changes": []}

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Could not parse review output", "changes": []}

    structured = response.get("structured_output")
    if not structured:
        raw = response.get("result", "")
        try:
            structured = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"error": "No structured output from review", "changes": []}

    return structured


def apply_taxonomy_changes(db, changes, project_id=None):
    """Apply a list of taxonomy changes (after user confirmation).

    Returns list of successfully applied changes.
    """
    applied = []
    for change in changes:
        change_type = change.get("type")
        reason = change.get("reason", "")

        try:
            if change_type == "add":
                name = change.get("category_name")
                if name:
                    cat_id = db.add_category(name, project_id=project_id)
                    if cat_id:
                        db.log_taxonomy_change("add", {"name": name}, reason, [cat_id],
                                               project_id=project_id)
                        applied.append(change)

            elif change_type == "merge":
                source = change.get("category_name")
                target = change.get("merge_into")
                if source and target:
                    success = db.merge_categories(source, target, reason,
                                                  project_id=project_id)
                    if success:
                        applied.append(change)

            elif change_type == "rename":
                old_name = change.get("category_name")
                new_name = change.get("new_name")
                if old_name and new_name:
                    success = db.rename_category(old_name, new_name, reason,
                                                 project_id=project_id)
                    if success:
                        applied.append(change)

            elif change_type == "add_subcategory":
                name = change.get("category_name")
                parent_name = change.get("parent_category")
                if name and parent_name:
                    parent = db.get_category_by_name(parent_name, project_id=project_id)
                    if parent:
                        cat_id = db.add_category(name, parent_id=parent["id"],
                                                 project_id=project_id)
                        if cat_id:
                            db.log_taxonomy_change(
                                "add_subcategory",
                                {"name": name, "parent": parent_name},
                                reason, [cat_id], project_id=project_id,
                            )
                            applied.append(change)

            elif change_type == "split":
                source = change.get("category_name")
                new_cats = change.get("split_into", [])
                if source and new_cats:
                    for new_name in new_cats:
                        db.add_category(new_name, project_id=project_id)
                    db.log_taxonomy_change(
                        "split", {"from": source, "into": new_cats}, reason,
                        project_id=project_id,
                    )
                    applied.append(change)

            elif change_type == "move":
                company_name = change.get("category_name")
                target_cat = change.get("merge_into")
                if company_name and target_cat:
                    target = db.get_category_by_name(target_cat, project_id=project_id)
                    if target:
                        companies = db.get_companies(search=company_name,
                                                     project_id=project_id)
                        for c in companies:
                            if c["name"].lower() == company_name.lower():
                                db.update_company(c["id"], {
                                    "category_id": target["id"],
                                })
                                db.log_taxonomy_change(
                                    "move",
                                    {"company": company_name, "to": target_cat},
                                    reason, project_id=project_id,
                                )
                                applied.append(change)
                                break

        except Exception as e:
            print(f"  Warning: Failed to apply {change_type} change: {e}")

    return applied
