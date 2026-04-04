"""
Curated MCP Server — Hand-crafted tools that compose API calls

Raw API mirroring gives the LLM one tool per endpoint, but curated tools
provide higher-level operations that:
  - Compose multiple API calls into a single action
  - Enforce business logic the LLM shouldn't have to know
  - Reduce round-trips and token usage

This server extends the auto-generated tools with curated additions.

Usage:
    # Default (stdio transport, all tools):
    python server_curated.py

    # Filter auto-generated tools by tag (curated tools always included):
    python server_curated.py --tag cases --tag customers

    # Remote/hosted mode (streamable HTTP):
    python server_curated.py --transport streamable-http --port 8080
"""

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from textwrap import dedent

import httpx
from fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Configuration — same env vars as the naive server
# ---------------------------------------------------------------------------

RAILS_API_URL = os.environ.get(
    "RAILS_API_URL",
    "https://api.acme-platform.example.com/api/v3",
)
RAILS_API_TOKEN = os.environ.get("RAILS_API_TOKEN", "demo-token-not-real")


# ---------------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------------
# Both auto-generated tools and curated tools use the same HTTP client.
# The Bearer token is set once here — individual tools never touch auth.

client = httpx.AsyncClient(
    base_url=RAILS_API_URL,
    headers={"Authorization": f"Bearer {RAILS_API_TOKEN}"},
    timeout=30.0,
)


# ---------------------------------------------------------------------------
# Helper: filter spec by tags (same as server_from_spec.py)
# ---------------------------------------------------------------------------


def filter_spec_by_tags(spec: dict, tags: list[str]) -> dict:
    """Return a copy of the spec containing only operations matching the given tags."""
    filtered = deepcopy(spec)
    tag_set = set(tags)
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options"}

    paths_to_remove = []
    for path, path_item in filtered.get("paths", {}).items():
        methods_to_remove = []
        for method in http_methods:
            operation = path_item.get(method)
            if operation is None:
                continue
            operation_tags = set(operation.get("tags", []))
            if not operation_tags.intersection(tag_set):
                methods_to_remove.append(method)
        for method in methods_to_remove:
            del path_item[method]
        if not any(m in path_item for m in http_methods):
            paths_to_remove.append(path)

    for path in paths_to_remove:
        del filtered["paths"][path]

    if "tags" in filtered:
        filtered["tags"] = [t for t in filtered["tags"] if t["name"] in tag_set]

    return filtered


# ---------------------------------------------------------------------------
# Build the MCP server
# ---------------------------------------------------------------------------
# Strategy: start with auto-generated tools from the OpenAPI spec (same as
# the naive server), then layer curated tools on top. This gives the LLM
# both granular API access AND high-level operations.


