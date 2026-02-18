"""Taxonomy API: tree, history, review, quality."""
from flask import Blueprint, current_app, jsonify, request

from config import DEFAULT_MODEL
from core.git_sync import sync_to_git_async
from storage.export import export_markdown, export_json
from web.async_jobs import start_async_job, write_result, poll_result
from web.notifications import notify_sse, send_slack

taxonomy_bp = Blueprint("taxonomy", __name__)


@taxonomy_bp.route("/api/taxonomy")
def get_taxonomy():
    project_id = request.args.get("project_id", type=int)
    stats = current_app.db.get_category_stats(project_id=project_id)
    return jsonify(stats)


@taxonomy_bp.route("/api/taxonomy/history")
def taxonomy_history():
    project_id = request.args.get("project_id", type=int)
    history = current_app.db.get_taxonomy_history(project_id=project_id)
    return jsonify(history)


# --- Review ---

def _run_taxonomy_review(job_id, project_id, model, observations):
    import json
    from core.taxonomy import review_taxonomy
    from storage.db import Database
    review_db = Database()
    result = review_taxonomy(review_db, model=model, project_id=project_id,
                             observations=observations)
    write_result("review", job_id, result)


@taxonomy_bp.route("/api/taxonomy/review", methods=["POST"])
def start_taxonomy_review():
    data = request.json or {}
    project_id = data.get("project_id")
    model = data.get("model", DEFAULT_MODEL)
    observations = data.get("observations", "")

    review_id = start_async_job("review", _run_taxonomy_review,
                                project_id, model, observations)
    return jsonify({"review_id": review_id})


@taxonomy_bp.route("/api/taxonomy/review/<review_id>")
def get_taxonomy_review(review_id):
    result = poll_result("review", review_id)
    if result.get("status") == "pending":
        return jsonify(result)
    return jsonify({"status": "complete", "result": result})


@taxonomy_bp.route("/api/taxonomy/review/apply", methods=["POST"])
def apply_taxonomy_review():
    from core.taxonomy import apply_taxonomy_changes
    db = current_app.db
    data = request.json
    changes = data.get("changes", [])
    project_id = data.get("project_id")
    applied = apply_taxonomy_changes(db, changes, project_id=project_id)
    export_markdown(db, project_id=project_id)
    export_json(db, project_id=project_id)
    if project_id and applied:
        desc = f"Applied {len(applied)} taxonomy changes"
        db.log_activity(project_id, "taxonomy_changed", desc, "taxonomy", None)
        notify_sse(project_id, "taxonomy_changed",
                   {"count": len(applied), "changes": applied})
        prefs = db.get_notification_prefs(project_id)
        if prefs and prefs.get("notify_taxonomy_change"):
            send_slack(project_id, f"Taxonomy updated: {desc}")
    if applied:
        sync_to_git_async(f"Taxonomy: {len(applied)} changes applied")
    return jsonify({"applied": len(applied), "changes": applied})


@taxonomy_bp.route("/api/taxonomy/quality")
def taxonomy_quality():
    project_id = request.args.get("project_id", type=int)
    quality = current_app.db.get_taxonomy_quality(project_id)
    return jsonify(quality)
