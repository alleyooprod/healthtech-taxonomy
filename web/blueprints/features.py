"""Feature Standardisation API — canonical vocabulary management.

Endpoints:
    GET    /api/features                   — List canonical features for a project
    POST   /api/features                   — Create a canonical feature
    GET    /api/features/<id>              — Get a feature with its mappings
    PUT    /api/features/<id>              — Update a feature
    DELETE /api/features/<id>              — Delete a feature
    POST   /api/features/merge             — Merge features into one
    GET    /api/features/categories         — List distinct categories
    POST   /api/features/<id>/mappings     — Add a mapping to a feature
    DELETE /api/features/mappings/<id>     — Remove a mapping
    POST   /api/features/resolve           — Resolve a raw value to canonical
    GET    /api/features/unmapped          — Find unmapped extracted values
    GET    /api/features/stats             — Vocabulary statistics
    POST   /api/features/suggest           — AI suggests canonical names for raw values
"""
import json

from flask import Blueprint, request, jsonify, current_app
from loguru import logger

features_bp = Blueprint("features", __name__)


@features_bp.route("/api/features", methods=["GET"])
def list_features():
    """List canonical features. Query: ?project_id=X&attr_slug=Y&category=Z&search=W"""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    attr_slug = request.args.get("attr_slug")
    category = request.args.get("category")
    search = request.args.get("search")

    db = current_app.db
    features = db.get_canonical_features(
        project_id, attr_slug=attr_slug, category=category, search=search,
    )
    return jsonify(features)


@features_bp.route("/api/features", methods=["POST"])
def create_feature():
    """Create a canonical feature.

    Body: {project_id, attr_slug, canonical_name, [description], [category], [mappings]}
    """
    data = request.json or {}
    project_id = data.get("project_id")
    attr_slug = data.get("attr_slug")
    canonical_name = data.get("canonical_name")

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    if not attr_slug:
        return jsonify({"error": "attr_slug is required"}), 400
    if not canonical_name or not canonical_name.strip():
        return jsonify({"error": "canonical_name is required"}), 400

    db = current_app.db
    fid = db.create_canonical_feature(
        project_id, attr_slug, canonical_name.strip(),
        description=data.get("description"),
        category=data.get("category"),
    )
    if fid is None:
        return jsonify({"error": "Feature already exists"}), 409

    # Auto-add the canonical name itself as a mapping
    db.add_feature_mapping(fid, canonical_name.strip())

    # Add optional initial mappings
    for raw in data.get("mappings", []):
        if raw and raw.strip():
            db.add_feature_mapping(fid, raw.strip())

    feature = db.get_canonical_feature(fid)
    return jsonify(feature), 201


@features_bp.route("/api/features/<int:feature_id>", methods=["GET"])
def get_feature(feature_id):
    """Get a canonical feature with its mappings."""
    db = current_app.db
    feature = db.get_canonical_feature(feature_id)
    if not feature:
        return jsonify({"error": "Feature not found"}), 404
    return jsonify(feature)


@features_bp.route("/api/features/<int:feature_id>", methods=["PUT"])
def update_feature(feature_id):
    """Update a canonical feature.

    Body: {[canonical_name], [description], [category]}
    """
    data = request.json or {}
    db = current_app.db

    feature = db.get_canonical_feature(feature_id)
    if not feature:
        return jsonify({"error": "Feature not found"}), 404

    updates = {}
    if "canonical_name" in data:
        name = data["canonical_name"]
        if not name or not name.strip():
            return jsonify({"error": "canonical_name cannot be empty"}), 400
        updates["canonical_name"] = name.strip()
    if "description" in data:
        updates["description"] = data["description"]
    if "category" in data:
        updates["category"] = data["category"]

    if updates:
        db.update_canonical_feature(feature_id, **updates)

    return jsonify(db.get_canonical_feature(feature_id))


@features_bp.route("/api/features/<int:feature_id>", methods=["DELETE"])
def delete_feature(feature_id):
    """Delete a canonical feature and its mappings."""
    db = current_app.db
    feature = db.get_canonical_feature(feature_id)
    if not feature:
        return jsonify({"error": "Feature not found"}), 404

    db.delete_canonical_feature(feature_id)
    return jsonify({"status": "deleted", "feature_id": feature_id})


@features_bp.route("/api/features/merge", methods=["POST"])
def merge_features():
    """Merge source features into target.

    Body: {target_id, source_ids: [1,2,3]}
    """
    data = request.json or {}
    target_id = data.get("target_id")
    source_ids = data.get("source_ids", [])

    if not target_id:
        return jsonify({"error": "target_id is required"}), 400
    if not source_ids:
        return jsonify({"error": "source_ids is required"}), 400

    db = current_app.db
    target = db.get_canonical_feature(target_id)
    if not target:
        return jsonify({"error": "Target feature not found"}), 404

    count = db.merge_canonical_features(target_id, source_ids)
    merged = db.get_canonical_feature(target_id)
    return jsonify({
        "status": "merged",
        "target": merged,
        "mappings_moved": count,
        "sources_deleted": len(source_ids),
    })


@features_bp.route("/api/features/categories", methods=["GET"])
def list_categories():
    """List distinct feature categories. Query: ?project_id=X&attr_slug=Y"""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    attr_slug = request.args.get("attr_slug")
    db = current_app.db
    categories = db.get_canonical_categories(project_id, attr_slug=attr_slug)
    return jsonify(categories)


