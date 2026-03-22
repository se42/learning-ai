"""
LEVEL 1 — Raw Anthropic SDK
============================

The agentic loop, fully explicit. Nothing is hidden.

Architecture: a plain while-loop over a mutable messages list.
The model either responds with text (done) or requests tool calls (continue).
You own every transition.

WHAT YOU OWN:
  - The message history (a plain list of dicts — you manage it)
  - The tool dispatch logic (a manual function call)
  - The loop termination logic (checking stop_reason yourself)
  - All state — there is no framework holding anything for you

TRADEOFFS:
  + Maximum transparency — the entire agent is ~40 lines you can read top-to-bottom
  + Zero framework dependencies — just `anthropic`
  + Easy to optimize exactly where needed (caching, retry, streaming)
  + No "magic" — every decision is visible and debuggable with a print statement
  - Verbose for complex flows (parallel tools, branching, sub-agents)
  - No built-in persistence — history lives in memory, gone when the process ends
  - You reinvent production concerns from scratch (retry, logging, state serialization)
  - Anthropic message format is specific to this SDK; switching models means rewriting
"""

import anthropic
from tools import ANTHROPIC_TOOLS, TOOL_DISPATCH

MODEL = "claude-haiku-4-5-20251001"


def run_agent(user_message: str) -> str:
    """
    Run a task to completion.

    The loop:
      1. Send current messages to Claude
      2. If stop_reason == "tool_use"  → execute tools, append results, go to 1
      3. If stop_reason == "end_turn"  → return final text
    """
    client = anthropic.Anthropic()

    # The entire conversation is this list.
    # You are responsible for it — the SDK does not manage history.
    messages = [{"role": "user", "content": user_message}]

    print(f"\n[L1] User: {user_message[:80]}...")

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=ANTHROPIC_TOOLS,
            messages=messages,
        )

        # ── Claude is done ────────────────────────────────────────────────────
        if response.stop_reason == "end_turn":
            final = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            print(f"[L1] Done.\n")
            return final

        # ── Claude wants to use tools ─────────────────────────────────────────
        if response.stop_reason == "tool_use":
            # Step 1: Append Claude's full response (including tool_use blocks) to history.
            # This is required — Claude's turn must appear in history before results.
            messages.append({"role": "assistant", "content": response.content})

            # Step 2: Execute each tool and collect results.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[L1] Tool call: {block.name}({block.input})")
                    result = TOOL_DISPATCH[block.name](block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,   # must reference the request's id
                        "content": result,
                    })

            # Step 3: Return results as a "user" message.
            # This surprises people — tool results are user-role, not assistant-role.
            # It's how Anthropic's protocol works: the model "asked" for tools,
            # and "you" (the user/environment) are providing the answers.
            messages.append({"role": "user", "content": tool_results})
            # Loop — Claude will see the results and decide what to do next.

        else:
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")


if __name__ == "__main__":
    answer = run_agent(
        "Research FastAPI vs Flask for a new microservice we're building. "
        "Look up both options and the comparison, then save your recommendation to a file."
    )
    print(f"Answer:\n{answer}")
