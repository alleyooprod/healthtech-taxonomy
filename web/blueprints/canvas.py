"""Canvas API: visual workspaces for arranging companies and notes."""
from flask import Blueprint, current_app, jsonify, request

canvas_bp = Blueprint("canvas", __name__)


@canvas_bp.route("/api/canvases", methods=["POST"])
def create_canvas():
    data = request.json or {}
    project_id = data.get("project_id")
    title = data.get("title", "Untitled Canvas").strip() or "Untitled Canvas"
    canvas_id = current_app.db.create_canvas(project_id, title)
    return jsonify({"id": canvas_id, "status": "ok"})


@canvas_bp.route("/api/canvases")
def list_canvases():
    project_id = request.args.get("project_id", type=int)
    items = current_app.db.list_canvases(project_id)
    return jsonify(items)


@canvas_bp.route("/api/canvases/<int:canvas_id>")
def get_canvas(canvas_id):
    item = current_app.db.get_canvas(canvas_id)
    if not item:
        return jsonify({"error": "Not found"}), 404
    return jsonify(item)


@canvas_bp.route("/api/canvases/<int:canvas_id>", methods=["PUT"])
def update_canvas(canvas_id):
    fields = request.json or {}
    current_app.db.update_canvas(canvas_id, fields)
    return jsonify({"status": "ok"})


@canvas_bp.route("/api/canvases/<int:canvas_id>", methods=["DELETE"])
def delete_canvas(canvas_id):
    current_app.db.delete_canvas(canvas_id)
    return jsonify({"status": "ok"})
