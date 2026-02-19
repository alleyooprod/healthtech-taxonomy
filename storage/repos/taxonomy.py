"""Categories, category stats, taxonomy changes, taxonomy quality."""
import json
from datetime import datetime


class TaxonomyMixin:

    def get_categories(self, project_id=None, active_only=True):
        with self._get_conn() as conn:
            query = "SELECT * FROM categories WHERE 1=1"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if active_only:
                query += " AND is_active = 1"
            query += " ORDER BY name"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_category_by_name(self, name, project_id=None):
        with self._get_conn() as conn:
            if project_id:
                row = conn.execute(
                    "SELECT * FROM categories WHERE name = ? AND project_id = ? AND is_active = 1",
                    (name, project_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM categories WHERE name = ? AND is_active = 1", (name,)
                ).fetchone()
            return dict(row) if row else None

    def add_category(self, name, parent_id=None, description=None, project_id=None):
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO categories (project_id, name, parent_id, description) VALUES (?, ?, ?, ?)",
                (project_id, name, parent_id, description),
            )
            return cursor.lastrowid

    def merge_categories(self, source_name, target_name, reason="", project_id=None):
        with self._get_conn() as conn:
            q = "SELECT id FROM categories WHERE name = ?"
            params = [source_name]
            if project_id:
                q += " AND project_id = ?"
                params.append(project_id)
            source = conn.execute(q, params).fetchone()

            q2 = "SELECT id FROM categories WHERE name = ?"
            params2 = [target_name]
            if project_id:
                q2 += " AND project_id = ?"
                params2.append(project_id)
            target = conn.execute(q2, params2).fetchone()

            if not source or not target:
                return False
            conn.execute(
                "UPDATE companies SET category_id = ? WHERE category_id = ?",
                (target["id"], source["id"]),
            )
            conn.execute(
                "UPDATE categories SET is_active = 0, merged_into_id = ? WHERE id = ?",
                (target["id"], source["id"]),
            )
            conn.execute(
                "INSERT INTO taxonomy_changes (project_id, change_type, details, reason, affected_category_ids) VALUES (?, ?, ?, ?, ?)",
                (
                    project_id, "merge",
                    json.dumps({"from": source_name, "into": target_name}),
                    reason, json.dumps([source["id"], target["id"]]),
                ),
            )
            return True

    def rename_category(self, old_name, new_name, reason="", project_id=None):
        with self._get_conn() as conn:
            q = "SELECT id FROM categories WHERE name = ?"
            params = [old_name]
            if project_id:
                q += " AND project_id = ?"
                params.append(project_id)
            cat = conn.execute(q, params).fetchone()
            if not cat:
                return False
            conn.execute(
                "UPDATE categories SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, datetime.now().isoformat(), cat["id"]),
            )
            conn.execute(
                "INSERT INTO taxonomy_changes (project_id, change_type, details, reason, affected_category_ids) VALUES (?, ?, ?, ?, ?)",
                (
                    project_id, "rename",
                    json.dumps({"from": old_name, "to": new_name}),
                    reason, json.dumps([cat["id"]]),
                ),
            )
            return True

    def get_category(self, category_id):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
            return dict(row) if row else None

    def update_category_color(self, category_id, color):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE categories SET color = ?, updated_at = ? WHERE id = ?",
                (color, datetime.now().isoformat(), category_id),
            )

    def get_category_stats(self, project_id=None):
        with self._get_conn() as conn:
            query = """
                SELECT c.id, c.name, c.parent_id, c.color,
                       COUNT(DISTINCT co.id) as company_count
                FROM categories c
                LEFT JOIN companies co
                    ON (co.category_id = c.id OR co.subcategory_id = c.id)
                    AND co.is_deleted = 0
                WHERE c.is_active = 1
            """
            params = []
            if project_id:
                query += " AND c.project_id = ?"
                params.append(project_id)
            query += " GROUP BY c.id ORDER BY c.name"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # --- Taxonomy Changes ---

    def log_taxonomy_change(self, change_type, details, reason="", affected_ids=None, project_id=None):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO taxonomy_changes (project_id, change_type, details, reason, affected_category_ids) VALUES (?, ?, ?, ?, ?)",
                (project_id, change_type, json.dumps(details), reason, json.dumps(affected_ids or [])),
            )

    def get_taxonomy_history(self, project_id=None, limit=50):
        with self._get_conn() as conn:
            query = "SELECT * FROM taxonomy_changes"
            params = []
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # --- Taxonomy Quality ---

    def get_taxonomy_quality(self, project_id):
        with self._get_conn() as conn:
            categories = conn.execute("""
                SELECT c.id, c.name, c.parent_id,
                       COUNT(co.id) as company_count,
                       AVG(co.confidence_score) as avg_confidence
                FROM categories c
                LEFT JOIN companies co ON co.category_id = c.id AND co.is_deleted = 0
                WHERE c.project_id = ? AND c.is_active = 1
                GROUP BY c.id
            """, (project_id,)).fetchall()

            empty = []
            overcrowded = []
            low_confidence = []
            total_companies = 0
            total_confidence = 0
            confidence_count = 0

            for cat in categories:
                c = dict(cat)
                if not c["parent_id"]:
                    if c["company_count"] == 0:
                        empty.append(c)
                    elif c["company_count"] > 15:
                        overcrowded.append(c)
                total_companies += c["company_count"]
                if c["avg_confidence"] is not None:
                    if c["avg_confidence"] < 0.5:
                        low_confidence.append(c)
                    total_confidence += c["avg_confidence"] * c["company_count"]
                    confidence_count += c["company_count"]

            avg_confidence = (total_confidence / confidence_count) if confidence_count > 0 else None

            return {
                "empty_categories": [{"id": c["id"], "name": c["name"]} for c in empty],
                "overcrowded_categories": [{"id": c["id"], "name": c["name"], "count": c["company_count"]} for c in overcrowded],
                "low_confidence_categories": [{"id": c["id"], "name": c["name"], "avg_confidence": round(c["avg_confidence"], 2)} for c in low_confidence],
                "avg_confidence": round(avg_confidence, 2) if avg_confidence else None,
                "total_companies": total_companies,
                "total_categories": len([c for c in categories if not dict(c).get("parent_id")]),
            }
