# Foundational Designs: Adding AI to a Rails Monolith

An instructional module demonstrating two pathways for adding AI capabilities to a mature Rails application via a service-oriented architecture.

| Pathway | What | Who | Where it runs |
|---------|------|-----|---------------|
| **Distributable MCP Server** | API tools + skills for IDEs | Your users | User's machine |
| **Intelligence Microservice** | Chat, search, extraction over HTTP | Your Rails app | Your infrastructure |

These are independent systems that serve the same Rails application from different angles. The MCP server gives your users AI-powered API access in their IDE. The intelligence service gives your Rails application AI capabilities internally.

See [assets/architecture.md](assets/architecture.md) for the full system diagram.

---

## Modules

| Module | Description |
|--------|-------------|
| [01-mcp-server/](01-mcp-server/) | MCP server auto-generated from OpenAPI spec, with tag filtering, curated tools, Docker distribution, and IDE configs |
| [02-skills/](02-skills/) | Four demo skills covering the full SKILL.md spec: basic tools, shell injection, subagent isolation, and safety controls |
| [03-intelligence-service/](03-intelligence-service/) | FastAPI microservice with chat proxy (+ SSE streaming), document search, and structured extraction |

Developer workflow skills for working on this project live in [.cursor/skills/](.cursor/skills/).

---

## Strategic Questions & Answers

### 1. Are these solid first steps?

**Yes.** Both pathways are achievable with minimal ops/infra work:

- **The MCP server requires zero infrastructure.** You build a Docker image; users run it locally. Their IDE connects via stdio. Auth is their existing API token passed as an environment variable. No new servers, no new auth flows, no new network policies.

- **The intelligence service is a single FastAPI app.** Rails makes HTTP POST requests — something it already does extensively. You deploy it the same way you deploy any Python service (ECS, Kubernetes, whatever you already run). No new protocols, no new dependencies on the Rails side beyond an HTTP client.

**One thing to watch:** When you graduate from a distributable MCP server (local, stdio) to a hosted MCP server (remote, streamable HTTP), you'll need OAuth 2.1 for multi-tenant auth. The MCP spec adopted OAuth 2.1 in late 2025. This isn't a blocker for starting — it's a known future complexity that you can plan for while the distributable approach proves value.

### 2. Are these popular, valuable patterns in 2026?

**Yes, both are mainstream.**

**MCP** adoption exploded in 2025-2026. It is the standard protocol for connecting LLMs to external tools, supported by Anthropic (Claude Code, Claude Desktop), Cursor, Windsurf, VS Code with GitHub Copilot, Gemini CLI, and 20+ other tools. The specification is at version 2025-11-25 with active development. Companies like Stripe, Cloudflare, and Sentry ship MCP servers for their APIs. FastMCP 3.x (released Feb-Mar 2026) makes server creation trivial, including native OpenAPI-to-MCP generation.

**Python AI microservices** are the most common pattern for adding LLM capabilities to existing applications. The stack (FastAPI + LangChain + Pydantic) is well-established with extensive documentation and community support. LangChain has 126k+ GitHub stars. FastAPI is the default choice for AI service backends.

The **Agent Skills specification** became an open standard in December 2025, adopted across 20+ tools. Skills are how teams package reusable AI workflows — they're the "playbook" layer that makes MCP tools actually useful in domain-specific contexts.

### 3. How can OpenAPI tags enable MCP tool grouping?

OpenAPI specs support `tags` on each operation — a way to categorize endpoints into logical groups. When you generate an MCP server with `FastMCP.from_openapi()`, these tags propagate into the tool metadata.

Users filter at startup with the `--tag` flag:

```bash
# All 8 tools (default):
python server_from_spec.py

# Just case management (3 tools):
python server_from_spec.py --tag cases

# Cases + customers (5 tools):
python server_from_spec.py --tag cases --tag customers
```

**Why this matters with 50+ endpoints:** Loading all tools overwhelms the LLM's context window and degrades response quality. Tag filtering lets users load only what they need. A support agent integration loads `cases` + `customers` + `knowledge`. A monitoring bot loads just `internal`. Same Docker image, same spec, different tool sets.

