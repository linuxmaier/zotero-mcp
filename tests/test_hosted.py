"""Tests for read-only and hosted tool hiding, and the health route (hosted.py).

The classification test is the important one for this fork: it fails when an
upstream merge adds a tool that isn't listed as read or write, so a new write
tool can't reach a read-only deployment unreviewed.
"""

from __future__ import annotations

import asyncio

import pytest

from zotero_mcp.hosted import (
    HOSTED_ENV_VAR,
    HOSTED_HIDDEN_TOOLS,
    READ_ONLY_ENV_VAR,
    READ_TOOLS,
    WRITE_TOOLS,
    hidden_tool_names,
    hosted_config_errors,
    unclassified_tools,
)
from zotero_mcp.toolsets import apply_toolsets


@pytest.fixture
def mcp(monkeypatch):
    from zotero_mcp.server import mcp

    monkeypatch.delenv(READ_ONLY_ENV_VAR, raising=False)
    monkeypatch.delenv(HOSTED_ENV_VAR, raising=False)
    yield mcp
    monkeypatch.delenv(READ_ONLY_ENV_VAR, raising=False)
    monkeypatch.delenv(HOSTED_ENV_VAR, raising=False)
    apply_toolsets(mcp, raw="all", transport="streamable-http")


def _listed(mcp) -> set[str]:
    return {t.name for t in asyncio.run(mcp.list_tools())}


class TestClassification:
    def test_every_registered_tool_is_read_or_write(self, mcp):
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        bad = unclassified_tools(_listed(mcp))
        assert not bad, (
            f"Tools not classified (or classified twice) in hosted.py: {bad}. "
            "Add each to READ_TOOLS or WRITE_TOOLS."
        )

    def test_no_stale_names(self, mcp):
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        stale = (READ_TOOLS | WRITE_TOOLS | HOSTED_HIDDEN_TOOLS) - _listed(mcp)
        assert not stale, f"hosted.py names tools that aren't registered: {sorted(stale)}"


class TestHiding:
    @pytest.mark.parametrize("value", ["true", "1", "YES"])
    def test_flags_accept_truthy_values(self, monkeypatch, value):
        monkeypatch.setenv(READ_ONLY_ENV_VAR, value)
        monkeypatch.setenv(HOSTED_ENV_VAR, value)
        assert hidden_tool_names() >= set(WRITE_TOOLS | HOSTED_HIDDEN_TOOLS)

    def test_hosted_hides_pdf_page_tool_without_pymupdf(self, monkeypatch):
        import zotero_mcp.hosted as hosted

        monkeypatch.setenv(HOSTED_ENV_VAR, "true")
        monkeypatch.setattr(hosted, "_pdf_extra_installed", lambda: False)
        assert "zotero_read_pdf_pages" in hidden_tool_names()
        monkeypatch.setattr(hosted, "_pdf_extra_installed", lambda: True)
        assert "zotero_read_pdf_pages" not in hidden_tool_names()

    def test_nothing_hidden_by_default(self, monkeypatch):
        monkeypatch.delenv(READ_ONLY_ENV_VAR, raising=False)
        monkeypatch.delenv(HOSTED_ENV_VAR, raising=False)
        assert hidden_tool_names() == set()

    def test_read_only_hides_write_tools_even_from_all(self, mcp, monkeypatch):
        monkeypatch.setenv(READ_ONLY_ENV_VAR, "true")
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        listed = _listed(mcp)
        assert not (listed & WRITE_TOOLS)
        assert "zotero_search_items" in listed

    def test_hosted_hides_local_and_library_tools(self, mcp, monkeypatch):
        monkeypatch.setenv(HOSTED_ENV_VAR, "true")
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        assert not (_listed(mcp) & HOSTED_HIDDEN_TOOLS)

    def test_hiding_is_reversible(self, mcp, monkeypatch):
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        full = _listed(mcp)

        monkeypatch.setenv(READ_ONLY_ENV_VAR, "true")
        monkeypatch.setenv(HOSTED_ENV_VAR, "true")
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        assert _listed(mcp) < full

        monkeypatch.delenv(READ_ONLY_ENV_VAR)
        monkeypatch.delenv(HOSTED_ENV_VAR)
        apply_toolsets(mcp, raw="all", transport="streamable-http")
        assert _listed(mcp) == full


def test_health_route_answers_without_zotero(mcp):
    from starlette.testclient import TestClient

    with TestClient(mcp.http_app()) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"


class TestHostedConfig:
    def test_not_hosted_needs_nothing(self, monkeypatch):
        monkeypatch.delenv(HOSTED_ENV_VAR, raising=False)
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        assert hosted_config_errors() == []

    def test_hosted_needs_web_api_credentials(self, monkeypatch):
        monkeypatch.setenv(HOSTED_ENV_VAR, "true")
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
        monkeypatch.setenv("ZOTERO_LOCAL", "true")
        errors = hosted_config_errors()
        assert len(errors) == 3

    def test_hosted_ready(self, monkeypatch):
        monkeypatch.setenv(HOSTED_ENV_VAR, "true")
        monkeypatch.setenv("ZOTERO_API_KEY", "k")
        monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123")
        monkeypatch.delenv("ZOTERO_LOCAL", raising=False)
        assert hosted_config_errors() == []
