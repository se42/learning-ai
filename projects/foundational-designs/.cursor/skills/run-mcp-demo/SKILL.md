---
name: run-mcp-demo
description: Start and test the MCP server demo from 01-mcp-server. Sets up dependencies, runs the server, and verifies tool registration.
allowed-tools:
  - Bash
argument-hint: "[--tag cases] [--curated]"
---

# Run MCP Server Demo

Start the MCP server demo for testing and development.

## Steps

1. Install dependencies:
```bash
cd 01-mcp-server && uv sync
```

2. Run the server based on arguments:

If `$ARGUMENTS` contains `--curated`:
```bash
cd 01-mcp-server && uv run python server_curated.py
```

Otherwise, run the naive server (pass through any --tag flags from $ARGUMENTS):
```bash
cd 01-mcp-server && uv run python server_from_spec.py $ARGUMENTS
```

## Quick Verification

To verify without starting the interactive server, check that the spec loads
and tools register:
```bash
cd 01-mcp-server && uv run python -c "
import json
from pathlib import Path
spec = json.loads(Path('mock_openapi_spec.json').read_text())
ops = [(m, p) for p, item in spec['paths'].items() for m in ['get','post','put','patch','delete'] if m in item]
print(f'Spec loaded: {len(ops)} operations across {len(spec.get(\"tags\", []))} tag groups')
for tag in spec.get('tags', []):
    tag_ops = [f'{m.upper()} {p}' for p, item in spec['paths'].items() for m in ['get','post'] if m in item and tag['name'] in item[m].get('tags',[])]
    print(f'  {tag[\"name\"]}: {len(tag_ops)} operations')
"
```

## MCP Inspector

For interactive testing with the FastMCP dev inspector:
```bash
cd 01-mcp-server && uv run fastmcp dev server_from_spec.py
```
