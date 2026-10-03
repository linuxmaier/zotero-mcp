# Hosted image: a read-only, Web-API-only MCP server for one personal library,
# served over streamable HTTP (see AGENTS.md). The upstream Dockerfile at the
# repo root stays as it is, so upstream merges don't conflict here.
#
# Core install only: no semantic, pdf, or scite extras, so no torch or PyMuPDF.
# Build from the repo root: docker build -f docker/hosted.Dockerfile .
FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install . && rm -rf /src

RUN useradd --create-home --shell /usr/sbin/nologin app
USER app
WORKDIR /home/app

# Deployment defaults; the platform's compose file can override any of them.
# ZOTERO_API_KEY and ZOTERO_LIBRARY_ID come from the platform's secrets.
ENV ZOTERO_MCP_HOSTED=true \
    ZOTERO_MCP_READ_ONLY=true \
    ZOTERO_MCP_TOOLSETS="none,-chatgpt-connector" \
    ZOTERO_LIBRARY_TYPE=user \
    ZOTERO_NO_CLAUDE=true

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]

ENTRYPOINT ["zotero-mcp", "serve", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
