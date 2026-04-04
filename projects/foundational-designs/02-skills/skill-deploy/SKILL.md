---
name: deploy-release
description: Execute a production deployment release with safety checks. This skill is MANUAL-ONLY — it cannot be auto-invoked by the model, only by explicit /deploy-release command.
disable-model-invocation: true
allowed-tools:
  - Bash(deploy:*)
  - Read
---

# Deploy Release

**Target: $ARGUMENTS**

> **Safety Note:** `disable-model-invocation: true` means this skill can ONLY
> be triggered by you typing `/deploy-release`. The LLM cannot decide on its
> own to start a deployment. This is the right pattern for any operation that
> modifies production systems.

## Pre-flight

Run the preflight check and present the results. Do NOT proceed without
explicit human confirmation at each gate.

```bash
echo "=== Deployment Pre-flight: $ARGUMENTS ==="
echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""
echo "Checks:"
echo "  [ ] Git working directory clean"
echo "  [ ] All tests passing"
echo "  [ ] No pending database migrations"
echo "  [ ] Deployment target reachable"
echo ""
echo "Review the above. Type 'proceed' to continue or 'abort' to cancel."
```

## Gate 1: Human Confirmation

**STOP.** Present the preflight results and wait for the user to say "proceed."
Do not continue automatically. Do not suggest proceeding. Just present the
information and wait.

## Gate 2: Deploy

Only after explicit confirmation:

```bash
echo "Deploying $ARGUMENTS..."
echo "(In production, this would run your actual deploy script)"
echo "Deploy complete."
```

## Gate 3: Verify

After deployment:

```bash
echo "=== Post-deploy Verification ==="
echo "  [ ] Health check passing"
echo "  [ ] No error rate spike"
echo "  [ ] Key user flows operational"
```

Present results and wait for human sign-off.

## Why disable-model-invocation?

This skill demonstrates a critical safety pattern. Some operations should
never be triggered by AI judgment alone:

- **Deployments** — production changes require human accountability
- **Data deletion** — irreversible actions need explicit consent
- **External communications** — sending emails/messages on behalf of users
- **Financial operations** — anything involving money or billing

The `disable-model-invocation` flag ensures the LLM can only execute this
skill when a human explicitly types the `/deploy-release` command. The LLM
cannot decide "this seems like a good time to deploy" on its own.
