"""FeaturesMixin — DB operations for canonical feature vocabulary.

Manages canonical features (standard names per project/attribute) and
feature mappings (raw extracted values → canonical names).
"""
import json


class FeaturesMixin:
    """Database methods for canonical features and mappings."""

    # ── Canonical Features ────────────────────────────────────

    def create_canonical_feature(self, project_id, attr_slug, canonical_name,
                                  description=None, category=None):
        """Create a canonical feature entry.

        Returns: feature_id (int) or None if duplicate.
        """
        with self._get_conn() as conn:
            try:
                cursor = conn.execute(
                    """INSERT INTO canonical_features
                       (project_id, attr_slug, canonical_name, description, category)
                       VALUES (?, ?, ?, ?, ?)""",
                    (project_id, attr_slug, canonical_name, description, category),
                )
                return cursor.lastrowid
            except Exception:
                # UNIQUE constraint violation — duplicate
                return None

    def get_canonical_feature(self, feature_id):
        """Get a single canonical feature by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM canonical_features WHERE id = ?", (feature_id,)
            ).fetchone()
            if not row:
                return None
            feature = dict(row)
            # Include mappings
            mappings = conn.execute(
                "SELECT * FROM feature_mappings WHERE canonical_feature_id = ?",
                (feature_id,),
            ).fetchall()
            feature["mappings"] = [dict(m) for m in mappings]
            return feature

    def get_canonical_features(self, project_id, attr_slug=None, category=None,
                                search=None):
        """List canonical features for a project.

        Returns: list[dict] with mapping counts.
        """
        clauses = ["cf.project_id = ?"]
        params = [project_id]

        if attr_slug:
            clauses.append("cf.attr_slug = ?")
            params.append(attr_slug)
        if category:
            clauses.append("cf.category = ?")
            params.append(category)
        if search:
            clauses.append("cf.canonical_name LIKE ?")
            params.append(f"%{search}%")

        where = " AND ".join(clauses)

        with self._get_conn() as conn:
            rows = conn.execute(
                f"""SELECT cf.*,
                           (SELECT COUNT(*) FROM feature_mappings fm
                            WHERE fm.canonical_feature_id = cf.id) as mapping_count
                    FROM canonical_features cf
                    WHERE {where}
                    ORDER BY cf.attr_slug, cf.canonical_name""",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def update_canonical_feature(self, feature_id, **fields):
        """Update a canonical feature."""
        allowed = {"canonical_name", "description", "category"}
        safe = {k: v for k, v in fields.items() if k in allowed}
        if not safe:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in safe)
        values = list(safe.values()) + [feature_id]
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE canonical_features SET {set_clause} WHERE id = ?",
                values,
            )
            return True

    def delete_canonical_feature(self, feature_id):
        """Delete a canonical feature and all its mappings (CASCADE)."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM canonical_features WHERE id = ?", (feature_id,)
            )

    def merge_canonical_features(self, target_id, source_ids):
        """Merge source features into target — moves all mappings to target.

        Returns: count of moved mappings.
        """
        if not source_ids:
            return 0

        with self._get_conn() as conn:
            count = 0
            for sid in source_ids:
                if sid == target_id:
                    continue
                # Move mappings (skip duplicates)
                mappings = conn.execute(
                    "SELECT raw_value FROM feature_mappings WHERE canonical_feature_id = ?",
                    (sid,),
                ).fetchall()
                for m in mappings:
                    try:
                        conn.execute(
                            """INSERT INTO feature_mappings
                               (canonical_feature_id, raw_value)
                               VALUES (?, ?)""",
                            (target_id, m["raw_value"]),
                        )
                        count += 1
                    except Exception:
                        # Duplicate mapping in target — skip
                        pass
                # Delete source feature (cascades mappings)
                conn.execute(
                    "DELETE FROM canonical_features WHERE id = ?", (sid,)
                )
            return count

    def get_canonical_categories(self, project_id, attr_slug=None):
        """Get distinct categories for canonical features in a project."""
        clauses = ["project_id = ?"]
        params = [project_id]
        if attr_slug:
            clauses.append("attr_slug = ?")
            params.append(attr_slug)
        where = " AND ".join(clauses)

        with self._get_conn() as conn:
            rows = conn.execute(
                f"""SELECT DISTINCT category FROM canonical_features
                    WHERE {where} AND category IS NOT NULL
                    ORDER BY category""",
                params,
            ).fetchall()
            return [r["category"] for r in rows]

    # ── Feature Mappings ──────────────────────────────────────

    def add_feature_mapping(self, canonical_feature_id, raw_value):
        """Add a raw value → canonical feature mapping.

        Returns: mapping_id (int) or None if duplicate.
        """
        with self._get_conn() as conn:
            try:
                cursor = conn.execute(
                    """INSERT INTO feature_mappings
                       (canonical_feature_id, raw_value)
                       VALUES (?, ?)""",
                    (canonical_feature_id, raw_value),
                )
                return cursor.lastrowid
            except Exception:
                return None

    def remove_feature_mapping(self, mapping_id):
        """Remove a feature mapping by ID."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM feature_mappings WHERE id = ?", (mapping_id,)
            )

    def get_feature_mappings(self, canonical_feature_id):
        """Get all raw value mappings for a canonical feature."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM feature_mappings WHERE canonical_feature_id = ?",
                (canonical_feature_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def resolve_raw_value(self, project_id, attr_slug, raw_value):
        """Find the canonical feature for a raw extracted value.

        Tries exact match first, then case-insensitive.
        Returns: canonical feature dict or None.
        """
        with self._get_conn() as conn:
            # Exact match
            row = conn.execute(
                """SELECT cf.* FROM canonical_features cf
                   JOIN feature_mappings fm ON fm.canonical_feature_id = cf.id
                   WHERE cf.project_id = ? AND cf.attr_slug = ?
                         AND fm.raw_value = ?""",
                (project_id, attr_slug, raw_value),
            ).fetchone()
            if row:
                return dict(row)

            # Case-insensitive fallback
            row = conn.execute(
                """SELECT cf.* FROM canonical_features cf
                   JOIN feature_mappings fm ON fm.canonical_feature_id = cf.id
                   WHERE cf.project_id = ? AND cf.attr_slug = ?
                         AND LOWER(fm.raw_value) = LOWER(?)""",
                (project_id, attr_slug, raw_value),
            ).fetchone()
            if row:
                return dict(row)

            # Check if the raw_value matches a canonical_name directly
            row = conn.execute(
                """SELECT * FROM canonical_features
                   WHERE project_id = ? AND attr_slug = ?
                         AND LOWER(canonical_name) = LOWER(?)""",
                (project_id, attr_slug, raw_value),
            ).fetchone()
            return dict(row) if row else None

    def get_unmapped_values(self, project_id, attr_slug):
        """Find extracted values that don't map to any canonical feature.

        Looks at accepted extraction results for the given attribute and finds
        values without a mapping.

        Returns: list of distinct unmapped values.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT DISTINCT ea.value
                   FROM entity_attributes ea
                   JOIN entities e ON e.id = ea.entity_id
                   WHERE e.project_id = ? AND ea.attr_slug = ?
                         AND ea.value IS NOT NULL AND ea.value != ''
                   ORDER BY ea.value""",
                (project_id, attr_slug),
            ).fetchall()

            # Filter out values that already have mappings
            mapped_values = set()
            all_mappings = conn.execute(
                """SELECT LOWER(fm.raw_value) as lv
                   FROM feature_mappings fm
                   JOIN canonical_features cf ON cf.id = fm.canonical_feature_id
                   WHERE cf.project_id = ? AND cf.attr_slug = ?""",
                (project_id, attr_slug),
            ).fetchall()
            for m in all_mappings:
                mapped_values.add(m["lv"])

            # Also include canonical names as mapped
            canonical_names = conn.execute(
                """SELECT LOWER(canonical_name) as ln
                   FROM canonical_features
                   WHERE project_id = ? AND attr_slug = ?""",
                (project_id, attr_slug),
            ).fetchall()
            for c in canonical_names:
                mapped_values.add(c["ln"])

            unmapped = []
            for r in rows:
                val = r["value"]
                if val and val.strip().lower() not in mapped_values:
                    unmapped.append(val)

            return unmapped

    def get_feature_vocabulary_stats(self, project_id):
        """Get vocabulary statistics for a project.

        Returns: dict with counts per attr_slug.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT attr_slug,
                          COUNT(*) as feature_count,
                          (SELECT COUNT(*) FROM feature_mappings fm
                           JOIN canonical_features cf2 ON cf2.id = fm.canonical_feature_id
                           WHERE cf2.project_id = cf.project_id AND cf2.attr_slug = cf.attr_slug
                          ) as mapping_count
                   FROM canonical_features cf
                   WHERE cf.project_id = ?
                   GROUP BY cf.attr_slug""",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
