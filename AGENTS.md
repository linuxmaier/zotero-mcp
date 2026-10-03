# zotero-mcp (hosted fork)

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`, never the symlink.

This is linuxmaier's fork of [54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp) (remote `upstream`). It runs as a **read-only MCP connector in claude.ai** for one person's **personal Zotero library**, reached only through the **Zotero Web API**. It's deployed as an app on the home-server platform (`linuxmaier/home-server`, `apps/zotero-mcp/`; design in that repo's ADR 0011), behind Cloudflare Access with Managed OAuth.

The user's goal: while working on something, find related papers in their library, and get links to items and PDFs to paste into their tasks (in Notion, reached through its own connector). Work is tracked in the "Hosted v1" milestone on GitHub.

## Branches and deploys

- **`production` is what deploys automatically.** A push to `production` builds the hosted image and publishes it to GHCR (`ghcr.io/linuxmaier/zotero-mcp-hosted`, tagged with the commit SHA and `production`); the home-server platform deploys it from there. Promote by merging `main` into `production`, only after tests pass on `main`.
- **`main`** is the integration branch: feature branches merge here through PRs, and so do upstream merges. Pushes to `main` build the image but don't publish it.
- Never push to `production` without the operator asking.

## Scope

- Expose what Zotero itself offers (search, metadata, full text, notes, annotations, collections, tags, web-library links). Don't build features Zotero doesn't have.
- Semantic search is out of scope for now; Zotero's keyword and full-text search cover it.
- Read-only: the deployment uses a read-only Zotero API key, and write tools are hidden.

## How the fork differs from upstream

Keep the diff small and additive so upstream merges stay cheap. Prefer new modules and environment switches over edits to large upstream files.

| Change | Where |
|---|---|
| Read-only and hosted tool hiding, tool read/write classification, `/healthz` | `src/zotero_mcp/hosted.py` (applied in `toolsets.apply_toolsets`) |
| Hosted mode refuses to start without Web API credentials | `cli.py` (`serve`) |
| `zotero_get_links`, and a `**Zotero link:**` line in results and metadata | `src/zotero_mcp/tools/links.py`, `utils.web_library_url` |
| Hosted image and its CI | `docker/hosted.Dockerfile`, `.github/workflows/hosted-image.yml` |

Configuration and the tool list are in [`docs/hosted.md`](docs/hosted.md).

**When merging upstream:** run the tests. `tests/test_hosted.py` fails if upstream added a tool that isn't classified in `hosted.py` as read or write; classify it before deploying, so a new write tool can't reach the read-only deployment.

## Development

- Tools are pinned in `mise.toml`. Set up with `mise exec -- uv venv && mise exec -- uv pip install -e ".[dev]"`.
- Tests: `.venv/bin/python -m pytest -q --ignore=tests/live`. `tests/test_webdav.py::test_download_attachment_file_falls_back_to_webdav` fails only in a full run (order-dependent; it predates the fork's changes).
- Build and run the hosted image locally: `docker build -f docker/hosted.Dockerfile -t zotero-mcp-hosted:dev .`, then run it with `ZOTERO_API_KEY` and `ZOTERO_LIBRARY_ID` set.
- Commit or push only when asked.
