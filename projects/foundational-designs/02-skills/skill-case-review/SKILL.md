---
name: case-review
description: Perform a thorough review of a support case with full context gathering, risk assessment, and recommended actions. Use for complex or escalated cases that need deep analysis.
allowed-tools:
  - mcp__acme-platform__getCase
  - mcp__acme-platform__getCustomer
  - mcp__acme-platform__listCaseNotes
  - mcp__acme-platform__searchArticles
context: fork
paths:
  - "02-skills/skill-case-review/**"
---

# Case Review (Deep Analysis)

Perform a comprehensive review of case **$1**.

This skill runs as a forked subagent (`context: fork`) so the analysis
does not pollute the main conversation. The `paths` restriction scopes
filesystem access to this skill's directory only.

## Step 1: Gather Context

Fetch all available data for the case:

!`bash ${CLAUDE_SKILL_DIR}/scripts/fetch_context.sh $1`

Use the MCP tools to retrieve:
- Full case details (getCase)
- Customer profile (getCustomer)
- All case notes (listCaseNotes)
- Related knowledge articles (searchArticles with the case subject)

## Step 2: Evaluate Against Checklist

Review the case against the checklist in [references/review-checklist.md](references/review-checklist.md).

## Step 3: Produce Review

Format your analysis as:

```
## Case Review: #[case_id]

### Summary
[2-3 sentence overview of the case and its current state]

### Risk Assessment
- **SLA Risk**: [on track / at risk / breached] — [reasoning]
- **Customer Impact**: [low / medium / high] — [reasoning]
- **Escalation Need**: [none / recommended / urgent] — [reasoning]

### Timeline
[Chronological summary of key events from notes]

### Recommended Actions
1. [Specific, actionable next step]
2. [...]

### Related Knowledge
- [Relevant articles found, with article IDs]
```
