"""
LEVEL 2 — Anthropic SDK with Structure
========================================

The same agentic loop, organized into a reusable Agent class.
Still only depends on `anthropic` — no LangChain, no new frameworks.

This level answers the question: "How far can you get with raw SDK before
you actually need a framework?"

WHAT THIS ADDS OVER LEVEL 1:
  - Streaming: text appears word-by-word, not all at once after tool calls
  - Type-safe block handling: isinstance(block, ToolUseBlock) vs string comparison
  - Persistent conversation history: agent remembers previous turns
  - Tool registration via decorator: tools are attached to the agent, not scattered globally
  - Reusable class: multiple agents can exist simultaneously with different tools/personas

TRADEOFFS:
  + Still fully within the Anthropic SDK — no new dependencies
  + Streaming is critical for production UX; this is where you first need it
  + Multi-turn memory with zero infrastructure (in-process list)
  + The decorator pattern makes tool registration self-documenting
  - More code upfront for a single-shot query (the class pays off at scale)
  - Conversation history grows unbounded — you need to prune or summarize in production
  - Still Anthropic-specific message format; no multi-model portability
  - No persistence across process restarts — history is in RAM

OBSERVATION:
  At this level you're essentially building LangGraph's internals by hand.
  The Agent class below is ~100 lines. LangGraph's StateGraph is ~10,000 lines,
  but it handles branching, sub-agents, checkpointing, and human-in-the-loop.
  The question is whether you need those features.
"""

import anthropic
from anthropic.types import ToolUseBlock
from typing import Callable

MODEL = "claude-haiku-4-5-20251001"


class Agent:
    """
    A stateful, streaming agent backed by the Anthropic SDK.

    Key design decisions:
    - self.history persists across calls (multi-turn memory)
    - Tools are registered via @agent.tool() decorator, keeping schema + implementation together
    - Streaming via client.messages.stream() gives real-time output
    """

    def __init__(self, system_prompt: str = "", model: str = MODEL):
        self.client = anthropic.Anthropic()
        self.model = model
        self.system_prompt = system_prompt
        self.history: list = []          # conversation persists across .chat() calls
        self._tools: dict[str, Callable] = {}
        self._tool_schemas: list[dict] = []

    def tool(self, name: str, description: str, schema: dict):
        """
        Decorator to register a function as an agent tool.

        Keeps the tool schema and implementation together:
            @agent.tool("search", "Look up info", {...})
            def search(topic: str) -> str:
                return ...

        The schema format is Anthropic's JSON Schema input_schema.
        """
        def decorator(fn: Callable) -> Callable:
            self._tools[name] = fn
            self._tool_schemas.append({
                "name": name,
                "description": description,
                "input_schema": schema,
            })
            return fn
        return decorator

    def chat(self, user_message: str) -> str:
        """
        Send a message and run the agentic loop to completion.

        - Streams text to stdout as it arrives (non-blocking UX)
        - Executes tool calls transparently
        - Appends everything to self.history (memory persists)
        - Returns the complete final text
        """
        self.history.append({"role": "user", "content": user_message})
        print(f"\n[L2] User: {user_message[:80]}...")

        while True:
            full_text = ""

            # Streaming: open a context manager, iterate text chunks as they arrive.
            # The model starts generating immediately; we don't wait for tool results.
            # When tool_use blocks appear, they're delivered as structured events.
            with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                tools=self._tool_schemas,
                messages=self.history,
            ) as stream:
                print("[L2] Claude: ", end="", flush=True)
                for chunk in stream.text_stream:
                    # Each chunk is a string fragment — print immediately
                    print(chunk, end="", flush=True)
                    full_text += chunk
                if full_text:
                    print()  # newline after streamed content

                # get_final_message() blocks until the stream is complete,
                # then returns the full structured response (with tool_use blocks etc.)
                final = stream.get_final_message()

            self.history.append({"role": "assistant", "content": final.content})

            if final.stop_reason == "end_turn":
                print("[L2] Done.\n")
                return full_text

            if final.stop_reason == "tool_use":
                tool_results = []
                for block in final.content:
                    # isinstance is more robust than block.type == "tool_use"
                    # because it works with type checkers and survives SDK version changes
                    if isinstance(block, ToolUseBlock):
                        print(f"[L2] Tool call: {block.name}({block.input})")
                        fn = self._tools.get(block.name)
                        if fn is None:
                            raise ValueError(f"Tool '{block.name}' not registered on this agent")
                        result = fn(**block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                self.history.append({"role": "user", "content": tool_results})
            else:
                raise RuntimeError(f"Unexpected stop_reason: {final.stop_reason}")


def build_agent() -> Agent:
    """
    Instantiate an Agent and register the demo tools.

    In production this might live in a dependency injection container,
    or tools might be loaded from config/plugins.
    """
    from tools import search, save_recommendation

    agent = Agent(system_prompt="You are a technical advisor. Use tools to research, then give clear recommendations.")

    @agent.tool(
        "search",
        "Look up information about a technology or topic.",
        {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    )
    def _search(topic: str) -> str:
        return search(topic)

    @agent.tool(
        "save_recommendation",
        "Save a recommendation or decision to a file for the user to review.",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["title", "body"],
        },
    )
    def _save(title: str, body: str) -> str:
        return save_recommendation(title, body)

    return agent


if __name__ == "__main__":
    agent = build_agent()

    agent.chat(
        "Research FastAPI vs Flask for a new microservice we're building. "
        "Look up both options and the comparison, then save your recommendation to a file."
    )

    # Demonstrate persistent memory: the agent recalls the previous conversation
    print("── Follow-up (agent remembers previous conversation) ──")
    agent.chat("Given that recommendation, what's the first thing we should do to get started?")
