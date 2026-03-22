# Agent Abstractions: Three Levels Compared

A focused demo of the same agent — a technical research assistant — built three ways. The goal is to make the tradeoffs between abstraction levels *visible in the code*, not just described in theory.

## The Task

All three agents solve the same problem: research FastAPI vs Flask, form a recommendation, and save it to a file. This exercises the two most fundamental agent capabilities: **reading** (search tool) and **acting** (save tool). The core loop runs multiple times.

## Files

| File | What it shows |
|---|---|
| `tools.py` | Shared business logic — the actual `search()` and `save_recommendation()` functions. Used by all levels. |
| `level1_raw_sdk.py` | The agentic loop written by hand using only `anthropic` |
| `level2_agent_class.py` | The same loop encapsulated in a reusable class, with streaming and multi-turn memory |
| `level3_langgraph.py` | The same loop expressed as a LangGraph state machine |
| `compare.py` | Runs all three on the same query and prints a summary table |

## How to Run

```bash
# From the repo root
uv run python projects/agent-abstractions/level1_raw_sdk.py
uv run python projects/agent-abstractions/level2_agent_class.py
uv run python projects/agent-abstractions/level3_langgraph.py

# Or all three at once with a comparison table:
uv run python projects/agent-abstractions/compare.py
```

Output files (the saved recommendations) appear in `projects/agent-abstractions/output/`.

---

## The Fundamental Concept: The Agentic Loop

All three levels implement the same loop. It's worth understanding this before anything else.

```
User message
    ↓
[Call model] ──── stop_reason == "end_turn" ──→ Return text to user
    ↑
    │            stop_reason == "tool_use"
    │                    ↓
    │            [Execute tools]
    │                    ↓
    └──────── [Append results to history]
```

The **message history** is the agent's memory. Each turn you send the full history to the model; it reads everything before responding. Tool results go back as a `user`-role message — this surprises people, but it's simply how Anthropic's protocol works: you (the environment) are providing the tool results, so you are the "user" in that turn.

Every level of abstraction is hiding some or all of this loop from you.

---

## Level 1 — Raw Anthropic SDK

**What you see:** A `while True` loop with a mutable list. That's it.

```python
messages = [{"role": "user", "content": user_message}]

while True:
    response = client.messages.create(model=..., tools=..., messages=messages)

    if response.stop_reason == "end_turn":
        return final_text

    if response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        # execute tools...
        messages.append({"role": "user", "content": tool_results})
```

**The insight:** There is no framework. The "agent" is a loop and a list. If something breaks, you know exactly where — there are no hidden layers between you and the API call.

**When this is the right choice:**
- You're building something where every millisecond of latency matters and you want to hand-optimize the loop
- Your agent flow is linear (no complex branching, no sub-agents)
- You want to avoid transitive dependencies (useful in lambda functions, containers with tight size constraints)
- You're learning — reading this code teaches you what every other level is abstracting

**The cost you're accepting:**
- You will eventually want multi-turn memory, streaming, retry logic, and logging. You'll build all of these yourself. They're not hard, but they add up.
- Switching from Anthropic to another model provider means rewriting the message format. The Anthropic dict format is not portable.

---

## Level 2 — Anthropic SDK with Structure

**What you see:** The loop is hidden inside a class. Callers just do `agent.chat("...")`.

The class adds three things the raw loop doesn't have:

1. **Streaming** — text arrives word-by-word during generation, not as one block after all tool calls resolve. This is essential for any user-facing application.

2. **Persistent history** — `self.history` accumulates across multiple `.chat()` calls. The agent remembers the conversation without any database.

3. **Tool registration** — tools are attached to the agent via a decorator, which keeps the schema and implementation next to each other and makes it easy to swap tool sets between agent instances.

**The insight:** This is the point where you're writing the infrastructure that LangChain was originally built to provide. The `Agent` class in `level2_agent_class.py` is ~100 lines. LangChain's equivalent abstractions are thousands of lines, but they handle many more edge cases.

**When this is the right choice:**
- You need streaming but don't want the full LangChain dependency tree
- Your flows are mostly linear but need multi-turn memory
- You want tight control over retry/error handling (e.g., for specific rate-limit strategies)
- Your team is Anthropic-committed and portability isn't a concern

