# Acme Platform API Patterns

## Case Statuses

| Status | Meaning | SLA Implications |
|--------|---------|------------------|
| `open` | New case, not yet assigned | Must be triaged within 4 hours |
| `pending` | Awaiting action (from us or customer) | Check `pending_reason` field |
| `resolved` | Solution provided, awaiting confirmation | Auto-closes after 72 hours |
| `closed` | Case complete | No further action needed |

## Priority Levels

| Priority | Response Target | Escalation |
|----------|----------------|------------|
| `critical` | 1 hour | Auto-escalates to senior after 2 hours |
| `high` | 4 hours | Auto-escalates after 8 hours |
| `medium` | 1 business day | Standard workflow |
| `low` | 3 business days | Batch review acceptable |

## Customer Tiers

| Tier | Cases/Month | Priority Override |
|------|-------------|-------------------|
| `free` | 2 | None |
| `pro` | 10 | Can request `high` |
| `enterprise` | Unlimited | All cases default `high`, can request `critical` |

## Common Response Shapes

### Case Object
```json
{
  "id": 1234,
  "subject": "Cannot export CSV from dashboard",
  "description": "When clicking export...",
  "status": "open",
  "priority": "medium",
  "customer_id": 567,
  "created_at": "2026-03-15T10:30:00Z",
  "updated_at": "2026-03-15T14:22:00Z",
  "notes": [
    {
      "id": 1,
      "author": "support-agent",
      "content": "Investigating CSV generation...",
      "created_at": "2026-03-15T11:00:00Z"
    }
  ]
}
```

### Customer Object
```json
{
  "id": 567,
  "name": "Acme Corp",
  "email": "support@acme.example.com",
  "tier": "enterprise",
  "created_at": "2024-01-10T00:00:00Z"
}
```
