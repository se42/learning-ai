"""
LEVEL 3 — LangGraph
=====================

The same task expressed as a declarative state machine.

LangGraph's mental model:
  - State:  a typed dict that flows through every node
  - Nodes:  Python functions that transform state and return partial updates
  - Edges:  transitions between nodes, fixed or conditional
  - The framework owns the tool loop; you describe structure, not mechanics

TWO APPROACHES SHOWN:
  A) create_react_agent() — one-liner; the recommended starting point
  B) Explicit StateGraph  — what A builds internally; shows the actual structure

TRADEOFFS:
  + Declarative graph is easier to reason about for complex, branching flows
  + Built-in checkpointing: persistent memory across sessions, process restarts
  + Human-in-the-loop: pause before any node, inject human feedback, resume
  + LangSmith: every node input/output/state is automatically traced (huge for debugging)
  + Model-agnostic: swap ChatAnthropic for ChatOpenAI with one line change
  + Parallel tool calls handled automatically by ToolNode
  - More indirection: ToolNode, add_messages reducer, and conditional edges are "magic"
  - LangChain ecosystem dependency is large (~150k LOC); version pinning matters
  - Graph structure adds conceptual overhead for simple, linear flows
  - Error messages from deep inside the graph can be harder to trace than a plain traceback

WHEN THE FRAMEWORK EARNS ITS KEEP:
  The raw SDK loop is fine for linear sequences. LangGraph pays off when you add:
    - Checkpointed memory (SqliteSaver, PostgresSaver)
    - Human approval before tool execution (interrupt_before=["tools"])
    - Sub-agents routing to each other (supervisor pattern)
    - Background jobs and webhook delivery (LangGraph Platform)
"""

from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool as lc_tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from tools import search as _search, save_recommendation as _save_rec

MODEL = "claude-haiku-4-5-20251001"

QUERY = (
    "Research FastAPI vs Flask for a new microservice we're building. "
    "Look up both options and the comparison, then save your recommendation to a file."
)


# ── Tools (LangChain wraps callables with @tool decorator) ──────────────────
# The @lc_tool decorator reads the function signature and docstring to produce
# the tool schema automatically — no manual JSON Schema required.

@lc_tool
def search(topic: str) -> str:
    """Look up information about a technology or topic."""
    return _search(topic)


@lc_tool
def save_recommendation(title: str, body: str) -> str:
    """Save a recommendation or decision to a file for the user to review."""
    return _save_rec(title, body)


tools = [search, save_recommendation]


# ═══════════════════════════════════════════════════════════════════════════════
# APPROACH A — create_react_agent (one-liner, recommended starting point)
# ═══════════════════════════════════════════════════════════════════════════════

def run_prebuilt(user_message: str, thread_id: str = "demo-a") -> str:
    """
    The simplest LangGraph agent.

    create_react_agent builds the full state machine internally:
      entry → agent node → conditional edge → tool node → agent node → ...

    thread_id enables persistent memory: the same thread_id will recall
    all prior messages via the checkpointer, even across process restarts
    (if you swap MemorySaver for SqliteSaver or PostgresSaver).
    """
    llm = ChatAnthropic(model=MODEL)
    memory = MemorySaver()  # swap for SqliteSaver(":memory:") or PostgresSaver for production

    agent = create_react_agent(llm, tools=tools, checkpointer=memory)
    config = {"configurable": {"thread_id": thread_id}}

    print(f"\n[L3A] User: {user_message[:80]}...")
    result = agent.invoke({"messages": [("user", user_message)]}, config)

    # The full message history is in result["messages"]:
    #   HumanMessage → AIMessage (tool_calls) → ToolMessage → AIMessage (final)
    # Each message is a structured LangChain object, not a raw dict.
    print(f"[L3A] Graph produced {len(result['messages'])} messages total.")
    print("[L3A] Done.\n")
    return result["messages"][-1].content


# ═══════════════════════════════════════════════════════════════════════════════
# APPROACH B — Explicit StateGraph (what create_react_agent builds for you)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """
    The state that flows through every node in the graph.

    Annotated[list, add_messages] is a LangGraph *reducer*:
    it appends new messages rather than replacing the list.
    Without a reducer, every node that returns {"messages": [...]}
    would overwrite the full history. This is the most common LangGraph footgun.
    """
    messages: Annotated[list, add_messages]


def build_explicit_graph():
    """
    Build the ReAct agent graph explicitly.
    This is structurally identical to what create_react_agent produces.
    Read this to understand what's happening inside Approach A.
    """
    llm = ChatAnthropic(model=MODEL).bind_tools(tools)
    tool_node = ToolNode(tools)  # auto-dispatches tool calls, formats results

    def call_model(state: AgentState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}  # reducer appends this; does not replace history

    def should_continue(state: AgentState) -> str:
        """Conditional edge: route to tools or finish."""
        last = state["messages"][-1]
        return "tools" if last.tool_calls else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")  # always return to agent after tools

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


def run_explicit(user_message: str, thread_id: str = "demo-b") -> str:
    app = build_explicit_graph()
    config = {"configurable": {"thread_id": thread_id}}

    print(f"\n[L3B] User: {user_message[:80]}...")
    result = app.invoke({"messages": [("user", user_message)]}, config)
    print(f"[L3B] Graph produced {len(result['messages'])} messages total.")
    print("[L3B] Done.\n")
    return result["messages"][-1].content


if __name__ == "__main__":
    print("═" * 60)
    print("Approach A: create_react_agent")
    print("═" * 60)
    answer_a = run_prebuilt(QUERY, thread_id="run-a")
    print(f"Answer:\n{answer_a}")

    # Demonstrate persistent memory: follow-up uses the same thread_id
    print("\n── Follow-up (thread_id='run-a' recalls previous conversation) ──")
    follow_up = run_prebuilt(
        "Given that recommendation, what's the main risk we should watch out for?",
        thread_id="run-a",
    )
    print(f"Follow-up answer:\n{follow_up}")

    print("\n" + "═" * 60)
    print("Approach B: Explicit StateGraph (same logic, visible structure)")
    print("═" * 60)
    answer_b = run_explicit(QUERY, thread_id="run-b")
    print(f"Answer:\n{answer_b}")