**The cost you're accepting:**
- The `self.history` list grows unbounded — you need to prune/summarize for long conversations
- No persistence across process restarts — if the server dies, the conversation is gone
- Still no graph structure — complex "if the agent said X, do Y" routing lives in your code, not in a declarative structure

---

## Level 3 — LangGraph

**What you see:** A graph declaration. You define nodes and edges; the framework runs the loop.

```python
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")
app = graph.compile(checkpointer=memory)
```

The loop you wrote by hand in Level 1 is now expressed as two nodes and two edges. The `ToolNode` handles dispatch and result formatting. The `add_messages` reducer on state handles history management.

**The insight:** LangGraph is a bet that complex agent flows are better expressed as an explicit graph than as nested if-statements and while loops. For simple flows, this adds overhead. For complex flows (multi-agent systems, human approval steps, sub-agent routing), it pays off significantly.

**The `add_messages` footgun:** The single most common LangGraph mistake is forgetting the reducer:
```python
# Wrong — each node update REPLACES the message list
messages: list

# Right — reducer APPENDS new messages to the existing list
messages: Annotated[list, add_messages]
```
This is "magic" — behavior defined by a type annotation — which is exactly the kind of indirection that makes LangGraph harder to debug when something goes wrong.

**When this is the right choice:**
- You need persistent memory across sessions/servers (plug in `SqliteSaver` or `PostgresSaver`)
- You need human-in-the-loop approval: `graph.compile(interrupt_before=["tools"])` pauses the graph before any tool executes
- You're building multi-agent systems where agents hand off to each other
- You want LangSmith tracing — every node, edge, and state snapshot is logged automatically
- You want to swap between Claude, GPT-4, and other models without changing agent code

**The cost you're accepting:**
- LangChain is a large, fast-moving dependency. Breaking changes happen. Version pinning is essential.
- Errors from inside `ToolNode` or the graph executor produce stack traces that are harder to read than a plain Python traceback
- The `add_messages` reducer and `Annotated` type magic are concepts your team needs to understand before they can safely modify the graph
- `create_react_agent` is convenient but opaque — until you read Approach B (the explicit graph), you don't know what it's doing

---

## Tradeoffs at a Glance

| | Level 1 | Level 2 | Level 3 |
|---|---|---|---|
| **Transparency** | Maximum | High | Medium |
| **Vendor lock-in** | Anthropic only | Anthropic only | Model-agnostic |
| **Framework dependencies** | None | None | LangChain + LangGraph |
| **Streaming** | Add it yourself | Built in | Via `.astream()` |
| **Multi-turn memory** | You build it | In-process list | Checkpointer (pluggable) |
| **Persistence across restarts** | None | None | SQLite / Postgres |
| **Human-in-the-loop** | You build it | You build it | `interrupt_before` |
| **Debugging** | `print()` | `print()` | LangSmith traces |
| **Multi-agent routing** | Manual | Manual | Supervisor / swarm patterns |
| **Lines of agent code** | ~40 | ~100 | ~10 (prebuilt) / ~40 (explicit) |

---

## The Decision Question

The most important question isn't which level is "best" — it's: **how much of the loop do you want to own?**

- If your agent does one thing and does it predictably: **Level 1**. You'll understand every failure.
- If you need streaming and multi-turn memory but want to stay dependency-light: **Level 2**. You're writing 100 lines once instead of pulling in a framework.
- If you need persistence, human approval, multi-agent routing, or production observability: **Level 3**. The framework earns its weight at scale.

The other key question: **how Anthropic-committed are you?** Levels 1 and 2 are tied to Anthropic's message format. Level 3 lets you swap models with one line. If you're building something that might need to run against OpenAI, Gemini, or a local model, that portability matters.

---

## What This Demo Doesn't Cover

Things intentionally omitted to keep the focus on fundamentals:

- **MCP (Model Context Protocol)**: Anthropic's open standard for defining tools as networked services. Increasingly relevant for sharing tools across agents and vendors.
- **Prompt caching**: Critical for production cost/latency — cache static tool schemas and system prompts to save 90%+ on input tokens.
- **Extended thinking**: Claude's ability to reason step-by-step before responding (`thinking` content blocks) — useful for complex planning tasks.
- **Async**: All three levels have async variants (`async_client.messages.create`, `await app.ainvoke`). Important for serving multiple users concurrently.
- **Multi-agent patterns**: Supervisor, swarm, and hierarchical agent designs. LangGraph has first-class support; the others require manual routing logic.
