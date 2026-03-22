"""
Run the same query through all three levels and compare results.

Usage:
    uv run python projects/agent-abstractions/compare.py
"""

import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])  # ensure local imports work

from level1_raw_sdk import run_agent
from level2_agent_class import build_agent
from level3_langgraph import run_prebuilt

QUERY = (
    "Research FastAPI vs Flask for a new microservice we're building. "
    "Look up both options and the comparison, then save your recommendation to a file."
)

WIDTH = 64


def banner(title: str):
    print(f"\n{'═' * WIDTH}")
    print(f"  {title}")
    print("═" * WIDTH)


def main():
    print(f"Task: {QUERY}\n")

    # ── Level 1 ───────────────────────────────────────────────────────────────
    banner("LEVEL 1  Raw Anthropic SDK — manual loop")
    t0 = time.perf_counter()
    ans1 = run_agent(QUERY)
    t1 = time.perf_counter() - t0
    print(f"Answer:\n{ans1}")
    print(f"\nTime: {t1:.1f}s | Agent code: ~40 lines | Dependencies: anthropic only")

    # ── Level 2 ───────────────────────────────────────────────────────────────
    banner("LEVEL 2  Anthropic SDK + Agent class — streaming, multi-turn memory")
    agent = build_agent()
    t0 = time.perf_counter()
    agent.chat(QUERY)
    t2 = time.perf_counter() - t0
    print(f"\nTime: {t2:.1f}s | Agent code: ~100 lines | Dependencies: anthropic only")

    # Demonstrate that memory persists across calls (Level 2 feature)
    print("\n  [Multi-turn demo: asking follow-up without re-stating context]")
    agent.chat("Given that recommendation, what's the first thing we should do?")

    # ── Level 3 ───────────────────────────────────────────────────────────────
    banner("LEVEL 3  LangGraph — declarative graph, built-in checkpointing")
    t0 = time.perf_counter()
    ans3 = run_prebuilt(QUERY, thread_id="compare-run")
    t3 = time.perf_counter() - t0
    print(f"Answer:\n{ans3}")
    print(f"\nTime: {t3:.1f}s | Agent code: ~10 lines | Dependencies: langchain + langgraph")

    # ── Summary ───────────────────────────────────────────────────────────────
    banner("SUMMARY")
    rows = [
        ("", "Level 1", "Level 2", "Level 3"),
        ("Agent code", "~40 lines", "~100 lines", "~10 lines"),
        ("Dependencies", "anthropic", "anthropic", "langchain, langgraph"),
        ("Streaming", "No", "Yes", "Via .astream()"),
        ("Multi-turn memory", "Manual", "In-process", "Checkpointer"),
        ("Persistence", "None", "RAM only", "Pluggable (SQLite, PG)"),
        ("Model portability", "No", "No", "Yes (one line swap)"),
        ("Observability", "print()", "print()", "LangSmith tracing"),
        ("Human-in-the-loop", "Build it", "Build it", "interrupt_before=[]"),
        (f"Wall time", f"{t1:.1f}s", f"{t2:.1f}s", f"{t3:.1f}s"),
    ]
    col_w = [max(len(r[i]) for r in rows) + 2 for i in range(4)]
    for i, row in enumerate(rows):
        line = "  ".join(str(cell).ljust(col_w[j]) for j, cell in enumerate(row))
        print(line)
        if i == 0:
            print("─" * sum(col_w))


if __name__ == "__main__":
    main()
