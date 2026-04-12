# Prefab + FastMCP demo

Interactive incident triage demo using **FastMCP** and **Prefab UI**. The agent calls a tool; the human reviews incidents in a rich UI rendered inside Cursor; decisions flow back into chat via `SendMessage` for the agent to act on.

Dependencies live in the **repo root** [`pyproject.toml`](../../pyproject.toml) (`fastmcp[apps]`, which pulls in `prefab-ui`).

## Tools

All tools are registered on a single flat `FastMCP` server via `@mcp.tool()`.

| Tool | What it does |
| ---- | ------------ |
| `incident_triage` | `app=True` entry point. Opens an interactive triage board with 5 fake incidents. Each row has **Investigate** and **Dismiss** buttons. |
| `triage_incident` | Records a decision server-side; returns updated incident list so the UI re-renders badges. Called by the UI buttons via `CallTool`. |
| `submit_triage` | Builds a summary of all decisions; the Submit button chains this into `SendMessage` so the summary appears in chat as if the user typed it. |
| `get_triage_summary` | Text summary of current decisions; callable by the agent after the user submits. |
| `greet` | Minimal hello-world card. |

## Human-in-the-loop flow

```
You (chat):       "Give me an ops report"
        |
Agent:             calls incident_triage()
        |
Cursor:            renders Prefab UI in chat — incident list with buttons
        |
You (in the UI):   click Investigate / Dismiss per incident
        |               each click -> CallTool(triage_incident) -> server records decision -> UI updates
        |
You (in the UI):   click "Submit Triage to Chat"
        |               CallTool(submit_triage) -> SendMessage(result)
        |
Back in chat:      "Here are my triage decisions: Investigate: INC-101, INC-104. Dismiss: INC-102, INC-105."
        |
Agent:             receives your decisions as a chat message and can proceed
                   (e.g. call get_triage_summary, open tickets, run further tools)
```

The key pieces:

- **`CallTool`** on each button calls a backend tool through MCP, and `SetState` + `RESULT` re-renders the UI with updated decision badges.
- **`SendMessage`** on the Submit button injects a message into the conversation as if you typed it. This closes the loop: the agent sees your structured decisions and can act on them.

## Architecture note: flat server, not FastMCPApp

`FastMCPApp` offers a nice separation of `@app.ui()` entry points from `@app.tool()` UI-only backends (hidden from the model's tool list). However, as of fastmcp 3.2.3 / Cursor 3.0.16, `@app.tool()` backend tools registered through a `FastMCPApp` provider are **not routable** via the parent server's `call_tool` — the host can't find them when the iframe fires `CallTool`. Registering everything on one flat `@mcp.tool()` server works reliably.

## MCP Apps are for tool results, not chat styling

Prefab does **not** theme the assistant's streamed markdown. It attaches **rich interactive UI to MCP tool results** in hosts that implement the [MCP Apps extension](https://modelcontextprotocol.io/extensions/apps/overview). Cursor 2.6+ renders these as sandboxed iframes in chat.

## Try it in a browser (dev preview)

From the **repository root**:

```bash
uv run fastmcp dev apps projects/prefab-demo/app.py
```

This opens a local dev UI on port **8080** where you can pick tools and see the rendered views. `SendMessage` targets the host conversation, so in the dev preview it succeeds silently — a toast confirms it fired.

## Cursor setup (stdio + `uv run`)

Create or edit `.cursor/mcp.json` at the **repo root**:

```json
{
  "mcpServers": {
    "prefab-demo": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--project",
        "${workspaceFolder}",
        "python",
        "${workspaceFolder}/projects/prefab-demo/app.py"
      ]
    }
  }
}
```

`${workspaceFolder}` resolves to the directory containing `.cursor/mcp.json`. If `uv` isn't on Cursor's PATH, use the full path from `which uv`.

**Sanity check in a terminal** (from repo root):

```bash
uv run --project . python projects/prefab-demo/app.py
```

## Files

| File     | Role |
| -------- | ---- |
| `app.py` | FastMCP server: interactive incident triage + standalone `greet` tool |
