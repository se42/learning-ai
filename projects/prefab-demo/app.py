"""FastMCP + Prefab UI demo: interactive incident triage with human-in-the-loop."""

from __future__ import annotations

from typing import Literal

from fastmcp import FastMCP
from prefab_ui.actions import SetState, ShowToast
from prefab_ui.actions.mcp import CallTool, SendMessage
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Column,
    Heading,
    Muted,
    Row,
    Separator,
    Small,
    Text,
)
from prefab_ui.components.control_flow import ForEach, If
from prefab_ui.rx import ITEM, RESULT

# ---------------------------------------------------------------------------
# Fake data — in a real server this comes from your monitoring stack / APIs.
# ---------------------------------------------------------------------------

_INCIDENTS: list[dict] = [
    {
        "id": "INC-101",
        "title": "Checkout latency spike",
        "severity": "critical",
        "summary": "p99 jumped from 42ms to 1.2s in us-east-1 over the last 15 minutes.",
    },
    {
        "id": "INC-102",
        "title": "Search indexer backlog",
        "severity": "warning",
        "summary": "Indexer is 12k documents behind; queries returning stale results.",
    },
    {
        "id": "INC-103",
        "title": "Notification delivery delay",
        "severity": "warning",
        "summary": "Email queue depth at 8k; average delivery time up from 2s to 45s.",
    },
    {
        "id": "INC-104",
        "title": "Auth service certificate expiry",
        "severity": "critical",
        "summary": "TLS cert expires in 18 hours; no auto-renewal configured.",
    },
    {
        "id": "INC-105",
        "title": "Elevated 404 rate on CDN",
        "severity": "info",
        "summary": "404 rate ticked up 3% after last deploy; likely stale asset references.",
    },
]

_decisions: dict[str, str | None] = {inc["id"]: None for inc in _INCIDENTS}


def _enriched_incidents() -> list[dict]:
    return [{**inc, "decision": _decisions[inc["id"]]} for inc in _INCIDENTS]


def _triage_summary_text() -> str:
    investigate = [iid for iid, d in _decisions.items() if d == "investigate"]
    dismiss = [iid for iid, d in _decisions.items() if d == "dismiss"]
    pending = [iid for iid, d in _decisions.items() if d is None]
    parts: list[str] = []
    if investigate:
        parts.append(f"Investigate: {', '.join(investigate)}")
    if dismiss:
        parts.append(f"Dismiss: {', '.join(dismiss)}")
    if pending:
        parts.append(f"Still pending: {', '.join(pending)}")
    return ". ".join(parts) + "." if parts else "No decisions recorded yet."


# ---------------------------------------------------------------------------
# All tools on one flat FastMCP server — no FastMCPApp provider indirection.
# ---------------------------------------------------------------------------

mcp = FastMCP("Prefab Demo")


@mcp.tool()
def triage_incident(
    incident_id: str,
    action: Literal["investigate", "dismiss"],
) -> list[dict]:
    """Record a triage decision for an incident and return the updated list."""
    if incident_id not in _decisions:
        raise ValueError(f"Unknown incident: {incident_id}")
    _decisions[incident_id] = action
    return _enriched_incidents()


@mcp.tool()
def submit_triage() -> str:
    """Build a triage summary from current server state."""
    return f"Here are my triage decisions: {_triage_summary_text()}"


@mcp.tool()
def get_triage_summary() -> str:
    """Return a text summary of current triage decisions."""
    return _triage_summary_text()


@mcp.tool(app=True)
def incident_triage() -> PrefabApp:
    """Open the incident triage board — review recent incidents and mark each for investigation or dismissal."""
    decision = ITEM.decision
    severity = ITEM.severity

    severity_variant = (severity == "critical").then(
        "destructive",
        (severity == "warning").then("warning", "secondary"),
    )
    decision_variant = (decision == "investigate").then("outline", "secondary")

    with Column(gap=6, css_class="p-6 max-w-4xl") as view:
        Heading("Incident Triage")
        Small(
            "Review each incident and decide: investigate or dismiss. "
            "When you're done, click Submit to send your decisions back to the agent."
        )
        Separator()

        with ForEach("incidents"):
            with Column(gap=2, css_class="p-4 border rounded-lg"):
                with Row(gap=2, align="center"):
                    Text(ITEM.id, css_class="font-mono font-semibold")
                    Text(ITEM.title, css_class="font-semibold")
                    Badge(label=severity, variant=severity_variant)
                    with If(decision):
                        Badge(label=decision, variant=decision_variant)

                Muted(ITEM.summary)

                with Row(gap=2):
                    Button(
                        "Investigate",
                        variant="default",
                        size="sm",
                        on_click=CallTool(
                            "triage_incident",
                            arguments={
                                "incident_id": ITEM.id,
                                "action": "investigate",
                            },
                            on_success=[
                                SetState("incidents", RESULT),
                                ShowToast(
                                    "Marked for investigation",
                                    variant="success",
                                ),
                            ],
                            on_error=ShowToast("Failed", variant="error"),
                        ),
                    )
                    Button(
                        "Dismiss",
                        variant="secondary",
                        size="sm",
                        on_click=CallTool(
                            "triage_incident",
                            arguments={
                                "incident_id": ITEM.id,
                                "action": "dismiss",
                            },
                            on_success=[
                                SetState("incidents", RESULT),
                                ShowToast("Dismissed", variant="default"),
                            ],
                            on_error=ShowToast("Failed", variant="error"),
                        ),
                    )

        Separator()

        Button(
            "Submit Triage to Chat",
            variant="default",
            on_click=CallTool(
                "submit_triage",
                on_success=[
                    SendMessage(RESULT),
                    ShowToast("Triage submitted to chat", variant="success"),
                ],
                on_error=ShowToast("Failed to submit", variant="error"),
            ),
        )

    return PrefabApp(
        view=view,
        state={"incidents": _enriched_incidents()},
    )


@mcp.tool(app=True)
def greet(name: str) -> PrefabApp:
    """Greet someone with a small card (minimal Prefab layout)."""
    with Column(gap=4, css_class="p-6") as view:
        Heading(f"Hello, {name}!")
        with Row(gap=2, align="center"):
            Text("Status")
            Badge("Greeted", variant="success")

    return PrefabApp(view=view)


if __name__ == "__main__":
    mcp.run()
