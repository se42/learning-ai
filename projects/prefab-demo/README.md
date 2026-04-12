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

## What MCP Apps / Prefab are good for

Prefab does **not** theme the assistant's streamed markdown. It attaches **rich interactive UI to MCP tool results** in hosts that implement the [MCP Apps extension](https://modelcontextprotocol.io/extensions/apps/overview). Cursor 2.6+ renders these as sandboxed iframes in chat. The question is: when would you actually reach for this instead of just letting the model write a text answer?

**Review and triage workflows** — The incident triage demo in this project is a good example. Any time you have a list of items that need human judgment (support cases, code review findings, deploy candidates, test failures), a table with action buttons is faster and less error-prone than reading paragraphs and typing decisions back. A support engineer working through cases in their IDE could triage, approve, and dismiss directly in the chat without switching windows.

**Dashboards and monitoring** — Service health, deployment status, API latency, error rates. These are the kind of multi-row, multi-column data sets that are painful to read as JSON or prose. Prefab has sortable tables, bar/line/area/pie charts, progress bars, and metric cards. The agent fetches the data; the human reads a real dashboard instead of squinting at numbers in a chat bubble.

**Data entry and structured input** — Forms with typed fields, dropdowns, date pickers, and validation. When the agent needs structured input from you (not just a free-text reply), a form gives you labeled fields and constraints. Think: filing a bug report, creating a config entry, or submitting parameters for a batch job — all without leaving the conversation.

**Exploratory browsing** — Search boxes wired to `CallTool`, paginated tables, accordion details, tabbed views. When a tool returns a large result set (employees, inventory, log entries), the human can search, sort, and drill into rows client-side without the agent re-running the query for every follow-up.

**Approval gates and human-in-the-loop** — Buttons that call backend tools to record a decision, then `SendMessage` to feed the result back into chat. This is the pattern our demo uses: the agent opens the UI, the human makes choices, the choices re-enter the conversation as structured input for the agent's next step. Useful anywhere you want the agent to propose and the human to approve before the agent proceeds (deployments, data migrations, bulk operations).

**The common thread**: the agent calls a tool, but the **output is meant for a person** who needs to read, compare, or act on it. Text works fine for short answers; Prefab is for the cases where a real UI would save time or reduce mistakes.

## The big picture: one service, many clients

The most important thing to understand about Prefab is where it sits in your architecture. If you're running a Python-based AI microservice (FastAPI, FastMCP, or both), **that service is the single source for both agent logic and user-facing interactions**. Prefab is how the AI team owns the presentation layer for those interactions without needing a frontend team or a build pipeline.

**Same code, different transports.** A `PrefabApp` built in Python works in all of these contexts:

- **IDE via MCP** — Cursor, Claude Desktop, or ChatGPT connect to your MCP server, call a tool, and render the Prefab UI in chat. Button clicks route back through MCP (`CallTool`).
- **Web app via HTTP** — Your React frontend makes an API call (maybe proxied through Rails) to your FastAPI intelligence service. The service returns the Prefab JSON or a self-contained HTML page (`PrefabApp.html()`). Button clicks route back via HTTP (`Fetch`). The React team just embeds a container; the AI team owns everything inside it.
- **Dev preview** — `fastmcp dev apps` runs the server and opens a browser. The AI team tests interactive flows locally without an IDE, a Rails app, or any infrastructure.

The AI team writes the `PrefabApp` once. It renders in all three places.

**How the web app path actually works.** When your React frontend requests a Prefab interaction from the AI service (proxied through Rails or called directly), the service can return one of two things:

- **Self-contained HTML** (`PrefabApp.html()`) — a complete mini page bundling the component tree, state, and renderer. React drops it into an iframe via `srcdoc`. The iframe handles everything: rendering, client-side interactivity, and `Fetch` calls back to the AI service for button actions. The React app doesn't need to know anything about Prefab. This is the easiest path.
- **Raw JSON** (`PrefabApp.to_json()`) — the structured component tree (headings, tables, buttons, actions) as a plain dict. React loads the Prefab renderer library as a dependency and renders the tree directly in the DOM — no iframe, tighter integration. Or, if the frontend team wants full control, they can skip the Prefab renderer entirely and write their own code that walks the JSON tree and maps each component type to their existing design system components.

In both cases, the AI service is the source of truth for what the user sees. Rails is just a proxy. The frontend provides a container and decides how much rendering responsibility it wants to take on.

**Why this matters for teams with a separate frontend.** Without Prefab, every AI-driven interaction that needs structured input from a user requires coordination: the AI team defines the data shape, the frontend team builds a React component, both teams agree on the API contract, and it ships after a round of review. With Prefab, the AI team defines the data shape *and* the UI in the same Python codebase. The frontend team's only job is carving out a container — an iframe or a div — and saying "render whatever the intelligence service returns here." The AI team can iterate on forms, add fields, swap layouts, and ship changes without touching the React app.

**Prefab and workflow orchestration (e.g. LangGraph).** Prefab handles presentation — what the human sees and clicks on. LangGraph (or any orchestration framework with human-in-the-loop support) handles execution — what happens before and after the human weighs in. They complement each other: a LangGraph graph hits an interrupt node and pauses; your service takes the pending data, builds a Prefab UI for the human to review and approve, collects the decisions, and feeds them back to the graph as the interrupt response. The graph resumes. Prefab doesn't replace your orchestration; it gives the orchestration a real UI for the human steps.

**The presentation isn't cutting-edge, and that's fine.** Prefab's components (built on shadcn/ui) are clean and professional but won't match a custom design system. For internal tools, human-in-the-loop workflows, and "the AI team needs to ask the user something" scenarios, that's the right trade-off. If a specific customer-facing interaction eventually needs pixel-perfect branding, the frontend team can build a proper React component for that one case. But for the first wave of AI-driven interactions, Prefab lets the AI team move without waiting in the frontend queue.

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
