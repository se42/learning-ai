# 01 — MCP Server from OpenAPI Spec

This module demonstrates how to build an MCP server from an existing OpenAPI spec and distribute it via Docker or uv for IDE integration.

**Scenario:** Your team has a mature Rails monolith with ~50 API endpoints across 3 OpenAPI spec versions. You want to let your users' LLMs interact with the API on their behalf — from inside their IDE (Cursor, Windsurf, Claude Desktop). Users provide their existing Rails API token as an environment variable. The MCP server handles the rest.

---

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard for connecting LLMs to external tools and data sources. If APIs are how applications talk to each other, MCP is how LLMs talk to applications. It provides a structured way for an LLM to discover, understand, and invoke external capabilities during a conversation.

An MCP server exposes three types of primitives:
- **Tools** — functions the LLM can invoke (e.g., "create a support case", "search the knowledge base")
- **Resources** — data the LLM can read (e.g., a customer's profile, a configuration file)
- **Prompts** — templates for common interactions (e.g., "triage this case", "draft a response")

The LLM's host application (Cursor, Claude Desktop, Windsurf) connects to MCP servers and makes their capabilities available during conversations. The user asks "look up customer 42", the LLM calls the `getCustomer` tool, and the result flows back into the conversation. The user never leaves their IDE.

MCP supports multiple **transports** — the mechanism by which the host application communicates with the server. The two you'll encounter are **stdio** (for local processes) and **streamable HTTP** (for remote/hosted servers). This module covers both.

---

## The OpenAPI Shortcut

If you already have an OpenAPI spec — and most mature Rails apps do — you can generate an MCP server with almost zero code.

`FastMCP.from_openapi()` reads your spec and creates one MCP tool per operation. Each operation's `operationId` becomes the tool name. The `summary` and `description` become the tool's description (what the LLM reads to decide when to use it). Parameters, request bodies, and response schemas are preserved.

Here's the pipeline:

```
OpenAPI Spec (JSON) → FastMCP.from_openapi() → MCP Server → LLM tools
```

**Before (OpenAPI operation):**
```json
{
  "operationId": "listCases",
  "summary": "List support cases",
  "description": "Returns a paginated list of support cases...",
  "parameters": [
    {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["open", "pending", "resolved", "closed"]}},
    {"name": "customer_id", "in": "query", "schema": {"type": "integer"}},
    {"name": "page", "in": "query", "schema": {"type": "integer"}}
  ]
}
```

**After (MCP tool, as the LLM sees it):**
```
Tool: listCases
Description: List support cases — Returns a paginated list of support cases...
Parameters:
  - status (string, optional): open | pending | resolved | closed
  - customer_id (integer, optional)
  - page (integer, optional)
```

The code that makes this happen is in `server_from_spec.py` — it's about 30 lines of actual logic. Load the spec, create an httpx client with auth, call `from_openapi()`, done.

---

## Tag-Based Tool Filtering

With 50+ endpoints, loading every tool overwhelms the LLM's context window and degrades performance. Every tool definition consumes tokens, and LLMs make worse decisions when presented with too many options.

OpenAPI tags let you organize endpoints into logical groups. This spec uses four:

| Tag | Tools | Description |
|-----|-------|-------------|
| `cases` | `listCases`, `createCase`, `getCase` | Support case management |
| `customers` | `listCustomers`, `getCustomer` | Customer records |
| `knowledge` | `listArticles`, `searchArticles` | Knowledge base articles |
| `internal` | `addCaseNote` | Internal team operations |

Filter at startup with the `--tag` flag:

```bash
# All 8 tools (default):
python server_from_spec.py

# Just case management (3 tools):
python server_from_spec.py --tag cases

# Cases + customers (5 tools):
python server_from_spec.py --tag cases --tag customers
```

The filtering happens before tools are registered: `filter_spec_by_tags()` strips non-matching operations from the spec, then `from_openapi()` only sees what's left.

This is a practical pattern for real deployments. A support agent integration might load `cases` + `customers` + `knowledge`. A bot that only triages might load just `cases`. The same spec, the same server code — different tool sets for different use cases.

---

## From Naive to Curated

Raw API mirroring is a starting point, not the destination. The naive server exposes every endpoint as a separate tool. That works, but it forces the LLM to orchestrate multi-step workflows itself:

**Without curated tools (3 round-trips):**
```
LLM → getCase(1024)         → case data
LLM → getCustomer(42)       → customer data
LLM → [reads notes from case response, synthesizes triage summary]
```

**With curated tool (1 round-trip):**
```
LLM → triage_case(1024)     → complete triage summary
```

`server_curated.py` demonstrates this progression. It starts with the same auto-generated tools, then adds three curated tools:

1. **`triage_case(case_id)`** — Fetches case + customer + notes, returns a structured triage summary. One tool call replaces three API calls. The summary format is consistent, so the LLM can reason over it reliably.

2. **`search_knowledge_for_case(case_id)`** — Fetches the case description, then uses it as a semantic search query against the knowledge base. Demonstrates tool chaining: the output of one API call feeds into another.

3. **`draft_response(case_id, tone)`** — Gathers case context and returns a response template. This is value-added tooling — it doesn't just mirror an API, it provides a starting point that incorporates context.

**When to create curated tools:**
- When a common workflow requires 2+ API calls in sequence
- When business logic should be enforced (e.g., "always check customer tier before escalating")
- When you want to control the format of what the LLM sees
- When reducing round-trips meaningfully improves latency

**The progression:**
1. **Naive** — One tool per endpoint. Fast to build, good enough to validate.
2. **Curated** — Hand-crafted tools for common workflows. Better UX, fewer errors.
3. **Agentic** — Tools that make decisions (e.g., auto-routing cases based on content). Future module territory.

---

## Distribution: Docker or uv

Users can run the MCP server via **Docker** (zero-dependency, fully isolated) or **uv** (lightweight, no Docker required). Both run the same server code — the only difference is packaging.

**Docker** is the "just works" option: one command, no Python install needed, no dependency conflicts. **uv** (`uvx`) is for users who already have Python 3.11+ and prefer not to introduce Docker — common in security-conscious environments where Docker may require additional policy approvals.

### Option A: Docker

```bash
# Build the image:
docker build -t acme-mcp .

# STDIO mode (default) — for local IDE integration:
docker run -i --rm -e RAILS_API_TOKEN=xxx acme-mcp

# Streamable HTTP mode — for remote/hosted deployment:
docker run -p 8080:8080 -e RAILS_API_TOKEN=xxx acme-mcp python server_from_spec.py --transport streamable-http

# With tag filtering:
docker run -i --rm -e RAILS_API_TOKEN=xxx acme-mcp python server_from_spec.py --tag cases

# Using the curated server:
docker run -i --rm -e RAILS_API_TOKEN=xxx acme-mcp python server_curated.py
```

### Option B: uv (Python)

`uvx` runs the package directly — it handles the virtualenv and dependencies transparently, so the user experience is nearly as clean as Docker.

```bash
# STDIO mode (default):
RAILS_API_TOKEN=xxx uvx acme-mcp-server

# With tag filtering:
RAILS_API_TOKEN=xxx uvx acme-mcp-server --tag cases

# Using the curated server:
RAILS_API_TOKEN=xxx uvx acme-mcp-server-curated

# Streamable HTTP mode:
RAILS_API_TOKEN=xxx uvx acme-mcp-server --transport streamable-http --port 8080
```

The `[project.scripts]` entry points in `pyproject.toml` make this work — `acme-mcp` and `acme-mcp-curated` map to the `main()` functions in `server_from_spec.py` and `server_curated.py` respectively.

### IDE Configuration

Each IDE has its own config format and file location. Sample configs are in `ide_configs/`, with both Docker and uv variants for each IDE.

**Cursor** — `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):
```json
{
  "mcpServers": {
    "acme-platform": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "RAILS_API_TOKEN", "acme-mcp:latest"],
      "env": { "RAILS_API_TOKEN": "your-token-here" }
    },
    "acme-platform-uv": {
      "_comment": "Alternative: run via uvx (requires Python 3.11+ and uv)",
      "command": "uvx",
      "args": ["acme-mcp-server"],
      "env": { "RAILS_API_TOKEN": "your-token-here" }
    }
  }
}
```

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):
```json
{
  "mcpServers": {
    "acme-platform": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "RAILS_API_TOKEN", "acme-mcp:latest"],
      "env": { "RAILS_API_TOKEN": "your-token-here" }
    },
    "acme-platform-uv": {
      "_comment": "Alternative: run via uvx (requires Python 3.11+ and uv)",
      "command": "uvx",
      "args": ["acme-mcp-server"],
      "env": { "RAILS_API_TOKEN": "your-token-here" }
    }
  }
}
```

**Windsurf** — `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "acme-platform": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "RAILS_API_TOKEN", "acme-mcp:latest"],
      "env": { "RAILS_API_TOKEN": "your-token-here" }
    },
    "acme-platform-uv": {
      "_comment": "Alternative: run via uvx (requires Python 3.11+ and uv)",
      "command": "uvx",
      "args": ["acme-mcp-server"],
      "env": { "RAILS_API_TOKEN": "your-token-here" }
    }
  }
}
```

Users pick one — `acme-platform` (Docker) or `acme-platform-uv` — and remove the other. In practice you'd document both and let users choose based on their environment.

### Transport Comparison

| Aspect | Local (stdio) | Remote (streamable-http) |
|--------|---------------|--------------------------|
| Transport | stdin/stdout | HTTPS |
| Auth | Env var (API token) | OAuth 2.1 / headers |
| Deployment | User's machine | Your infrastructure |
| Scaling | Single user | Multi-tenant |
| State | Per-process | Per-session |
| When to use | Starting out, distributable image | Production, hosted service |

Start with stdio. It's simpler, requires no infrastructure, and is how most MCP servers are distributed today. Users choose Docker or uv based on their environment — both use stdio by default. Move to streamable HTTP when you need centralized control, multi-tenant auth, or want to eliminate client-side installation entirely.

---

## Running the Demo

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) — for development and uv-based distribution
- Docker — for Docker-based distribution (optional if using uv)

### Local Development

```bash
# Install dependencies:
uv sync

