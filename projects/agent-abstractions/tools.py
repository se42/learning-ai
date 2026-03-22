"""
Shared tool implementations used across all three levels.

Separating business logic from agent plumbing is good practice at every level of abstraction.
The same Python functions are reused everywhere — what changes is how the agent discovers,
calls, and formats results from them.

Tools:
  search(topic)                    — look up information on a topic (simulated)
  save_recommendation(title, body) — write a recommendation to disk (real side effect)
"""

import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"


# ── Tool implementations (pure business logic) ──────────────────────────────

def search(topic: str) -> str:
    """Look up information about a technology topic."""
    db = {
        "fastapi": (
            "FastAPI is a modern Python web framework built on Starlette and Pydantic. "
            "Key traits: async-first, automatic OpenAPI docs, type-safe request/response "
            "validation via Pydantic, excellent performance (comparable to NodeJS/Go for "
            "I/O-bound workloads). Released 2018. Strong ecosystem, widely adopted for "
            "microservices and ML-serving APIs. Requires Python 3.7+."
        ),
        "flask": (
            "Flask is a lightweight Python web framework ('micro-framework'). Key traits: "
            "synchronous by default (WSGI), minimal core with extensions for everything else, "
            "huge ecosystem, battle-tested since 2010. Excellent for small services and teams "
            "that want explicit control. Async support added in Flask 2.0 but not idiomatic. "
            "Extremely well-documented; vast tutorial and Stack Overflow coverage."
        ),
        "fastapi vs flask": (
            "FastAPI vs Flask comparison: FastAPI wins on performance, type safety, and "
            "auto-generated docs. Flask wins on maturity, ecosystem size, and simplicity for "
            "small projects. For new async microservices: FastAPI. For teams with existing "
            "Flask expertise or WSGI constraints: Flask. Both are production-proven."
        ),
    }
    key = topic.lower().strip()
    result = db.get(key) or db.get(key.split(" vs ")[0]) or (
        f"No specific data for '{topic}'. General advice: evaluate based on team expertise, "
        "performance requirements, and ecosystem compatibility."
    )
    return result


def save_recommendation(title: str, body: str) -> str:
    """Write a recommendation to a markdown file in the output/ directory."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = title.lower().replace(" ", "_").replace("/", "_")
    path = OUTPUT_DIR / f"{slug}.md"
    path.write_text(f"# {title}\n\n{body}\n")
    return f"Saved to {path}"


# ── Anthropic SDK tool schemas (JSON Schema format) ──────────────────────────
# Used by Level 1 and Level 2, which talk directly to the Anthropic API.

ANTHROPIC_TOOLS = [
    {
        "name": "search",
        "description": "Look up information about a technology or topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic to search for, e.g. 'FastAPI vs Flask'",
                }
            },
            "required": ["topic"],
        },
    },
    {
        "name": "save_recommendation",
        "description": "Save a recommendation or decision to a file for the user to review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the recommendation, e.g. 'API Framework Decision'",
                },
                "body": {
                    "type": "string",
                    "description": "The full recommendation text in markdown format.",
                },
            },
            "required": ["title", "body"],
        },
    },
]

# Dispatcher: maps tool name → callable
TOOL_DISPATCH = {
    "search": lambda args: search(**args),
    "save_recommendation": lambda args: save_recommendation(**args),
}
