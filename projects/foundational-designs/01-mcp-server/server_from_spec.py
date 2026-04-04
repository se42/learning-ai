"""
Naive MCP Server — Auto-generated from OpenAPI Spec

This is the quickest path from an existing API to an MCP server.
FastMCP.from_openapi() reads your OpenAPI spec and creates one MCP tool
per operation. Users get every endpoint as a tool their LLM can call.

Usage:
    # Default (stdio transport, all tools):
    python server_from_spec.py

    # Filter to specific tag groups:
    python server_from_spec.py --tag cases --tag customers

    # Remote/hosted mode (streamable HTTP):
    python server_from_spec.py --transport streamable-http --port 8080
"""

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap


# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------
# In production, users set RAILS_API_TOKEN to their actual token.
# The URL defaults to the mock spec's server URL for demo purposes.

RAILS_API_URL = os.environ.get(
    "RAILS_API_URL",
    "https://api.acme-platform.example.com/api/v3",
)
RAILS_API_TOKEN = os.environ.get("RAILS_API_TOKEN", "demo-token-not-real")


# ---------------------------------------------------------------------------
# Helper: filter an OpenAPI spec to only include operations with given tags
# ---------------------------------------------------------------------------
# Why filter? A mature Rails app might have 50+ endpoints. Loading all of
# them as MCP tools floods the LLM's context window with tool definitions,
# which degrades response quality and wastes tokens. Tag-based filtering
# lets you serve a focused subset — e.g., only case-management tools for a
# support-focused integration.


def filter_spec_by_tags(spec: dict, tags: list[str]) -> dict:
    """
    Return a copy of the OpenAPI spec containing only operations whose tags
    intersect with the requested tag list.

    This works by iterating every path and every method within it. If an
    operation's tags don't overlap with the filter set, the operation is
    removed. Paths that end up with zero operations are removed entirely.
    """
    # Work on a deep copy so we don't mutate the original spec.
    filtered = deepcopy(spec)
    tag_set = set(tags)

    # Standard HTTP methods that can appear as keys under a path item.
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options"}

    paths_to_remove = []

    for path, path_item in filtered.get("paths", {}).items():
        methods_to_remove = []

        for method in http_methods:
            operation = path_item.get(method)
            if operation is None:
                continue

            # An operation's tags is a list of strings.
            # If the operation has no tags, it won't match any filter.
            operation_tags = set(operation.get("tags", []))
            if not operation_tags.intersection(tag_set):
                methods_to_remove.append(method)

        # Remove non-matching methods from this path.
        for method in methods_to_remove:
            del path_item[method]

        # If no methods remain, mark the whole path for removal.
        remaining_methods = [m for m in http_methods if m in path_item]
        if not remaining_methods:
            paths_to_remove.append(path)

    for path in paths_to_remove:
        del filtered["paths"][path]

    # Also filter the top-level tags array to only include active tags,
    # so the spec stays internally consistent.
    if "tags" in filtered:
        filtered["tags"] = [t for t in filtered["tags"] if t["name"] in tag_set]

    return filtered


# ---------------------------------------------------------------------------
# Build the MCP server from the OpenAPI spec
# ---------------------------------------------------------------------------


def build_server(spec: dict) -> FastMCP:
    """
    Create a FastMCP server from an OpenAPI spec dictionary.

    FastMCP.from_openapi() does the heavy lifting:
      - Each OpenAPI operation becomes one MCP tool.
      - The tool name comes from operationId.
      - The tool description comes from the operation summary + description.
      - Parameters (query, path, body) become tool input arguments.
      - The httpx client handles actual HTTP requests to the Rails API.
    """
    # Set up the HTTP client that will make real API calls.
    # The Bearer token is injected here — the LLM never sees or handles it.
    client = httpx.AsyncClient(
        base_url=RAILS_API_URL,
        headers={"Authorization": f"Bearer {RAILS_API_TOKEN}"},
        timeout=30.0,
    )

    # from_openapi() parses the spec and registers one tool per operation.
    # The returned object is a fully configured FastMCP server instance.
    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="Acme Platform MCP Server",
    )

    return mcp


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Acme Platform MCP server (auto-generated from OpenAPI spec).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help=(
            "Only expose tools for the specified OpenAPI tag. "
            "Can be repeated: --tag cases --tag customers. "
            "Available tags: cases, customers, knowledge, internal."
        ),
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="Transport mode. 'stdio' for local IDE integration (default), "
        "'streamable-http' for remote/hosted deployment.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for streamable-http transport (default: 8080).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    # Load the OpenAPI spec from the same directory as this script.
    spec_path = Path(__file__).parent / "mock_openapi_spec.json"
    with open(spec_path) as f:
        spec = json.load(f)

    # Count total operations before any filtering (for the startup summary).
    total_ops = sum(
        1
        for path_item in spec.get("paths", {}).values()
        for method in ("get", "post", "put", "patch", "delete")
        if method in path_item
    )

    # Apply tag filter if requested.
    if args.tags:
        spec = filter_spec_by_tags(spec, args.tags)

    # Count operations after filtering.
    active_ops = sum(
        1
        for path_item in spec.get("paths", {}).values()
        for method in ("get", "post", "put", "patch", "delete")
        if method in path_item
    )

    # Build the server from the (possibly filtered) spec.
    mcp = build_server(spec)

    # Print startup summary to stderr (stdout is reserved for stdio transport).
    active_tags = args.tags if args.tags else [t["name"] for t in spec.get("tags", [])]
    print("=" * 60, file=sys.stderr)
    print("  Acme Platform MCP Server (from OpenAPI spec)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Transport:    {args.transport}", file=sys.stderr)
    print(f"  API base URL: {RAILS_API_URL}", file=sys.stderr)
    print(f"  Tools loaded: {active_ops} of {total_ops} operations", file=sys.stderr)
    print(f"  Active tags:  {', '.join(active_tags)}", file=sys.stderr)
    if args.transport == "streamable-http":
        print(f"  Port:         {args.port}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Start the server. For stdio transport, this reads from stdin and writes
    # to stdout using the MCP JSON-RPC protocol. For streamable-http, it
    # starts an HTTP server on the specified port.
    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
