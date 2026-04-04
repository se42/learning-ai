# Intelligence Service — AI Microservice for Rails

A FastAPI service that gives your Rails monolith AI capabilities over plain HTTP.
Rails says "do X"; this service decides which LLM handles it and how.

---

## Why a Separate Service?

Three reasons justify running a separate Python service instead of embedding AI
directly in Rails:

**1. The Python ecosystem is where AI lives.** LangChain, FastAPI, and every
major LLM SDK are Python-first. Ruby ports exist but trail by months, lack
features, and have smaller communities. A Python service gives you access to
every new model and technique on day one.

**2. Keeping LLMs outside the API boundary is a security win.** The intelligence
service never has direct database access. It receives text, processes it through
an LLM, and returns structured results. Your API keys for OpenAI, Gemini, and
other providers live in this service's environment — not scattered across your
Rails codebase. If this service is compromised, the attacker gets LLM access,
not your production database.

**3. The AI team iterates independently.** Model swaps, prompt tuning, and new
features ship without touching the Rails release cycle. The AI team deploys
multiple times a day; the Rails team deploys weekly. Different cadences,
different concerns, separate services.

**"Isn't this overkill?"** For a single LLM proxy call, yes — a Ruby gem would
suffice. But you are building toward conversation memory, RAG pipelines,
multi-step agents, and tool-using workflows. You will hit the limits of a
Rails-embedded approach within months. The service boundary pays for itself the
moment you need to maintain conversation state or orchestrate multi-step LLM
workflows.

---

## Architecture

The Rails app communicates with this service over HTTP. Simple POST requests
with JSON bodies, JSON responses back.

```
Rails App                        Intelligence Service
-----------                      --------------------
POST /api/chat            ->     Receives request
  {messages: [...]}              Looks up feature config (config.py)
                                 Selects model (llm_factory.py)
                                 Calls LLM provider (OpenAI, Gemini, etc.)
  <- {content: "...",            Returns response
      model_used: "gpt-4o"}
```

The critical design decision: **Rails never specifies a model.** It sends a
capability request ("do chat", "do extraction") and a `feature` field. The
intelligence service resolves the model from its feature-to-model configuration
map. This means the AI team can swap GPT-4o for Gemini 2.5 Pro, change
temperatures, or switch providers entirely — without touching Rails code and
without a Rails deploy.

The Rails side is a thin HTTP client. Something like:

```ruby
# app/clients/intelligence_client.rb
class IntelligenceClient
  BASE_URL = ENV.fetch("INTELLIGENCE_SERVICE_URL", "http://localhost:8000")

  def self.chat(messages:)
    response = HTTParty.post("#{BASE_URL}/api/chat",
      body: { messages: messages }.to_json,
      headers: { "Content-Type" => "application/json" }
    )
    JSON.parse(response.body)
  end

  def self.extract(text:, schema_hint:)
    response = HTTParty.post("#{BASE_URL}/api/extract",
      body: { text: text, schema_hint: schema_hint }.to_json,
      headers: { "Content-Type" => "application/json" }
    )
    JSON.parse(response.body)
  end
end
```

That client never changes when models change. That is the value of the boundary.

---

## Feature-to-Model Mapping

The architectural keystone is `app/config.py`. It defines a `FEATURE_MODEL_MAP`
that routes each feature to a specific provider, model, temperature, and token
limit:

| Feature      | Provider     | Model           | Temperature | Why                                                    |
|-------------|-------------|-----------------|-------------|--------------------------------------------------------|
| `chat`       | openai       | gpt-4o          | 0.7         | Conversational quality matters; higher temp = creative  |
| `search`     | google-genai | gemini-2.0-flash | 0.1         | Speed matters for search reranking; low temp = consistent |
| `extraction` | openai       | gpt-4o-mini     | 0.0         | Constrained task; cheap model works; zero temp = deterministic |

Each choice is deliberate:

- **Chat uses the strongest model** because conversation quality is
  user-facing and directly affects perception of the product.
- **Search uses the fastest model** because users are waiting for results
  and the task (reranking documents) is simpler than open conversation.
- **Extraction uses the cheapest model** because pulling structured fields
  from text is a constrained task that smaller models handle well, and
  temperature 0.0 ensures the same input always produces the same output.

To change a model, edit one line in `config.py` and restart the service:

```python
# Before: using GPT-4o for chat
"chat": ModelConfig(provider="openai", model="gpt-4o", temperature=0.7, max_tokens=2048),

# After: switched to Gemini for chat
"chat": ModelConfig(provider="google-genai", model="gemini-2.5-pro", temperature=0.7, max_tokens=2048),
```

No Rails changes. No API contract changes. No client changes.

---

## The Chat Proxy

