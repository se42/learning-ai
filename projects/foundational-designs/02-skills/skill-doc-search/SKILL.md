---
name: doc-search
description: Search the Acme Platform knowledge base for articles relevant to a query or topic. Use when someone needs help finding documentation, troubleshooting guides, or reference material.
allowed-tools:
  - mcp__acme-platform__searchArticles
  - mcp__acme-platform__getArticles
argument-hint: "[search query or topic]"
---

# Documentation Search

Search the knowledge base for: **$ARGUMENTS**

## Available Categories

!`cat ${CLAUDE_SKILL_DIR}/scripts/list_categories.sh | tail -n +3`

## Instructions

1. Use the `searchArticles` tool with the query from $ARGUMENTS
2. For the top 3 results, review the content for relevance
3. Synthesize a concise answer that:
   - Directly addresses the query
   - Cites article titles and IDs (so the user can find the full article)
   - Notes if the available documentation doesn't fully cover the topic

## Response Format

```
**Results for: "$ARGUMENTS"**

[Synthesized answer addressing the query]

📄 Sources:
- [Article Title] (art-XXX) — [one-line relevance note]
- [Article Title] (art-XXX) — [one-line relevance note]

💡 [Optional: suggest related searches if the query is broad]
```

## Tips

- If the query is broad (e.g., "billing"), suggest narrowing to a specific aspect
- If no results match well, say so honestly rather than forcing a bad match
- For API-related queries, always check if there's a corresponding code example
