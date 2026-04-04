#!/bin/bash
# Gathers preliminary context for a case review.
# Called via shell injection: !`bash ${CLAUDE_SKILL_DIR}/scripts/fetch_context.sh $1`
#
# This script runs BEFORE the skill body is processed by the LLM,
# so its output becomes part of the skill's context. Use this for
# any pre-computation or data gathering that doesn't require LLM tools.

CASE_ID="${1:?Usage: fetch_context.sh <case_id>}"

echo "## Pre-Review Context for Case #${CASE_ID}"
echo ""
echo "Review initiated at: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "Reviewer session: ${CLAUDE_SESSION_ID:-unknown}"
echo ""
echo "Checklist loaded from: ${CLAUDE_SKILL_DIR}/references/review-checklist.md"
echo ""
echo "Proceed with MCP tool calls to gather case data."