**Files:** `app/routers/chat.py`, `app/services/llm_factory.py`

Two endpoints serve chat: a synchronous endpoint and a streaming endpoint.

### Synchronous: POST /api/chat

Send a conversation, get the complete response:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant for Acme Corp."},
      {"role": "user", "content": "How do I reset my API key?"}
    ]
  }'
```

Response:
```json
{
  "content": "To reset your API key, go to Settings > API Keys in your dashboard...",
  "model_used": "openai/gpt-4o",
  "usage": {"input_tokens": 32, "output_tokens": 85}
}
```

Good for background jobs, internal tools, and anywhere you do not need
incremental display.

### Streaming: POST /api/chat/stream

Same input, but tokens stream back as Server-Sent Events (SSE):

```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain webhooks in two sentences."}
    ]
  }'
```

Response (event stream):
```
data: {"token": "Web"}
data: {"token": "hooks"}
data: {"token": " let"}
data: {"token": " your"}
data: {"token": " system"}
...
data: {"done": true, "model_used": "openai/gpt-4o"}
```

**Why streaming matters:** Without it, the user stares at a spinner for 5-15
seconds while the LLM generates the full response. With SSE, the first token
arrives in ~200ms and tokens appear as they are generated. The UI feels alive.

SSE is a simple protocol — the server sends `data: ...\n\n` lines over a
long-lived HTTP connection. Most HTTP clients support it. In Rails, you can
consume it with Faraday's streaming adapter or Net::HTTP's `read_body` block.

---

## Document Search

**Files:** `app/routers/search.py`, `app/services/search_service.py`,
`sample_data/docs.json`

The search endpoint takes a natural language query and returns relevant
documents from a local corpus:

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to authenticate API requests", "max_results": 3}'
```

Response:
```json
{
  "results": [
    {
      "title": "Authentication and API Tokens",
      "content": "Acme uses Bearer token authentication for all API requests...",
      "score": 0.1823,
      "article_id": "art-002"
    },
    ...
  ],
  "query": "how to authenticate API requests",
  "model_used": "keyword-search"
}
```

The current implementation uses TF-IDF keyword matching — no LLM needed, no
external dependencies. It tokenizes the query and documents, computes term
frequency-inverse document frequency scores, and returns the top matches.

This is deliberately simple. The upgrade path does not change the API contract:

1. **Keyword search** (this demo) — no dependencies, works offline, good enough
   for small corpora.
2. **Embedding search** — use an LLM's embeddings API to compute semantic
   similarity. "How do I log in?" matches "Authentication and API Tokens" even
   though the words are different.
3. **Vector store** — pgvector, Pinecone, or Weaviate for production-scale RAG
   with millions of documents.

The key insight: `POST /api/search` returns `SearchResponse` regardless of which
implementation sits behind it. The Rails client code does not change when you
upgrade from keywords to vectors. That is the value of the service boundary.

---

## Structured Extraction

**Files:** `app/routers/extract.py`, `app/services/extraction_service.py`

This is often the first feature that makes stakeholders say "I get it." Send
unstructured text plus a description of what to extract; get back structured
JSON.

```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hi, I am Jane Smith from Globex Corp. My email is jane@globex.com and you can reach me at 555-0142. We are having issues with our billing integration and need urgent help.",
    "schema_hint": "Extract contact info and support request: name, email, phone, company, issue_summary, urgency (low/medium/high)"
  }'
```

Response:
```json
{
  "extracted": {
    "name": "Jane Smith",
    "email": "jane@globex.com",
    "phone": "555-0142",
    "company": "Globex Corp",
    "issue_summary": "Issues with billing integration",
    "urgency": "high"
  },
  "model_used": "openai/gpt-4o-mini"
}
```

The `schema_hint` is natural language, not a formal schema. This means
non-technical stakeholders can define extraction templates:

- `"Extract contact information: name, email, phone"`
- `"Extract action items: description, assignee, due_date"`
- `"Classify this support case: category, urgency (low/medium/high), summary"`
- `"Parse this invoice: vendor, amount, currency, date, line_items"`

The LLM does the understanding (figuring out which parts of the text map to
which fields). The service parses and returns the JSON. The Rails app gets clean
structured data it can store, display, and act on.

In Rails, the integration looks like:

```ruby
result = IntelligenceClient.extract(
  text: support_email.body,
  schema_hint: "contact info: name, email, phone, company"
)
contact = Contact.new(result["extracted"])
```

---

## Provider-Agnostic Design

**File:** `app/services/llm_factory.py`

