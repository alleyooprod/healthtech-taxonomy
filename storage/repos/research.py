"""Research CRUD: deep dive and open-ended research sessions."""
import json
from datetime import datetime


class ResearchMixin:

    def create_research(self, project_id, title, scope_type, scope_id=None,
                        prompt="", context=None, model=None):
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO research (project_id, title, scope_type, scope_id,
                   prompt, context, model, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (project_id, title, scope_type, scope_id, prompt,
                 json.dumps(context) if context else None, model),
            )
            return cursor.lastrowid

    def update_research(self, research_id, fields):
        fields["updated_at"] = datetime.now().isoformat()
        safe_fields = {k: v for k, v in fields.items()
                       if k in {"title", "result", "status", "cost_usd",
                                "duration_ms", "updated_at"}}
        if not safe_fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in safe_fields)
        values = list(safe_fields.values()) + [research_id]
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE research SET {set_clause} WHERE id = ?", values
            )

    def get_research(self, research_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM research WHERE id = ?", (research_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_research(self, project_id, limit=50):
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT id, project_id, title, scope_type, scope_id,
                          model, status, created_at, updated_at
                   FROM research WHERE project_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (project_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_research(self, research_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM research WHERE id = ?", (research_id,))
