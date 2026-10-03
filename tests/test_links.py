"""Tests for web-library links: zotero_get_links and the link line in results."""

from __future__ import annotations

from conftest import DummyContext

from zotero_mcp.client import format_item_metadata
from zotero_mcp.tools import links
from zotero_mcp.utils import format_item_result, web_library_url

WEB = "https://www.zotero.org/hanna"

PARENT = {
    "key": "ABCD1234",
    "links": {"alternate": {"href": f"{WEB}/items/ABCD1234", "type": "text/html"}},
    "data": {
        "key": "ABCD1234",
        "itemType": "journalArticle",
        "title": "Sleep and screens",
        "DOI": "https://doi.org/10.1000/xyz123",
        "creators": [],
    },
}
PDF = {
    "key": "PDFK5678",
    "links": {"alternate": {"href": f"{WEB}/items/PDFK5678", "type": "text/html"}},
    "data": {
        "key": "PDFK5678",
        "itemType": "attachment",
        "title": "Full Text PDF",
        "contentType": "application/pdf",
        "linkMode": "imported_url",
        "parentItem": "ABCD1234",
    },
}
LINKED_URL = {
    "key": "URLK0001",
    "data": {
        "key": "URLK0001",
        "itemType": "attachment",
        "title": "Publisher page",
        "contentType": "text/html",
        "linkMode": "linked_url",
        "url": "https://example.org/paper",
    },
}


class _Backend:
    def __init__(self, items, children):
        self._items = items
        self._children = children

    def get_item(self, key):
        return self._items.get(key)

    def get_children(self, keys, *, item_type=None):
        return {k: self._children[k] for k in keys if k in self._children}


def _use(monkeypatch, items, children=None):
    backend = _Backend(items, children or {})
    monkeypatch.setattr(links._library, "get_library_backend", lambda: backend)


def test_item_with_pdf_lists_web_doi_and_desktop_links(monkeypatch):
    _use(monkeypatch, {"ABCD1234": PARENT}, {"ABCD1234": [PDF, LINKED_URL]})

    out = links.get_links("abcd1234", ctx=DummyContext())

    assert f"{WEB}/items/ABCD1234" in out
    assert "https://doi.org/10.1000/xyz123" in out
    assert "zotero://select/library/items/ABCD1234" in out
    assert f"{WEB}/items/PDFK5678" in out
    assert "zotero://open-pdf/library/items/PDFK5678" in out
    assert "https://example.org/paper" in out


def test_attachment_key_returns_its_own_links(monkeypatch):
    _use(monkeypatch, {"PDFK5678": PDF})

    out = links.get_links("PDFK5678", ctx=DummyContext())

    assert f"{WEB}/items/PDFK5678" in out
    assert "zotero://open-pdf/library/items/PDFK5678" in out


def test_item_without_attachments(monkeypatch):
    _use(monkeypatch, {"ABCD1234": PARENT}, {"ABCD1234": []})
    assert "Attachments: none." in links.get_links("ABCD1234", ctx=DummyContext())


def test_unknown_and_malformed_keys(monkeypatch):
    _use(monkeypatch, {})
    assert "No item found" in links.get_links("ZZZZ9999", ctx=DummyContext())
    assert links.get_links("not a key", ctx=DummyContext()).startswith("Error:")


def test_web_url_only_from_web_api_links():
    assert web_library_url(PARENT) == f"{WEB}/items/ABCD1234"
    assert web_library_url({"data": {}}) is None
    local = {"links": {"alternate": {"href": "https://www.zotero.org/users/local/abc/items/X"}}}
    assert web_library_url(local) is None


def test_search_results_and_metadata_show_the_link():
    assert f"**Zotero link:** {WEB}/items/ABCD1234" in format_item_result(PARENT)
    assert f"**Zotero link:** {WEB}/items/ABCD1234" in format_item_metadata(PARENT)
    assert not any("Zotero link" in line for line in format_item_result(LINKED_URL))
