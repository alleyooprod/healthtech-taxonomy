"""Notes, version history, events, and tags."""
import json
from datetime import datetime


class SocialMixin:

    # --- Notes ---

    def get_notes(self, company_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM company_notes WHERE company_id = ? ORDER BY is_pinned DESC, created_at DESC",
                (company_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_note(self, company_id, content):
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO company_notes (company_id, content) VALUES (?, ?)",
                (company_id, content),
            )
            return cursor.lastrowid

    def update_note(self, note_id, content):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE company_notes SET content = ?, updated_at = ? WHERE id = ?",
                (content, datetime.now().isoformat(), note_id),
            )

    def delete_note(self, note_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM company_notes WHERE id = ?", (note_id,))

    def toggle_pin_note(self, note_id):
        with self._get_conn() as conn:
            row = conn.execute("SELECT is_pinned FROM company_notes WHERE id = ?", (note_id,)).fetchone()
            if not row:
                return None
            new_val = 0 if row["is_pinned"] else 1
            conn.execute("UPDATE company_notes SET is_pinned = ? WHERE id = ?", (new_val, note_id))
            return new_val

    # --- Versions ---

    def save_version(self, company_id, description="Edit"):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
            if not row:
                return
            snapshot = dict(row)
            snapshot.pop("id", None)
            conn.execute(
                "INSERT INTO company_versions (company_id, snapshot, change_description) VALUES (?, ?, ?)",
                (company_id, json.dumps(snapshot, default=str), description),
            )

    def get_versions(self, company_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM company_versions WHERE company_id = ? ORDER BY created_at DESC",
                (company_id,),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["snapshot"] = json.loads(d["snapshot"])
                result.append(d)
            return result

    def restore_version(self, version_id):
        with self._get_conn() as conn:
            ver = conn.execute(
                "SELECT * FROM company_versions WHERE id = ?", (version_id,)
            ).fetchone()
            if not ver:
                return None
            snapshot = json.loads(ver["snapshot"])
            company_id = ver["company_id"]

            self.save_version(company_id, f"Before restore to version {version_id}")

            update_fields = [
                "name", "url", "what", "target", "products", "funding", "geography",
                "tam", "tags", "category_id", "subcategory_id", "confidence_score",
                "employee_range", "founded_year", "funding_stage", "total_funding_usd",
                "hq_city", "hq_country", "linkedin_url", "status",
            ]
            sets = []
            vals = []
            for f in update_fields:
                if f in snapshot:
                    sets.append(f"{f} = ?")
                    vals.append(snapshot[f])
            sets.append("updated_at = ?")
            vals.append(datetime.now().isoformat())
            vals.append(company_id)
            conn.execute(f"UPDATE companies SET {', '.join(sets)} WHERE id = ?", vals)
            return company_id

    # --- Events ---

    def add_event(self, company_id, event_type, description="", event_date=None):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO company_events (company_id, event_type, description, event_date) VALUES (?, ?, ?, ?)",
                (company_id, event_type, description, event_date),
            )

    def get_events(self, company_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM company_events WHERE company_id = ? ORDER BY COALESCE(event_date, created_at) DESC",
                (company_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_event(self, event_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM company_events WHERE id = ?", (event_id,))

    # --- Tags ---

    def get_all_tags(self, project_id=None):
        with self._get_conn() as conn:
            query = "SELECT tags FROM companies WHERE tags IS NOT NULL AND tags != '[]'"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()

        tag_counts = {}
        for row in rows:
            try:
                tags = json.loads(row["tags"])
            except (json.JSONDecodeError, TypeError):
                continue
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return [{"tag": t, "count": c} for t, c in sorted(tag_counts.items(), key=lambda x: -x[1])]

    def rename_tag(self, old_tag, new_tag, project_id=None):
        with self._get_conn() as conn:
            query = "SELECT id, tags FROM companies WHERE tags LIKE ?"
            params = [f'%"{old_tag}"%']
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()

            updated = 0
            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                except (json.JSONDecodeError, TypeError):
                    continue
                if old_tag in tags:
                    tags = [new_tag if t == old_tag else t for t in tags]
                    conn.execute(
                        "UPDATE companies SET tags = ? WHERE id = ?",
                        (json.dumps(tags), row["id"]),
                    )
                    updated += 1
            return updated

    def merge_tags(self, source_tag, target_tag, project_id=None):
        with self._get_conn() as conn:
            query = "SELECT id, tags FROM companies WHERE tags LIKE ?"
            params = [f'%"{source_tag}"%']
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()

            updated = 0
            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                except (json.JSONDecodeError, TypeError):
                    continue
                if source_tag in tags:
                    tags = [target_tag if t == source_tag else t for t in tags]
                    tags = list(dict.fromkeys(tags))
                    conn.execute(
                        "UPDATE companies SET tags = ? WHERE id = ?",
                        (json.dumps(tags), row["id"]),
                    )
                    updated += 1
            return updated

    def delete_tag(self, tag_name, project_id=None):
        with self._get_conn() as conn:
            query = "SELECT id, tags FROM companies WHERE tags LIKE ?"
            params = [f'%"{tag_name}"%']
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()

            updated = 0
            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                except (json.JSONDecodeError, TypeError):
                    continue
                if tag_name in tags:
                    tags = [t for t in tags if t != tag_name]
                    conn.execute(
                        "UPDATE companies SET tags = ? WHERE id = ?",
                        (json.dumps(tags), row["id"]),
                    )
                    updated += 1
            return updated
