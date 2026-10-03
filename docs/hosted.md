# Hosted mode

How this fork runs as a remote, read-only MCP server for one personal library over the Zotero Web API. Built by `docker/hosted.Dockerfile`; deployed by the home-server platform.

## Configuration

All configuration comes from environment variables. The image sets the defaults below; the deployment supplies the two secrets.

| Variable | Image default | Meaning |
|---|---|---|
| `ZOTERO_API_KEY` | (secret) | Zotero API key. Create it at zotero.org/settings/keys with only **Allow library access** checked, so it can't write. |
| `ZOTERO_LIBRARY_ID` | (secret) | The numeric user ID shown on the same page ("Your userID for use in API calls"). |
| `ZOTERO_LIBRARY_TYPE` | `user` | Personal library. |
| `ZOTERO_MCP_HOSTED` | `true` | Hide tools that need desktop Zotero, library switching, citation-key lookup, semantic search, and (without PyMuPDF) PDF page rendering. Refuse to start without the API key and library ID. |
| `ZOTERO_MCP_READ_ONLY` | `true` | Hide every write tool. |
| `ZOTERO_MCP_TOOLSETS` | `none,-chatgpt-connector` | No optional toolsets, and no ChatGPT `search`/`fetch` pair. |
| `ZOTERO_NO_CLAUDE` | `true` | Don't look for a Claude Desktop config. |

The server listens on port 8000: MCP at `/mcp`, and `GET /healthz` returns `ok` without calling Zotero. Authentication is handled in front of it (Cloudflare Access and the platform's JWT sidecar), not by the server.

The server keeps no state that needs backing up: it writes only caches it can rebuild.

## Tools

With the defaults above, 16 tools (about 7k tokens of tool definitions, down from about 16k for upstream's default profile over HTTP):

- **Search:** `zotero_search_items`, `zotero_advanced_search`, `zotero_search_by_tag`, `zotero_search_collections`, `zotero_get_recent`
- **Read:** `zotero_get_item_metadata`, `zotero_get_item_fulltext`, `zotero_get_item_children`, `zotero_get_notes`, `zotero_get_annotations`, `zotero_synthesize_annotations`, `zotero_export_bibliography`
- **Browse:** `zotero_get_collections`, `zotero_get_collection_items`, `zotero_get_tags`
- **Links:** `zotero_get_links`

Full text comes from Zotero's own full-text index, which the user's desktop Zotero builds and syncs. Search results and metadata include a `**Zotero link:**` line: the item's page in the zotero.org web library, as the Web API reports it.
