"""Research templates: reusable prompt templates with variable substitution."""

DEFAULT_TEMPLATES = [
    {
        "name": "Competitive Landscape",
        "prompt_template": "Map the competitive landscape for {scope}. Identify key players, their positioning, market share estimates, strengths and weaknesses, and recent strategic moves.",
        "scope_type": "project",
    },
    {
        "name": "Pricing Analysis",
        "prompt_template": "Analyze pricing strategies across {scope}. Compare pricing models, tiers, average contract values, and how pricing relates to market positioning.",
        "scope_type": "project",
    },
    {
        "name": "Market Trends",
        "prompt_template": "Research current market trends affecting {scope}. Include emerging technologies, regulatory changes, investment patterns, and growth projections for the next 3-5 years.",
        "scope_type": "project",
    },
    {
        "name": "Product Reviews & Sentiment",
        "prompt_template": "Research product reviews and user sentiment for {scope}. Analyze customer feedback from G2, Capterra, app stores, and social media. Identify common praises and complaints.",
        "scope_type": "project",
    },
    {
        "name": "Customer Journey",
        "prompt_template": "Analyze the customer journey for {scope}. Map how customers discover, evaluate, purchase, and use products in this space. Identify pain points and opportunities.",
        "scope_type": "project",
    },
]


class TemplateMixin:

    def seed_default_templates(self, project_id):
        """Seed default research templates for a new project."""
        with self._get_conn() as conn:
            for t in DEFAULT_TEMPLATES:
                conn.execute(
                    """INSERT OR IGNORE INTO research_templates
                       (project_id, name, prompt_template, scope_type, is_default)
                       VALUES (?, ?, ?, ?, 1)""",
                    (project_id, t["name"], t["prompt_template"], t["scope_type"]),
                )

    def get_research_templates(self, project_id):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM research_templates WHERE project_id = ? ORDER BY is_default DESC, name",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def create_research_template(self, project_id, name, prompt_template, scope_type="project"):
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO research_templates (project_id, name, prompt_template, scope_type)
                   VALUES (?, ?, ?, ?)""",
                (project_id, name, prompt_template, scope_type),
            )
            return cursor.lastrowid

    def update_research_template(self, template_id, name, prompt_template, scope_type=None):
        with self._get_conn() as conn:
            if scope_type:
                conn.execute(
                    "UPDATE research_templates SET name = ?, prompt_template = ?, scope_type = ? WHERE id = ?",
                    (name, prompt_template, scope_type, template_id),
                )
            else:
                conn.execute(
                    "UPDATE research_templates SET name = ?, prompt_template = ? WHERE id = ?",
                    (name, prompt_template, template_id),
                )

    def delete_research_template(self, template_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM research_templates WHERE id = ?", (template_id,))
