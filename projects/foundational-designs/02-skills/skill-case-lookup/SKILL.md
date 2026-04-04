---
name: case-lookup
description: Look up a support case by ID and summarize its current status, customer context, and recent activity. Use when someone asks about a specific case number or wants a case overview.
allowed-tools:
  - mcp__acme-platform__getCase
  - mcp__acme-platform__getCustomer
---

# Case Lookup

Look up case **$ARGUMENTS** and provide a concise status summary.

## Steps

1. Fetch the case details using the `getCase` tool with the case ID from $ARGUMENTS
2. Fetch the associated customer using the `getCustomer` tool with the `customer_id` from the case
3. Summarize in this format:

```
**Case #[id]: [subject]**
Status: [status] | Priority: [priority]
Customer: [name] ([tier] tier)
Created: [created_at] | Last updated: [updated_at]

Recent notes: [last 3 notes, if any]

⚠️ Flags: [any concerns — see rules below]
```

## Business Rules

- Always include the customer's support tier — it determines SLA expectations
- If the case has been open more than 7 days, flag it as "potentially stale"
- If the customer is on the enterprise tier and priority is not critical, note that enterprise cases should be reviewed for priority escalation
- If there are no notes in the last 48 hours, flag as "needs attention"

## Reference

For standard case statuses and priority definitions, see [API Patterns](references/api-patterns.md).
