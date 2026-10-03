"""Web API full-text search returns parent items, and recent items skip attachments.

Over the Web API a full-text match is reported on the attachment holding the
text, and the default ``itemType=-attachment`` filter drops it, so a paper
that mentions the query only in its body went missing (found against a real
library: 1 result where Zotero had 16 matches).
"""

from __future__ import annotations

from zotero_mcp.library import ApiBackend
from zotero_mcp.tools.search import _add_fulltext_parents


def _item(key, *, parent=None, collections=(), deleted=False, item_type="journalArticle"):
    data = {"key": key, "itemType": item_type, "title": key, "collections": list(collections)}
    if parent:
        data["parentItem"] = parent
    if deleted:
        data["deleted"] = 1
    return {"key": key, "data": data}


class _Zot:
    def __init__(self, attachments):
        self.attachments = attachments
        self.calls = []

    def items(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("itemType") == "attachment" and kwargs.get("start", 0) == 0:
            return list(self.attachments)
        return []


class _Backend:
    def __init__(self, parents):
        self.parents = {p["key"]: p for p in parents}

    def get_items(self, keys):
        return {k: self.parents[k] for k in keys if k in self.parents}


def test_adds_parents_after_metadata_matches_without_duplicates():
    zot = _Zot([
        _item("ATT00001", parent="PAPER001", item_type="attachment"),
        _item("ATT00002", parent="PAPER002", item_type="attachment"),
        _item("ATT00003", parent="PAPER002", item_type="attachment"),
        _item("ATT00004", parent="META0001", item_type="attachment"),
        _item("STANDALN", item_type="attachment"),
    ])
    backend = _Backend([_item("PAPER001"), _item("PAPER002"), _item("META0001")])

    out = _add_fulltext_parents(zot, backend, [_item("META0001")], "q", 10)

    assert [i["key"] for i in out] == ["META0001", "PAPER001", "PAPER002"]
    assert zot.calls[0]["qmode"] == "everything"
    assert zot.calls[0]["itemType"] == "attachment"


def test_respects_limit_and_skips_trashed_parents():
    zot = _Zot([_item(f"ATT0000{n}", parent=f"PAPER00{n}", item_type="attachment") for n in range(1, 5)])
    backend = _Backend([_item("PAPER001", deleted=True), _item("PAPER002"), _item("PAPER003"), _item("PAPER004")])

    out = _add_fulltext_parents(zot, backend, [], "q", 2)

    assert [i["key"] for i in out] == ["PAPER002", "PAPER003"]


def test_collection_scope_keeps_only_member_parents():
    zot = _Zot([
        _item("ATT00001", parent="PAPER001", item_type="attachment"),
        _item("ATT00002", parent="PAPER002", item_type="attachment"),
    ])
    backend = _Backend([_item("PAPER001", collections=["COLL0001"]), _item("PAPER002", collections=["OTHER001"])])

    out = _add_fulltext_parents(zot, backend, [], "q", 10, ["COLL0001"])

    assert [i["key"] for i in out] == ["PAPER001"]


def test_full_results_and_api_errors_leave_items_unchanged():
    full = [_item("META0001")]
    assert _add_fulltext_parents(_Zot([]), _Backend([]), full, "q", 1) == full

    class _Broken:
        def items(self, **kwargs):
            raise RuntimeError("429")

    assert _add_fulltext_parents(_Broken(), _Backend([]), [], "q", 5) == []


def test_api_recent_items_exclude_attachments():
    zot = _Zot([])
    ApiBackend(zot).recent_items(limit=5)
    assert zot.calls[0]["itemType"] == "-attachment"
    assert zot.calls[0]["sort"] == "dateAdded"