The factory uses LangChain's `init_chat_model()` — a universal constructor that
takes a provider name and model name and returns the right client class
(`ChatOpenAI`, `ChatGoogleGenerativeAI`, `ChatAnthropic`, etc.) already
configured.

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    model="gpt-4o",
    model_provider="openai",
    temperature=0.7,
    max_tokens=2048,
)
```

The calling code receives a `BaseChatModel` and never knows which provider is
behind it. `model.ainvoke(messages)` works the same whether the model is OpenAI,
Gemini, or Anthropic.

This matters because:

- **Provider outages happen.** When OpenAI is down, change one line in config
  and route to Gemini.
- **Pricing changes.** When a cheaper model launches, swap it in for cost
  savings without any code changes.
- **New models launch weekly.** Testing a new model is a config change, not a
  refactor.

Adding a new provider requires:
1. `pip install langchain-{provider}`
2. Set the API key environment variable
3. Update the feature config in `config.py`

No code changes. No new abstractions. The factory and `init_chat_model` handle
the rest.

---

## The Graduation Path

This demo is Phase 1 — stateless LLM proxy, keyword search, structured
extraction. Here is what comes next and why each phase is a natural extension of
this service:

### Conversation Memory

**Problem:** The chat endpoint is stateless. Each request is independent. For
multi-turn conversations, Rails must send the entire conversation history every
time.

**Solution:** Add a session store (Redis or Postgres). The Rails app sends a
`session_id`; this service maintains the conversation history. Conversations
persist across requests. The service manages context windows (trimming old
messages when the conversation exceeds the model's token limit).

This is extremely awkward to do in Rails without pulling in LLM infrastructure.
The intelligence service already has LangChain, which has built-in memory
abstractions.

### RAG with Vector Stores

**Problem:** The keyword search works for small corpora but cannot handle
semantic similarity ("How do I log in?" should match "Authentication and API
Tokens").

**Solution:** Add pgvector (if you already run Postgres) or Pinecone. Ingest
your documents, embed them using an embedding model, and search by vector
similarity. The search endpoint evolves from keyword to vector — same API,
dramatically better results.

The service already has the search contract (`POST /api/search` returns
`SearchResponse`). The Rails client does not change.

### Multi-Step Agents

**Problem:** Some tasks require multiple LLM calls: research, draft, review,
refine. A single request-response cycle is not enough.

**Solution:** Add LangGraph. Define workflows as state machines where each node
is an LLM call or tool invocation. The agent can call tools (including your own
Rails API via MCP), maintain state across steps, and recover from failures with
checkpointing.

Example: a "draft response" agent that reads the support case, searches the
knowledge base, drafts a reply, self-reviews for accuracy, and returns the final
draft. This is 4-5 LLM calls orchestrated as a graph — trivial with LangGraph,
painful to build from scratch.

### User-Authorized Operations

**Problem:** The intelligence service needs to perform actions on behalf of
users (update a case, send a reply) but should not have blanket write access.

**Solution:** Delegated auth. The Rails app passes a scoped token with each
request. The intelligence service uses that token to call back into the Rails
API with the user's permissions. Every action is auditable and scoped to what
the user is allowed to do.

Each of these phases is a natural extension of this service. Each would be
extremely awkward bolted onto Rails. The architectural investment in a separate
service pays for itself starting at Phase 2.

---

## Running the Demo

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install Dependencies

```bash
cd 03-intelligence-service
uv sync
```

Or with pip:
```bash
pip install -e .
```

### Set API Keys

For the chat and extraction endpoints (which call real LLMs):

```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

The search and health endpoints work without API keys (they use local data).

### Start the Service

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### Test the Endpoints

**Health check** (no API key needed):
```bash
curl http://localhost:8000/health
```

**Search** (no API key needed):
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication tokens", "max_results": 3}'
```

**Chat** (requires OPENAI_API_KEY):
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is a webhook?"}
    ]
  }'
```

**Streaming chat** (requires OPENAI_API_KEY):
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain API rate limiting in three sentences."}
    ]
  }'
```

**Extraction** (requires OPENAI_API_KEY):
```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Meeting notes: John will update the dashboard by Friday. Sarah needs to review the API docs before next Tuesday. Budget approval pending from Mike.",
    "schema_hint": "Extract action items: person, task, deadline"
  }'
```

**Interactive API docs** (built into FastAPI):
```
http://localhost:8000/docs
```

### What Needs API Keys vs. What Does Not

| Endpoint             | Needs API Key? | Why                                    |
|---------------------|---------------|----------------------------------------|
| `GET /health`        | No             | Returns config info only               |
| `POST /api/search`   | No             | Uses local keyword search              |
| `POST /api/chat`     | Yes (OpenAI)   | Calls GPT-4o                          |
| `POST /api/chat/stream` | Yes (OpenAI) | Calls GPT-4o with streaming           |
| `POST /api/extract`  | Yes (OpenAI)   | Calls GPT-4o-mini                     |
