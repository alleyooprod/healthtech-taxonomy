"""Settings API: share tokens, shared view, notifications, activity, SSE stream."""
import json
import queue

from flask import Blueprint, current_app, jsonify, request

from web.notifications import sse_clients, _is_valid_slack_webhook

settings_bp = Blueprint("settings", __name__)


# --- Share Tokens ---

@settings_bp.route("/api/share-tokens", methods=["GET"])
def list_share_tokens():
    project_id = request.args.get("project_id", type=int)
    return jsonify(current_app.db.get_share_tokens(project_id))


@settings_bp.route("/api/share-tokens", methods=["POST"])
def create_share_token():
    db = current_app.db
    data = request.json
    project_id = data.get("project_id")
    label = data.get("label", "Shared link")
    token = db.create_share_token(project_id, label=label)
    if project_id:
        db.log_activity(project_id, "share_created",
                        f"Created share link: {label}", "project", project_id)
    return jsonify({"token": token, "url": f"/shared/{token}"})


@settings_bp.route("/api/share-tokens/<int:token_id>", methods=["DELETE"])
def revoke_share_token(token_id):
    current_app.db.revoke_share_token(token_id)
    return jsonify({"ok": True})


# --- Shared View (public) ---

@settings_bp.route("/shared/<token>")
def shared_view(token):
    db = current_app.db
    share = db.validate_share_token(token)
    if not share:
        return jsonify({"error": "Invalid or expired share link"}), 404
    project_id = share["project_id"]
    companies = db.get_companies(project_id=project_id)
    categories = db.get_category_stats(project_id=project_id)
    stats = db.get_stats(project_id=project_id)
    return jsonify({
        "project_id": project_id,
        "companies": companies,
        "categories": categories,
        "stats": stats,
        "label": share.get("label", "Shared view"),
        "read_only": True,
    })


# --- Activity Log ---

@settings_bp.route("/api/activity")
def get_activity():
    project_id = request.args.get("project_id", type=int)
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify(current_app.db.get_activity(project_id, limit=limit, offset=offset))


# --- Notification Preferences ---

@settings_bp.route("/api/notification-prefs", methods=["GET"])
def get_notification_prefs():
    project_id = request.args.get("project_id", type=int)
    prefs = current_app.db.get_notification_prefs(project_id)
    return jsonify(prefs or {
        "slack_webhook_url": None, "notify_batch_complete": 1,
        "notify_taxonomy_change": 1, "notify_new_company": 0,
    })


@settings_bp.route("/api/notification-prefs", methods=["POST"])
def save_notification_prefs():
    data = request.json
    current_app.db.save_notification_prefs(
        project_id=data.get("project_id"),
        slack_webhook_url=data.get("slack_webhook_url"),
        notify_batch_complete=data.get("notify_batch_complete", 1),
        notify_taxonomy_change=data.get("notify_taxonomy_change", 1),
        notify_new_company=data.get("notify_new_company", 0),
    )
    return jsonify({"ok": True})


@settings_bp.route("/api/notification-prefs/test-slack", methods=["POST"])
def test_slack():
    data = request.json
    webhook_url = data.get("slack_webhook_url", "").strip()
    if not webhook_url:
        return jsonify({"error": "No webhook URL provided"}), 400
    if not _is_valid_slack_webhook(webhook_url):
        return jsonify({"error": "Invalid Slack webhook URL. Must be https://hooks.slack.com/services/..."}), 400
    import urllib.request
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps({"text": "Test notification from Research Taxonomy Library"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- SSE Stream ---

@settings_bp.route("/api/events/stream")
def sse_stream():
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return "project_id required", 400

    q = queue.Queue()
    if project_id not in sse_clients:
        sse_clients[project_id] = []
    sse_clients[project_id].append(q)

    def generate():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            if project_id in sse_clients and q in sse_clients[project_id]:
                sse_clients[project_id].remove(q)

    return current_app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
