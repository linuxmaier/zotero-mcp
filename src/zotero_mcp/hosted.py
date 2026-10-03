"""Tool filtering and health check for running as a hosted server.

This fork runs the server as a remote MCP connector for one personal library,
reached only through the Zotero Web API (see AGENTS.md). Two environment
variables shape the tool surface for that, on top of ``ZOTERO_MCP_TOOLSETS``:

==========================  =================================================
Variable                    Effect
==========================  =================================================
``ZOTERO_MCP_READ_ONLY``    Hide every tool in :data:`WRITE_TOOLS`.
``ZOTERO_MCP_HOSTED``       Hide tools that need desktop Zotero, switch the
                            process-wide active library, or manage the
                            semantic index (:data:`HOSTED_HIDDEN_TOOLS`).
==========================  =================================================

Both accept "true", "yes", or "1". Hiding is applied last by
:func:`zotero_mcp.toolsets.apply_toolsets`, so an optional toolset can't bring
a hidden tool back.

Every registered tool must appear in exactly one of :data:`READ_TOOLS` or
:data:`WRITE_TOOLS`; :func:`unclassified_tools` (exercised by the test suite)
fails when an upstream merge adds a tool that hasn't been classified, so a new
write tool can't slip into a read-only deployment unnoticed.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

READ_ONLY_ENV_VAR = "ZOTERO_MCP_READ_ONLY"
HOSTED_ENV_VAR = "ZOTERO_MCP_HOSTED"

#: Tools that change the library, Zotero's authorization state, or the
#: server's semantic index.
WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "zotero_add_item",
        "zotero_add_item_relation",
        "zotero_attach_file",
        "zotero_authorize_local_writes",
        "zotero_batch_update",
        "zotero_create_annotation",
        "zotero_create_collection",
        "zotero_delete_annotation",
        "zotero_delete_collection",
        "zotero_delete_item",
        "zotero_manage_note",
        "zotero_merge_duplicates",
        "zotero_remove_item_relation",
        "zotero_set_item_collections",
        "zotero_set_item_parent",
        "zotero_update_annotation",
        "zotero_update_collection",
        "zotero_update_item",
        "zotero_update_search_database",
    }
)

#: Tools that only read.
READ_TOOLS: frozenset[str] = frozenset(
    {
        "fetch",
        "scite_check_retractions",
        "scite_enrich_item",
        "scite_enrich_search",
        "search",
        "zotero_advanced_search",
        "zotero_export_bibliography",
        "zotero_find_duplicates",
        "zotero_find_related_papers",
        "zotero_get_annotations",
        "zotero_get_attachment_path",
        "zotero_get_collection_items",
        "zotero_get_collections",
        "zotero_get_feed_items",
        "zotero_get_item_children",
        "zotero_get_item_fulltext",
        "zotero_get_item_metadata",
        "zotero_get_item_related",
        "zotero_get_links",
        "zotero_get_notes",
        "zotero_get_page_layout",
        "zotero_get_pdf_outline",
        "zotero_get_recent",
        "zotero_get_search_database_status",
        "zotero_get_tags",
        "zotero_library_coverage",
        "zotero_list_feeds",
        "zotero_list_libraries",
        "zotero_read_pdf_pages",
        "zotero_search_by_citation_key",
        "zotero_search_by_tag",
        "zotero_search_collections",
        "zotero_search_items",
        "zotero_semantic_search",
        "zotero_switch_library",
        "zotero_synthesize_annotations",
        "zotero_write_capabilities",
    }
)

#: Tools hidden in hosted mode.
HOSTED_HIDDEN_TOOLS: frozenset[str] = frozenset(
    {
        # Need desktop Zotero: its SQLite database, storage directory, or
        # local API.
        "zotero_get_attachment_path",
        "zotero_authorize_local_writes",
        "zotero_write_capabilities",
        "zotero_list_feeds",
        "zotero_get_feed_items",
        # Keys come from the Better BibTeX desktop plugin; over the Web API the
        # tool falls back to scanning every item's Extra field.
        "zotero_search_by_citation_key",
        # The library is pinned by ZOTERO_LIBRARY_ID. Switching sets
        # process-global state (client._active_library_override), which would
        # leak between sessions on a shared server.
        "zotero_list_libraries",
        "zotero_switch_library",
        # Semantic search isn't offered; Zotero's own keyword and full-text
        # search cover the hosted use.
        "zotero_semantic_search",
        "zotero_update_search_database",
        "zotero_get_search_database_status",
    }
)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"true", "yes", "1"}


def is_read_only() -> bool:
    return _env_flag(READ_ONLY_ENV_VAR)


def is_hosted() -> bool:
    return _env_flag(HOSTED_ENV_VAR)


def hidden_tool_names() -> set[str]:
    """Tools to hide under the current environment."""
    hidden: set[str] = set()
    if is_read_only():
        hidden |= WRITE_TOOLS
    if is_hosted():
        hidden |= HOSTED_HIDDEN_TOOLS
        if not _pdf_extra_installed():
            hidden |= PDF_EXTRA_TOOLS
    return hidden


#: Tools that need the ``pdf`` extra (PyMuPDF), which the hosted image leaves
#: out. Hidden in hosted mode when it isn't installed. The ``pdf-geometry``
#: toolset tools need it too, but that group is opt-in already.
PDF_EXTRA_TOOLS: frozenset[str] = frozenset({"zotero_read_pdf_pages"})


def _pdf_extra_installed() -> bool:
    import importlib.util

    return importlib.util.find_spec("fitz") is not None


def hosted_config_errors() -> list[str]:
    """What's missing for hosted mode to reach the Web API; empty when ready.

    Without an API key the server falls back to local mode, which on a server
    starts cleanly and then fails every call, so hosted mode refuses to start.
    """
    if not is_hosted():
        return []
    errors = [
        f"{name} is not set"
        for name in ("ZOTERO_API_KEY", "ZOTERO_LIBRARY_ID")
        if not os.environ.get(name, "").strip()
    ]
    if _env_flag("ZOTERO_LOCAL"):
        errors.append("ZOTERO_LOCAL is set, but hosted mode reads only through the Web API")
    return errors


def unclassified_tools(registered: Iterable[str]) -> list[str]:
    """Registered tools missing from, or listed in both, READ_TOOLS and WRITE_TOOLS."""
    return sorted(
        name
        for name in registered
        if (name in READ_TOOLS) == (name in WRITE_TOOLS)
    )


def register_health_route(mcp) -> None:
    """Add ``GET /healthz`` for platform health checks on HTTP transports.

    It answers without touching the Zotero API, so it reports whether the
    process is serving, not whether Zotero is reachable.
    """
    from starlette.responses import PlainTextResponse

    @mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(request):  # noqa: ARG001 - signature required by Starlette
        return PlainTextResponse("ok")