# Run the naive server (stdio mode, all tools):
python server_from_spec.py

# Run with tag filtering (cases only):
python server_from_spec.py --tag cases

# Run the curated server:
python server_curated.py

# Run in streamable-http mode:
python server_from_spec.py --transport streamable-http --port 8080
```

### Using the MCP Inspector

FastMCP includes a development inspector that lets you browse tools and test them interactively:

```bash
fastmcp dev server_from_spec.py
```

This opens a web UI where you can see all registered tools, their parameters, and invoke them manually. It's the fastest way to verify your server works before connecting an IDE.

### Docker

```bash
# Build:
docker build -t acme-mcp .

# Run (stdio):
docker run -i --rm -e RAILS_API_TOKEN=your-token acme-mcp

# Run (streamable-http):
docker run -p 8080:8080 -e RAILS_API_TOKEN=your-token acme-mcp python server_from_spec.py --transport streamable-http
```

Note: Since this is a demo with a mock spec, API calls will fail (there's no real server at `api.acme-platform.example.com`). The value is in seeing the server startup, tool registration, and MCP protocol interaction. To test with a real API, point `RAILS_API_URL` at your actual server and provide a valid token.

---

## What's Next

This module covers the foundation: spec-to-server generation, tag filtering, curated tools, and dual distribution (Docker + uv). The next modules build on this:

- **02-skills/** — Composing tools into higher-level skills that encode multi-step workflows
- **03-intelligence-service/** — The path from distributable MCP server to hosted MCP server with OAuth, multi-tenancy, and observability
