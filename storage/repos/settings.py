"""Share tokens, saved views, map layouts, distinct values, activity, notifications, reports, stats."""
import json
from datetime import datetime


class SettingsMixin:

    # --- Share Tokens ---

    def create_share_token(self, project_id, label="Shared link", expires_at=None):
        import secrets
        token = secrets.token_urlsafe(32)
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO share_tokens (project_id, token, label, expires_at) VALUES (?, ?, ?, ?)",
                (project_id, token, label, expires_at),
            )
        return token

    def get_share_tokens(self, project_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM share_tokens WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def validate_share_token(self, token):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM share_tokens WHERE token = ? AND is_active = 1",
                (token,),
            ).fetchone()
            if not row:
                return None
            r = dict(row)
            if r.get("expires_at"):
                if datetime.fromisoformat(r["expires_at"]) < datetime.now():
                    return None
            return r

    def revoke_share_token(self, token_id):
        with self._get_conn() as conn:
            conn.execute("UPDATE share_tokens SET is_active = 0 WHERE id = ?", (token_id,))

    # --- Saved Views ---

    def get_saved_views(self, project_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM saved_views WHERE project_id = ? ORDER BY name",
                (project_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["filters"] = json.loads(d["filters"])
                result.append(d)
            return result

    def save_view(self, project_id, name, filters):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO saved_views (project_id, name, filters)
                   VALUES (?, ?, ?)""",
                (project_id, name, json.dumps(filters)),
            )

    def delete_saved_view(self, view_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM saved_views WHERE id = ?", (view_id,))

    # --- Map Layouts ---

    def get_map_layouts(self, project_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM map_layouts WHERE project_id = ? ORDER BY name",
                (project_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["layout_data"] = json.loads(d["layout_data"])
                result.append(d)
            return result

    def save_map_layout(self, project_id, name, layout_data):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO map_layouts (project_id, name, layout_data, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (project_id, name, json.dumps(layout_data), datetime.now().isoformat()),
            )

    # --- Distinct Values ---

    def get_distinct_geographies(self, project_id=None):
        with self._get_conn() as conn:
            query = "SELECT DISTINCT geography FROM companies WHERE geography IS NOT NULL AND geography != ''"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            query += " ORDER BY geography"
            rows = conn.execute(query, params).fetchall()
            return [r["geography"] for r in rows]

    def get_distinct_funding_stages(self, project_id=None):
        with self._get_conn() as conn:
            query = "SELECT DISTINCT funding_stage FROM companies WHERE funding_stage IS NOT NULL AND funding_stage != ''"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            query += " ORDER BY funding_stage"
            rows = conn.execute(query, params).fetchall()
            return [r["funding_stage"] for r in rows]

    # --- Activity Log ---

    def log_activity(self, project_id, action, description="", entity_type=None, entity_id=None):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO activity_log (project_id, action, description, entity_type, entity_id)
                VALUES (?, ?, ?, ?, ?)""",
                (project_id, action, description, entity_type, entity_id),
            )

    def get_activity(self, project_id, limit=50, offset=0):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM activity_log WHERE project_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (project_id, limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Notification Prefs ---

    def get_notification_prefs(self, project_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM notification_prefs WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            return dict(row) if row else None

    def save_notification_prefs(self, project_id, slack_webhook_url=None,
                                notify_batch_complete=1, notify_taxonomy_change=1,
                                notify_new_company=0):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO notification_prefs (project_id, slack_webhook_url,
                   notify_batch_complete, notify_taxonomy_change, notify_new_company)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                   slack_webhook_url = excluded.slack_webhook_url,
                   notify_batch_complete = excluded.notify_batch_complete,
                   notify_taxonomy_change = excluded.notify_taxonomy_change,
                   notify_new_company = excluded.notify_new_company,
                   updated_at = datetime('now')""",
                (project_id, slack_webhook_url, notify_batch_complete,
                 notify_taxonomy_change, notify_new_company),
            )

    # --- Reports ---

    def save_report(self, project_id, report_id, category_name, company_count,
                    model, markdown_content, status="complete", error_message=None):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO reports
                   (project_id, report_id, category_name, company_count, model,
                    markdown_content, status, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (project_id, report_id, category_name, company_count,
                 model, markdown_content, status, error_message),
            )

    def get_reports(self, project_id=None):
        with self._get_conn() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM reports WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM reports ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_report(self, report_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM reports WHERE report_id = ?", (report_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_report(self, report_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))

    # --- Stats ---

    def get_stats(self, project_id=None):
        with self._get_conn() as conn:
            if project_id:
                companies = conn.execute(
                    "SELECT COUNT(*) FROM companies WHERE project_id = ? AND is_deleted = 0", (project_id,)
                ).fetchone()[0]
                categories = conn.execute(
                    "SELECT COUNT(*) FROM categories WHERE is_active = 1 AND parent_id IS NULL AND project_id = ?",
                    (project_id,),
                ).fetchone()[0]
                latest = conn.execute(
                    "SELECT MAX(processed_at) FROM companies WHERE project_id = ?",
                    (project_id,),
                ).fetchone()[0]
            else:
                companies = conn.execute(
                    "SELECT COUNT(*) FROM companies WHERE is_deleted = 0"
                ).fetchone()[0]
                categories = conn.execute(
                    "SELECT COUNT(*) FROM categories WHERE is_active = 1 AND parent_id IS NULL"
                ).fetchone()[0]
                latest = conn.execute(
                    "SELECT MAX(processed_at) FROM companies"
                ).fetchone()[0]
            return {
                "total_companies": companies,
                "total_categories": categories,
                "last_updated": latest,
            }
