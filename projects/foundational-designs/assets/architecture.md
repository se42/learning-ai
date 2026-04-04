# Architecture Overview

Two independent pathways for adding AI capabilities to the Rails monolith.

## System Diagram

```
                          ┌──────────────────────────────────────────────────┐
                          │              USER'S MACHINE (IDE)               │
                          │                                                  │
                          │  ┌────────────┐     ┌─────────────────────────┐ │
                          │  │            │     │ MCP Server (Docker/uv)  │ │
                          │  │  Cursor /  │────▶│                         │ │
                          │  │  Windsurf /│ MCP │  Auto-generated tools   │ │
                          │  │  Claude    │proto│  + Curated tools        │ │
                          │  │  Desktop   │col  │                         │ │
                          │  │            │◀────│  Auth: user's API token │ │
                          │  │  + Skills  │     │  Transport: stdio       │ │
                          │  │  (SKILL.md)│     └───────────┬─────────────┘ │
                          │  └────────────┘                 │               │
                          └─────────────────────────────────┼───────────────┘
                                                            │
                                                            │ HTTPS (Bearer token)
                                                            │ User's existing API calls
                                                            ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                            YOUR INFRASTRUCTURE                                │
│                                                                                │
│  ┌───────────────────────────┐         HTTP/JSON         ┌──────────────────┐ │
│  │                           │                           │                  │ │
│  │     Rails Monolith        │  POST /api/chat           │  Intelligence    │ │
│  │                           │  POST /api/search         │  Service         │ │
│  │  - 50 API endpoints       │  POST /api/extract        │  (FastAPI)       │ │
│  │  - OpenAPI spec (v1-v3)   │─────────────────────────▶ │                  │ │
│  │  - Existing auth system   │                           │  Model routing   │ │
│  │  - Business logic         │  ◀─────────────────────── │  LLM calls       │ │
│  │                           │    {content, model_used}  │  Structured I/O  │ │
│  │                           │                           │                  │ │
│  └───────────────────────────┘                           └────────┬─────────┘ │
│                                                                   │           │
└───────────────────────────────────────────────────────────────────┼───────────┘
                                                                    │
                                                                    │ API calls
                                                                    ▼
                                                          ┌──────────────────┐
                                                          │  LLM Providers   │
                                                          │  ──────────────  │
                                                          │  OpenAI (GPT-4o) │
                                                          │  Google (Gemini) │
                                                          │  (Anthropic)     │
                                                          └──────────────────┘
```

## Two Pathways, Different Audiences

```
┌─────────────────────────────────────────┬─────────────────────────────────────────┐
│  PATHWAY 1: Distributable MCP Server    │  PATHWAY 2: Intelligence Microservice   │
│                                         │                                         │
│  Audience: Your users (developers)      │  Audience: Your Rails app (internal)    │
│  Runs on: User's machine                │  Runs on: Your infrastructure           │
│  Install: Docker image or uvx           │  Auth: None needed (internal network)   │
│  Auth: User's own API token             │  Transport: HTTP/JSON                   │
│  Transport: stdio (local) or HTTP       │  LLM: Service-controlled (you choose)   │
│  LLM: User's own (their IDE)            │                                         │
│                                         │                                         │
│  Delivers:                              │  Delivers:                              │
│  - API tools in the IDE                 │  - Chat proxy with streaming            │
│  - Skills for common workflows          │  - Document search                      │
│  - Tag-filtered tool groups             │  - Structured data extraction           │
│                                         │                                         │
│  Grows into:                            │  Grows into:                            │
│  - Hosted/remote MCP server             │  - Conversation memory                  │
│  - OAuth 2.1 multi-tenant auth          │  - RAG with vector stores               │
│  - Custom agentic tools                 │  - Multi-step agents                    │
│                                         │  - User-authorized operations           │
└─────────────────────────────────────────┴─────────────────────────────────────────┘
```

## Data Flow

### Pathway 1: MCP Server (user-side)

```
1. User asks LLM: "Look up case 1024"
2. LLM matches skill → loads case-lookup SKILL.md
3. Skill instructs LLM to use getCase + getCustomer tools
4. LLM calls MCP tools → MCP server calls Rails API (user's token)
5. Rails API returns data → MCP server returns to LLM
6. LLM follows skill instructions → formats response for user
```

### Pathway 2: Intelligence Service (server-side)

```
1. Rails app needs to extract contact info from a support email
2. Rails POSTs to /api/extract with text + schema_hint
3. Intelligence service looks up feature config → selects gpt-4o-mini
4. Service calls OpenAI → gets structured JSON back
5. Pydantic validates the response
6. Service returns clean JSON to Rails → Rails creates Contact record
```

## Key: Where Skills Fit

Skills are a **client-side** concept. They live in the user's IDE and instruct the LLM on how to use MCP tools effectively. They do not interact with the intelligence service.

```
Skills ──instruct──▶ LLM ──invokes──▶ MCP Tools ──call──▶ Rails API
                                                           (existing endpoints)

Rails App ──calls──▶ Intelligence Service ──calls──▶ LLM Providers
                     (new endpoints)                  (OpenAI, Gemini)
```

These are two independent systems that happen to serve the same Rails application from different angles.
