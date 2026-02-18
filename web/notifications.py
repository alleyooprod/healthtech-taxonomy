"""SSE (Server-Sent Events) infrastructure and Slack webhook notifications."""
import json
import queue


sse_clients = {}  # project_id -> list of queues


def notify_sse(project_id, event_type, data):
    """Push an event to all SSE clients for a project."""
    if project_id in sse_clients:
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        dead = []
        for q in sse_clients[project_id]:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            try:
                sse_clients[project_id].remove(q)
            except ValueError:
                pass
        if not sse_clients[project_id]:
            del sse_clients[project_id]


def _is_valid_slack_webhook(url):
    """Validate that a URL is a legitimate Slack webhook to prevent SSRF."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == "hooks.slack.com"
            and parsed.path.startswith("/services/")
        )
    except Exception:
        return False


def send_slack(project_id, message):
    """Send a Slack webhook notification if configured."""
    from flask import current_app
    try:
        db = current_app.db
        prefs = db.get_notification_prefs(project_id)
        webhook_url = prefs.get("slack_webhook_url") if prefs else None
        if webhook_url and _is_valid_slack_webhook(webhook_url):
            import urllib.request
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps({"text": message}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
