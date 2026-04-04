# Distributable MCP Server — Docker Distribution Path
#
# This image is one of two distribution options for the MCP server.
# Users who prefer not to use Docker can run via uv instead:
#   RAILS_API_TOKEN=xxx uvx acme-mcp-server
#
# This image supports two transport modes:
#
#   STDIO (default) — for local IDE integration:
#     docker run -i --rm -e RAILS_API_TOKEN=xxx acme-mcp
#
#   Streamable HTTP — for remote/hosted deployment:
#     docker run -p 8080:8080 -e RAILS_API_TOKEN=xxx acme-mcp --transport streamable-http
#
# The same image serves both modes. STDIO is the starting point;
# streamable HTTP is the path to a hosted MCP server later.
#
# Build:
#     docker build -t acme-mcp .
#
# Override to use curated server:
#     docker run -i --rm -e RAILS_API_TOKEN=xxx acme-mcp python server_curated.py
#
# Filter by tags:
#     docker run -i --rm -e RAILS_API_TOKEN=xxx acme-mcp python server_from_spec.py --tag cases

# --- Base image ---
# python:3.12-slim keeps the image small (~150MB) while including
# everything we need. Alpine would be smaller but causes issues with
# some Python C extensions.
FROM python:3.12-slim

# --- Install uv ---
# uv is a fast Python package manager. We use it instead of pip for
# faster, more reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# --- Set up working directory ---
WORKDIR /app

# --- Copy dependency definition first ---
# Docker layer caching: if pyproject.toml hasn't changed, the
# dependency install layer is reused even when code changes.
COPY pyproject.toml .

# --- Install dependencies ---
# --system installs into the system Python (no virtualenv needed in Docker).
# --no-dev skips development dependencies.
RUN uv pip install --system -r pyproject.toml

# --- Copy application code ---
COPY mock_openapi_spec.json .
COPY server_from_spec.py .
COPY server_curated.py .

# --- Expose port for streamable-http mode ---
# Only used when running with --transport streamable-http.
# Ignored in stdio mode (the default).
EXPOSE 8080

# --- Entry point ---
# ENTRYPOINT + CMD pattern allows users to override CMD to pass flags.
#
# Default: runs the naive server in stdio mode.
# Override examples:
#   docker run ... acme-mcp python server_from_spec.py --tag cases
#   docker run ... acme-mcp python server_curated.py
#   docker run ... acme-mcp python server_from_spec.py --transport streamable-http
ENTRYPOINT ["python"]
CMD ["server_from_spec.py"]