def build_server(spec: dict) -> FastMCP:
    """Build a FastMCP server with both auto-generated and curated tools."""

    # Step 1: Auto-generate tools from the OpenAPI spec.
    # This gives us the same baseline as server_from_spec.py.
    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="Acme Platform MCP Server (Curated)",
    )

    # ------------------------------------------------------------------
    # Step 2: Add curated tools using the @mcp.tool() decorator.
    #
    # Why curated tools?
    #
    # The auto-generated tools mirror the API 1:1. That's fine for simple
    # lookups, but real support workflows require multiple API calls in
    # sequence. Without curated tools, the LLM has to:
    #   1. Figure out which endpoints to call and in what order.
    #   2. Make each call separately (one round-trip per tool invocation).
    #   3. Piece together the results itself.
    #
    # Curated tools encode that workflow knowledge. One tool call replaces
    # several, reducing latency, token usage, and the chance of errors.
    # ------------------------------------------------------------------

    @mcp.tool()
    async def triage_case(case_id: int) -> str:
        """
        Fetch a support case, its customer profile, and recent notes,
        then return a structured triage summary.

        This replaces three separate API calls (getCase, getCustomer,
        and reading the notes array) with a single tool invocation.
        The summary format is designed to give an LLM everything it
        needs to reason about the case in one shot.
        """
        # Fetch the case detail (includes notes).
        case_resp = await client.get(f"/cases/{case_id}")
        if case_resp.status_code == 404:
            return f"Case {case_id} not found."
        case_resp.raise_for_status()
        case = case_resp.json()

        # Fetch the customer who filed the case.
        customer_resp = await client.get(f"/customers/{case['customer_id']}")
        customer_resp.raise_for_status()
        customer = customer_resp.json()

        # Build a structured triage summary.
        # This format is intentional — it gives the LLM a consistent
        # structure to reason over, regardless of the case contents.
        notes_summary = "No notes yet."
        if case.get("notes"):
            recent_notes = case["notes"][-5:]  # Last 5 notes, most recent context
            notes_lines = []
            for note in recent_notes:
                notes_lines.append(f"  - [{note['created_at']}] {note['author']}: {note['body']}")
            notes_summary = "\n".join(notes_lines)

        return dedent(f"""\
            === Triage Summary for Case #{case_id} ===

            Subject:    {case['subject']}
            Status:     {case['status']}
            Priority:   {case['priority']}
            Created:    {case['created_at']}
            Updated:    {case['updated_at']}

            Customer:   {customer['name']} ({customer['email']})
            Tier:       {customer['tier']}

            Description:
            {case['description']}

            Recent Notes:
            {notes_summary}

            === End Triage Summary ===
        """)

    @mcp.tool()
    async def search_knowledge_for_case(case_id: int, max_results: int = 3) -> str:
        """
        Fetch a case's description, then search the knowledge base for
        articles that might help resolve it.

        This demonstrates tool chaining: it reads from one endpoint
        (getCase) and feeds the result into another (searchArticles).
        The LLM doesn't need to know about this two-step process —
        it just asks "find knowledge articles for case 1024" and gets
        relevant results back.

        Args:
            case_id: The ID of the case to find knowledge articles for.
            max_results: Maximum number of articles to return (default 3).
        """
        # Step 1: Get the case to understand what the issue is about.
        case_resp = await client.get(f"/cases/{case_id}")
        if case_resp.status_code == 404:
            return f"Case {case_id} not found."
        case_resp.raise_for_status()
        case = case_resp.json()

        # Step 2: Use the case subject + description as a semantic search query.
        # The /articles/search endpoint uses embeddings, so natural language works.
        search_query = f"{case['subject']} {case['description']}"
        articles_resp = await client.get(
            "/articles/search",
            params={"q": search_query},
        )
        articles_resp.raise_for_status()
        articles = articles_resp.json().get("data", [])

        # Limit to the requested number of results.
        articles = articles[:max_results]

        if not articles:
            return f"No knowledge base articles found for case #{case_id} ({case['subject']})."

        # Format results for the LLM.
        lines = [f"Knowledge articles relevant to case #{case_id} ({case['subject']}):\n"]
        for i, article in enumerate(articles, 1):
            score = article.get("relevance_score", "N/A")
            lines.append(f"{i}. [{article['title']}] (ID: {article['id']}, relevance: {score})")
            lines.append(f"   Category: {article.get('category', 'N/A')}")
            # Include a preview of the content (first 200 chars).
            content_preview = article.get("content", "")[:200]
            if len(article.get("content", "")) > 200:
                content_preview += "..."
            lines.append(f"   Preview: {content_preview}")
            lines.append("")

        return "\n".join(lines)

    @mcp.tool()
    async def draft_response(case_id: int, tone: str = "professional") -> str:
        """
        Fetch case context and return a suggested response template
        that an agent can review and customize before sending.

        This is a value-added tool — it doesn't just mirror an API call,
        it provides a starting point that incorporates case context.
        The tone parameter lets the LLM adjust formality.

        Note: This returns a TEMPLATE, not a final response. The agent
        should always review and edit before sending to the customer.

        Args:
            case_id: The ID of the case to draft a response for.
            tone: Response tone — 'professional' (default), 'friendly', or 'technical'.
        """
        # Gather context: case details + customer info.
        case_resp = await client.get(f"/cases/{case_id}")
        if case_resp.status_code == 404:
            return f"Case {case_id} not found."
        case_resp.raise_for_status()
        case = case_resp.json()

        customer_resp = await client.get(f"/customers/{case['customer_id']}")
        customer_resp.raise_for_status()
        customer = customer_resp.json()

        # Also search for relevant knowledge articles to include links.
        articles_resp = await client.get(
            "/articles/search",
            params={"q": case["subject"]},
        )
        articles_resp.raise_for_status()
        articles = articles_resp.json().get("data", [])[:2]  # Top 2 articles

        # Build the response template.
        # The tone parameter adjusts the greeting and closing.
        greetings = {
            "professional": f"Dear {customer['name']} team,",
            "friendly": f"Hi {customer['name']} team!",
            "technical": f"Hello,",
        }
        closings = {
            "professional": "Best regards,",
            "friendly": "Thanks so much!",
            "technical": "Regards,",
        }
        greeting = greetings.get(tone, greetings["professional"])
        closing = closings.get(tone, closings["professional"])

        # Build article references if we have relevant ones.
        article_section = ""
        if articles:
            article_lines = ["You may also find these resources helpful:"]
            for article in articles:
                article_lines.append(f"  - {article['title']}")
            article_section = "\n".join(article_lines) + "\n\n"

        template = dedent(f"""\
            === Draft Response Template (tone: {tone}) ===
            === Review and edit before sending to the customer ===

            {greeting}

            Thank you for reaching out regarding: {case['subject']}

            [AGENT: Summarize the investigation findings and resolution here]

            {article_section}{closing}
            [Your Name]
            Acme Platform Support

            === End Template ===

            Context used:
            - Case #{case_id}: {case['subject']} (status: {case['status']}, priority: {case['priority']})
            - Customer: {customer['name']} (tier: {customer['tier']})
            - Relevant articles found: {len(articles)}
        """)

        return template

    return mcp


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Acme Platform MCP server (curated tools + auto-generated).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        help=(
            "Filter auto-generated tools by OpenAPI tag. "
            "Can be repeated. Curated tools are always included. "
            "Available tags: cases, customers, knowledge, internal."
        ),
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="Transport mode (default: stdio).",
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

    # Load the OpenAPI spec.
    spec_path = Path(__file__).parent / "mock_openapi_spec.json"
    with open(spec_path) as f:
        spec = json.load(f)

    total_ops = sum(
        1
        for path_item in spec.get("paths", {}).values()
        for method in ("get", "post", "put", "patch", "delete")
        if method in path_item
    )

    # Apply tag filtering to the auto-generated tools.
    if args.tags:
        spec = filter_spec_by_tags(spec, args.tags)

    active_ops = sum(
        1
        for path_item in spec.get("paths", {}).values()
        for method in ("get", "post", "put", "patch", "delete")
        if method in path_item
    )

    # Build the server (auto-generated + curated tools).
    mcp = build_server(spec)

    # Curated tools are always available regardless of tag filtering.
    curated_count = 3  # triage_case, search_knowledge_for_case, draft_response

    active_tags = args.tags if args.tags else [t["name"] for t in spec.get("tags", [])]
    print("=" * 60, file=sys.stderr)
    print("  Acme Platform MCP Server (Curated)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Transport:         {args.transport}", file=sys.stderr)
    print(f"  API base URL:      {RAILS_API_URL}", file=sys.stderr)
    print(f"  Auto-gen tools:    {active_ops} of {total_ops} operations", file=sys.stderr)
    print(f"  Curated tools:     {curated_count}", file=sys.stderr)
    print(f"  Total tools:       {active_ops + curated_count}", file=sys.stderr)
    print(f"  Active tags:       {', '.join(active_tags)}", file=sys.stderr)
    if args.transport == "streamable-http":
        print(f"  Port:              {args.port}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
