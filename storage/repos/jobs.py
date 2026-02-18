"""Jobs, batches, and triage operations."""
import json
from datetime import datetime


class JobsMixin:

    def create_jobs(self, batch_id, urls, project_id=None):
        with self._get_conn() as conn:
            for source_url, resolved_url in urls:
                conn.execute(
                    "INSERT INTO jobs (project_id, batch_id, url, source_url) VALUES (?, ?, ?, ?)",
                    (project_id, batch_id, resolved_url, source_url),
                )

    def get_pending_jobs(self, batch_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE batch_id = ? AND status NOT IN ('done', 'error') ORDER BY id",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_failed_jobs(self, batch_id=None):
        with self._get_conn() as conn:
            if batch_id:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE batch_id = ? AND status = 'error'",
                    (batch_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = 'error'"
                ).fetchall()
            return [dict(r) for r in rows]

    def update_job(self, job_id, status, error_message=None, company_id=None):
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE jobs SET status=?, error_message=?, company_id=?,
                   attempts = attempts + CASE WHEN ? = 'error' THEN 1 ELSE 0 END,
                   updated_at=?
                WHERE id=?""",
                (status, error_message, company_id, status, datetime.now().isoformat(), job_id),
            )

    def get_batch_companies(self, batch_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT co.* FROM companies co
                   JOIN jobs j ON j.company_id = co.id
                   WHERE j.batch_id = ? AND j.status = 'done'""",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_batch_summary(self, batch_id):
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN status NOT IN ('done','error') THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status='error' AND error_message LIKE 'Timeout:%' THEN 1 ELSE 0 END) as timeouts
                FROM jobs WHERE batch_id = ?""",
                (batch_id,),
            ).fetchone()
            return dict(row)

    def get_recent_batches(self, project_id=None, limit=10):
        with self._get_conn() as conn:
            query = """SELECT batch_id, MIN(created_at) as started,
                COUNT(*) as total,
                SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
                SUM(CASE WHEN status='error' AND error_message LIKE 'Timeout:%' THEN 1 ELSE 0 END) as timeouts,
                SUM(CASE WHEN status NOT IN ('done','error') THEN 1 ELSE 0 END) as pending
                FROM jobs"""
            params = []
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            query += " GROUP BY batch_id ORDER BY started DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_batch_details(self, batch_id):
        with self._get_conn() as conn:
            jobs = conn.execute(
                """SELECT j.*, co.name as company_name, co.category_id,
                          c.name as category_name
                   FROM jobs j
                   LEFT JOIN companies co ON j.company_id = co.id
                   LEFT JOIN categories c ON co.category_id = c.id
                   WHERE j.batch_id = ?
                   ORDER BY j.id""",
                (batch_id,),
            ).fetchall()
            triage = conn.execute(
                """SELECT * FROM triage_results WHERE batch_id = ?
                   ORDER BY id""",
                (batch_id,),
            ).fetchall()
            return {
                "jobs": [dict(r) for r in jobs],
                "triage": [dict(r) for r in triage],
            }

    # --- Triage ---

    def save_triage_results(self, batch_id, results, project_id=None):
        with self._get_conn() as conn:
            for r in results:
                conn.execute(
                    """INSERT INTO triage_results
                       (project_id, batch_id, original_url, resolved_url, status, reason,
                        title, meta_description, scraped_text_preview, is_accessible)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        project_id, batch_id,
                        r["original_url"], r["resolved_url"],
                        r["status"], r["reason"],
                        r["title"], r["meta_description"],
                        r["scraped_text_preview"],
                        1 if r["is_accessible"] else 0,
                    ),
                )

    def get_triage_results(self, batch_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM triage_results WHERE batch_id = ? ORDER BY id",
                (batch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_triage_action(self, triage_id, action, replacement_url=None, user_comment=None):
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE triage_results SET user_action = ?, replacement_url = ?,
                   user_comment = ?, updated_at = datetime('now') WHERE id = ?""",
                (action, replacement_url, user_comment, triage_id),
            )

    def get_confirmed_urls(self, batch_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM triage_results WHERE batch_id = ?
                   ORDER BY id""",
                (batch_id,),
            ).fetchall()

        urls = []
        for row in rows:
            r = dict(row)
            if r["user_action"] == "skip":
                continue
            if r["user_action"] == "replace" and r.get("replacement_url"):
                urls.append((r["original_url"], r["replacement_url"]))
            elif r["status"] == "valid" or r["user_action"] == "include":
                urls.append((r["original_url"], r["resolved_url"]))
        return urls
