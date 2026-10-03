"""Links to an item and its attachments, for pasting into notes and task tools."""

import re

from zotero_mcp import library as _library
from zotero_mcp import utils as _utils
from zotero_mcp._app import mcp
from zotero_mcp._context import Context
from zotero_mcp.client import with_zotero_api_lock
from zotero_mcp.tools import _helpers

_ITEM_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")


@mcp.tool(
    name="zotero_get_links",
    description=(
        "Get shareable links for a Zotero item and its attachments (PDFs, "
        "snapshots), to paste into notes, documents, or task tools. "
        "Returns the item's page in the zotero.org web library and each "
        "attachment's web-library page, which open in any browser for "
        "someone signed in to Zotero; the DOI link when the item has one; "
        "and zotero:// links that open the item or PDF in the Zotero desktop "
        "app. Web-library links need the Zotero Web API; other modes return "
        "only the DOI and desktop links. "
        "item_key: the 8-character key of a top-level item (search results "
        "show it) or of an attachment. "
        "Example: zotero_get_links(item_key='RTKZQI8E')."
    ),
)
@with_zotero_api_lock
def get_links(item_key: str, *, ctx: Context) -> str:
    """Web-library, DOI, and desktop links for an item and its attachments."""
    key = (item_key or "").strip().upper()
    if not _ITEM_KEY_RE.match(key):
        return f"Error: '{item_key}' is not a Zotero item key (8 letters or digits)."

    backend = _library.get_library_backend()
    try:
        item = backend.get_item(key)
    except Exception as e:
        ctx.error(f"Error fetching item {key}: {e}")
        return f"Error fetching item {key}: {e}"
    if not item:
        return f"No item found with key `{key}`."

    data = item.get("data", {})
    title = _utils.item_display_title(data)
    lines = [f"# Links for {title}", f"**Item Key:** {key}", ""]

    if data.get("itemType") == "attachment":
        lines += _attachment_lines(item)
        return "\n".join(lines).rstrip()

    if url := _utils.web_library_url(item):
        lines.append(f"- **Zotero web library:** {url}")
    if doi := _helpers._normalize_doi(data.get("DOI", "")):
        lines.append(f"- **DOI:** https://doi.org/{doi}")
    lines.append(f"- **Zotero desktop:** zotero://select/library/items/{key}")

    try:
        children = backend.get_children([key], item_type="attachment").get(key)
    except Exception as e:
        ctx.warning(f"Couldn't list attachments for {key}: {e}")
        children = None

    lines.append("")
    if children is None:
        lines.append("Attachments: couldn't be listed.")
    elif not children:
        lines.append("Attachments: none.")
    else:
        lines.append("## Attachments")
        for child in children:
            lines.append("")
            lines += _attachment_lines(child, heading="###")

    return "\n".join(lines).rstrip()


def _attachment_lines(attachment: dict, heading: str = "##") -> list[str]:
    data = attachment.get("data", {})
    key = attachment.get("key") or data.get("key", "")
    name = data.get("title") or data.get("filename") or key
    content_type = data.get("contentType") or "unknown type"
    link_mode = data.get("linkMode", "")

    lines = [f"{heading} {name} ({content_type})", f"**Attachment Key:** {key}"]
    if link_mode == "linked_url":
        if url := data.get("url"):
            lines.append(f"- **Web page:** {url}")
        return lines

    if url := _utils.web_library_url(attachment):
        lines.append(f"- **Zotero web library:** {url}")
    if content_type == "application/pdf":
        lines.append(f"- **Zotero desktop (open PDF):** zotero://open-pdf/library/items/{key}")
    else:
        lines.append(f"- **Zotero desktop:** zotero://select/library/items/{key}")
    if link_mode == "linked_file":
        lines.append("- Note: a linked file lives on one computer, not in Zotero storage, so it opens only there.")
    return lines