@features_bp.route("/api/features/<int:feature_id>/mappings", methods=["POST"])
def add_mapping(feature_id):
    """Add a mapping to a canonical feature.

    Body: {raw_value}
    """
    data = request.json or {}
    raw_value = data.get("raw_value")

    if not raw_value or not raw_value.strip():
        return jsonify({"error": "raw_value is required"}), 400

    db = current_app.db
    feature = db.get_canonical_feature(feature_id)
    if not feature:
        return jsonify({"error": "Feature not found"}), 404

    mid = db.add_feature_mapping(feature_id, raw_value.strip())
    if mid is None:
        return jsonify({"error": "Mapping already exists"}), 409

    return jsonify({"mapping_id": mid, "raw_value": raw_value.strip()}), 201


@features_bp.route("/api/features/mappings/<int:mapping_id>", methods=["DELETE"])
def remove_mapping(mapping_id):
    """Remove a feature mapping."""
    db = current_app.db
    db.remove_feature_mapping(mapping_id)
    return jsonify({"status": "deleted", "mapping_id": mapping_id})


@features_bp.route("/api/features/resolve", methods=["POST"])
def resolve_value():
    """Resolve a raw value to its canonical feature.

    Body: {project_id, attr_slug, raw_value}
    """
    data = request.json or {}
    project_id = data.get("project_id")
    attr_slug = data.get("attr_slug")
    raw_value = data.get("raw_value")

    if not all([project_id, attr_slug, raw_value]):
        return jsonify({"error": "project_id, attr_slug, and raw_value are required"}), 400

    db = current_app.db
    canonical = db.resolve_raw_value(project_id, attr_slug, raw_value)
    if canonical:
        return jsonify({"matched": True, "canonical": canonical})
    return jsonify({"matched": False, "canonical": None})


@features_bp.route("/api/features/unmapped", methods=["GET"])
def get_unmapped():
    """Find extracted values without canonical mappings.

    Query: ?project_id=X&attr_slug=Y
    """
    project_id = request.args.get("project_id", type=int)
    attr_slug = request.args.get("attr_slug")

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    if not attr_slug:
        return jsonify({"error": "attr_slug is required"}), 400

    db = current_app.db
    unmapped = db.get_unmapped_values(project_id, attr_slug)
    return jsonify({"unmapped": unmapped, "count": len(unmapped)})


@features_bp.route("/api/features/stats", methods=["GET"])
def get_vocabulary_stats():
    """Get vocabulary statistics. Query: ?project_id=X"""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    db = current_app.db
    stats = db.get_feature_vocabulary_stats(project_id)
    return jsonify(stats)


@features_bp.route("/api/features/suggest", methods=["POST"])
def suggest_canonical_names():
    """AI suggests canonical names for a list of raw extracted values.

    Body: {project_id, attr_slug, raw_values: [...], [model]}
    """
    data = request.json or {}
    project_id = data.get("project_id")
    attr_slug = data.get("attr_slug")
    raw_values = data.get("raw_values", [])
    model = data.get("model")

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    if not attr_slug:
        return jsonify({"error": "attr_slug is required"}), 400
    if not raw_values:
        return jsonify({"error": "raw_values is required"}), 400

    db = current_app.db

    # Get existing canonical features for context
    existing = db.get_canonical_features(project_id, attr_slug=attr_slug)
    existing_names = [f["canonical_name"] for f in existing]

    from core.llm import run_cli

    prompt = f"""You are a research analyst standardising feature/attribute vocabulary.

TASK: For each raw extracted value below, suggest a canonical (standardised) name.
If a value matches an existing canonical name, map it to that name.
If it's a new concept, propose a clean, concise canonical name.

EXISTING CANONICAL NAMES:
{json.dumps(existing_names, indent=2) if existing_names else "(none yet)"}

RAW VALUES TO STANDARDISE:
{json.dumps(raw_values, indent=2)}

RULES:
1. Canonical names should be Title Case, concise, and unambiguous
2. Group synonyms and variations under one canonical name
3. Preserve meaningful distinctions — don't over-merge
4. For each raw value, return the canonical name and whether it's new or existing"""

    schema = {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "raw_value": {"type": "string"},
                        "canonical_name": {"type": "string"},
                        "is_new": {"type": "boolean"},
                        "category": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["raw_value", "canonical_name", "is_new"],
                },
            },
        },
        "required": ["suggestions"],
    }

    try:
        response = run_cli(
            prompt=prompt,
            model=model or "claude-sonnet-4-6",
            timeout=60,
            json_schema=json.dumps(schema),
        )

        if response.get("is_error"):
            return jsonify({"error": response.get("result", "LLM error")}), 422

        structured = response.get("structured_output")
        if not structured:
            try:
                from json_repair import loads as repair_loads
                structured = repair_loads(response.get("result", "{}"))
            except Exception:
                return jsonify({"error": "LLM did not return structured output"}), 422

        return jsonify({
            "suggestions": structured.get("suggestions", []),
            "cost_usd": response.get("cost_usd", 0),
        })

    except Exception as e:
        logger.error("Feature suggestion failed: %s", e)
        return jsonify({"error": str(e)}), 422