The `mock_openapi_spec.json` in `01-mcp-server/` demonstrates this with 4 tag groups across 8 operations. The `filter_spec_by_tags()` function in `server_from_spec.py` shows the implementation.

### 4. MCP + Skills interplay, and local vs. remote MCP

**MCP provides tools. Skills provide playbooks.**

An MCP server exposes tools — discrete functions the LLM can invoke (e.g., "get a case", "search articles"). But tools alone don't encode *how* to use them for your domain. A skill fills that gap: it tells the LLM which tools to use, in what order, with what business rules, and how to format the output.

```
Skills ──instruct──▶ LLM ──invokes──▶ MCP Tools ──call──▶ Rails API
```

Skills reference MCP tools by their fully qualified name (`mcp__acme-platform__getCase`). The `02-skills/` module has four demo skills showing how this works in practice.

**Local distributable vs. hosted remote:**

| Aspect | Local (distributable Docker image) | Remote (hosted MCP server) |
|--------|-----------------------------------|-----------------------------|
| Transport | stdio (stdin/stdout) | Streamable HTTP (HTTPS) |
| Auth | User's API token as env var | OAuth 2.1 / API key headers |
| Runs on | User's machine | Your infrastructure |
| Scaling | One user per process | Multi-tenant, load-balanced |
| Distribution | Docker image on registry | URL in IDE config |
| Tools | Same | Same |
| Skills | Same | Same |

**Start with local distributable.** It requires zero infrastructure, is how most MCP servers are distributed today, and lets you validate which tools and skills users actually need. The Docker image you build now works for both — you just switch the entrypoint command from stdio to streamable-http when you're ready to host.

### 5. What next-step complexities justify the Python microservice?

The first features (chat proxy, search, extraction) could technically be implemented as a Ruby gem calling OpenAI directly. Here's what makes that approach fall apart quickly:

**Conversation memory** — Multi-turn conversations need server-side state management. You need to store conversation history, manage context windows (summarize old messages when the conversation exceeds token limits), and handle session lifecycle. This is LLM-specific infrastructure that doesn't belong in your Rails data model.

**RAG with vector stores** — When keyword search isn't good enough, you need embedding computation and vector similarity search. The libraries (LangChain, llama-index, chromadb, pgvector bindings) are Python-native. Ruby equivalents either don't exist or trail by months.

**Multi-step agents** — Complex tasks require orchestrating multiple LLM calls: research → draft → review → finalize. LangGraph models these as state machines with checkpointing — if a step fails, the agent resumes from the last checkpoint rather than starting over. This framework doesn't exist in Ruby.

**User-authorized write operations** — When agents need to act on behalf of users (update cases, send replies), you need delegated credentials, per-action permission checks, and audit logging. This is a security-critical boundary that warrants its own service with its own deployment and monitoring.

**Evaluation and quality control** — The AI team needs to benchmark models, A/B test prompts, and track quality metrics. The intelligence service is where this infrastructure lives — you can't run LLM evaluations from inside Rails without pulling in the entire Python ML stack.

Each of these is a natural extension of the FastAPI service in `03-intelligence-service/`. Each would be painful to bolt onto Rails. The service boundary pays for itself at Phase 2 (memory or RAG), and is essential by Phase 3 (agents).

**How to explain this to your team:** "We're building a Python service because that's where the AI tools live. The first features are simple by design — we're learning the patterns and building the foundation. But look at what comes next: conversation memory, semantic search, multi-step agents. Each of those is trivial to add to our Python service and would be a major project to build in Rails. We're investing in the architecture now so we can move fast later."

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker (for MCP server distribution demo)
- API keys for OpenAI and/or Google Gemini (only needed for intelligence service endpoints that call LLMs)

### Quick Start

```bash
# MCP Server demo:
cd 01-mcp-server
uv sync
python server_from_spec.py           # Start with all tools
python server_from_spec.py --tag cases  # Start with just case tools

# Intelligence Service demo:
cd 03-intelligence-service
uv sync
export OPENAI_API_KEY="sk-..."       # Needed for chat + extraction
uv run uvicorn app.main:app --reload --port 8100

# Test endpoints:
curl http://localhost:8100/health
curl -X POST http://localhost:8100/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "authentication"}'
```

Each module's README has detailed setup and testing instructions.
