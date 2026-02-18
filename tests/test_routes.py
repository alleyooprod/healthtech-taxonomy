"""Tests for Flask API routes."""
import json


class TestIndexRoute:
    def test_index_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Research Taxonomy Library" in r.data


class TestProjectsAPI:
    def test_create_and_list_projects(self, client):
        # Get CSRF token
        r = client.get("/")
        csrf = client.get("/api/projects").headers.get("X-CSRF-Token", "")

        r = client.post("/api/projects", json={
            "name": "Test Project",
            "purpose": "Testing routes",
            "seed_categories": "Cat 1\nCat 2",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert "id" in data

        r = client.get("/api/projects")
        assert r.status_code == 200
        projects = r.get_json()
        assert any(p["name"] == "Test Project" for p in projects)


class TestTaxonomyAPI:
    def test_get_taxonomy(self, client):
        # Create a project first
        client.post("/api/projects", json={
            "name": "Tax Test",
            "seed_categories": "A\nB",
        })
        r = client.get("/api/taxonomy?project_id=1")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)


class TestStaticFiles:
    def test_styles_css(self, client):
        r = client.get("/static/styles.css")
        assert r.status_code == 200
        assert b"@import" in r.data

    def test_base_css(self, client):
        r = client.get("/static/base.css")
        assert r.status_code == 200
        assert b":root" in r.data

    def test_core_js(self, client):
        r = client.get("/static/js/core.js")
        assert r.status_code == 200


class TestExportEndpoints:
    def test_export_json(self, client):
        client.post("/api/projects", json={
            "name": "Export Test",
            "seed_categories": "X",
        })
        r = client.get("/api/export/json?project_id=1")
        assert r.status_code == 200

    def test_export_csv(self, client):
        client.post("/api/projects", json={
            "name": "CSV Test",
            "seed_categories": "X",
        })
        r = client.get("/api/export/csv?project_id=1")
        assert r.status_code == 200


class TestJobsAPI:
    def test_list_jobs_empty(self, client):
        r = client.get("/api/jobs")
        assert r.status_code == 200
        assert r.get_json() == []
