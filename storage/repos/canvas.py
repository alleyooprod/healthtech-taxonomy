"""Canvas CRUD: visual workspaces for arranging companies and notes."""
import json
from datetime import datetime


class CanvasMixin:

    def create_canvas(self, project_id, title="Untitled Canvas"):
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO canvases (project_id, title) VALUES (?, ?)",
                (project_id, title),
            )
            return cursor.lastrowid

    def get_canvas(self, canvas_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM canvases WHERE id = ?", (canvas_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            # Parse JSON data field
            try:
                d["data"] = json.loads(d["data"]) if d["data"] else {}
            except (json.JSONDecodeError, TypeError):
                d["data"] = {}
            return d

    def update_canvas(self, canvas_id, fields):
        fields["updated_at"] = datetime.now().isoformat()
        safe = {}
        for k, v in fields.items():
            if k in {"title", "data", "updated_at"}:
                safe[k] = json.dumps(v) if k == "data" and isinstance(v, dict) else v
        if not safe:
            return
        set_clause = ", ".join(f"{k} = ?" for k in safe)
        values = list(safe.values()) + [canvas_id]
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE canvases SET {set_clause} WHERE id = ?", values
            )

    def list_canvases(self, project_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT id, project_id, title, created_at, updated_at
                   FROM canvases WHERE project_id = ?
                   ORDER BY updated_at DESC""",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_canvas(self, canvas_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM canvases WHERE id = ?", (canvas_id,))
