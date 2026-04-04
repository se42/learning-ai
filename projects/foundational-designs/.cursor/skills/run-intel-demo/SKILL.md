---
name: run-intel-demo
description: Start and test the intelligence service demo from 03-intelligence-service. Sets up dependencies, starts FastAPI, and runs verification curl commands.
allowed-tools:
  - Bash
---

# Run Intelligence Service Demo

Start the intelligence microservice for testing and development.

## Steps

1. Install dependencies:
```bash
cd 03-intelligence-service && uv sync
```

2. Start the service:
```bash
cd 03-intelligence-service && uv run uvicorn app.main:app --reload --port 8100
```

## Quick Verification (run in another terminal)

These commands test each endpoint:

```bash
# Health check (no API key needed):
curl -s http://localhost:8100/health | python3 -m json.tool

# Search (no API key needed — uses mock data):
curl -s -X POST http://localhost:8100/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "authentication", "max_results": 3}' | python3 -m json.tool

# Chat (needs OPENAI_API_KEY):
curl -s -X POST http://localhost:8100/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}' | python3 -m json.tool

# Extraction (needs OPENAI_API_KEY):
curl -s -X POST http://localhost:8100/api/extract \
  -H 'Content-Type: application/json' \
  -d '{"text": "Contact John at john@test.com or 555-1234", "schema_hint": "name, email, phone"}' | python3 -m json.tool
```

## Notes

- The search endpoint works without any API keys (uses local mock data)
- Chat and extraction endpoints require `OPENAI_API_KEY` to be set
- FastAPI auto-generates Swagger docs at http://localhost:8100/docs
