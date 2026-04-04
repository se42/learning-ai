# 02 — Agent Skills (SKILL.md Specification)

This module demonstrates the Anthropic Agent Skills specification — an open standard for packaging reusable AI capabilities as self-contained playbooks.

**The relationship to MCP:** MCP servers provide *tools* (the verbs an LLM can invoke). Skills provide *playbooks* (the instructions, context, and constraints that guide how an LLM uses those tools). Without skills, the LLM is guessing at your workflows. With skills, it's following your team's actual processes.

---

## What is a Skill?

A skill is a folder containing a `SKILL.md` file and optional supporting resources (scripts, reference docs, templates). The `SKILL.md` has YAML frontmatter (metadata) and a Markdown body (instructions).

When a user asks something that matches a skill's description, the IDE loads the skill's instructions into the LLM's context. The LLM then follows those instructions — using the specified tools, applying the business rules, and producing output in the expected format.

**Key properties:**
- **Persistent** — Skills survive across conversations. Define them once, use them forever.
- **Automatic** — The IDE matches user requests to skills based on descriptions. No manual invocation needed (unless you want it).
- **Progressive disclosure** — Only the metadata loads at startup (~100 tokens per skill). The full body loads only when triggered. Supporting files load only when referenced. This keeps context overhead minimal.
- **Open standard** — As of December 2025, Agent Skills is an open standard adopted by 20+ tools: Claude Code, Cursor, VS Code with GitHub Copilot, Gemini CLI, and more.

---

## Anatomy of a Skill

Every skill is a directory:

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: additional documentation
└── assets/           # Optional: templates, data files
```

The `SKILL.md` file has two parts:

```markdown
---
name: skill-name
description: What this skill does and when to use it
allowed-tools:
  - mcp__server-name__toolName
---

# Skill Title

Instructions for the LLM...
```

---

## Frontmatter Reference

### Base Specification (Portable)

These fields are part of the open Agent Skills spec and work across all compatible tools:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | 1-64 chars, lowercase + hyphens. Becomes the `/slash-command` in Claude Code. Must match the folder name. |
| `description` | Yes | 1-1024 chars. What the skill does AND when to use it. The IDE uses this to decide when to auto-load the skill. Front-load key use cases — UI may truncate at 250 chars. |
| `allowed-tools` | No | Tools the skill is pre-approved to use without asking. Format: `mcp__servername__toolName` for MCP tools, or `Bash(command:*)` for shell commands. |
| `license` | No | License name or path to LICENSE file. |
| `compatibility` | No | Environment requirements (OS, packages, network access). |
| `metadata` | No | Arbitrary key-value pairs (author, version, etc.). |

### Claude Code Extensions

These fields are Claude Code-specific and may not work in other tools:

| Field | Type | Description |
|-------|------|-------------|
| `disable-model-invocation` | Boolean | `true` = only invocable via `/command`, never auto-triggered. For dangerous operations. |
| `user-invocable` | Boolean | `false` = hidden from `/` menu. Only auto-triggered by description match. For background knowledge. |
| `argument-hint` | String | Autocomplete hint shown in the `/` menu. E.g., `"[case-id]"` or `"[query]"`. |
| `context` | String | `"fork"` = runs in an isolated subagent context. Main conversation is not affected. |
| `paths` | String | Glob patterns restricting filesystem access. E.g., `"**/*.py"` or `"02-skills/**"`. |
| `model` | String | Override the model when this skill is active. |
| `effort` | String | Override effort level: `low`, `medium`, `high`, `max`. |
| `agent` | String | Subagent type when `context: fork`. E.g., `"Explore"`, `"Plan"`. |
| `shell` | String | Shell for shell injection: `"bash"` (default) or `"powershell"`. |

---

## String Substitutions

Use these variables in the SKILL.md body:

| Variable | Description | Example |
|----------|-------------|---------|
| `$ARGUMENTS` | All arguments passed when invoking the skill | `/doc-search billing API` → `"billing API"` |
| `$1`, `$2`, ... | Positional arguments | `/case-review 1024` → `$1` = `"1024"` |
| `${CLAUDE_SKILL_DIR}` | Absolute path to the skill's directory | Use to reference scripts and files |
| `${CLAUDE_SESSION_ID}` | Current session ID | Useful for logging and tracing |

---

## Shell Injection

Prefix a command with `!` in backticks to execute it when the skill loads. The command's output replaces the placeholder before the LLM sees the skill body.

```markdown
## Current Git Status
!`git status --short`

## Available Scripts
!`ls ${CLAUDE_SKILL_DIR}/scripts/`
```

**When to use:** Inject dynamic context that changes between invocations — git state, file listings, environment info, timestamps. The LLM never sees the command itself, only the output.

**When not to use:** Don't use for expensive operations or anything with side effects. Shell injection runs every time the skill loads.

---

## Progressive Disclosure

Skills load in layers to minimize context overhead:

```
Layer 1: Metadata (~100 tokens per skill)
  → Always loaded at startup for all skills
  → name + description — just enough for the IDE to match requests

Layer 2: Instructions (<5k tokens)
  → Loaded when the skill triggers
  → The SKILL.md body — step-by-step instructions

Layer 3: References (on-demand)
  → Loaded only when the LLM reads them
  → Files in references/, scripts/, assets/
  → Can be arbitrarily large without affecting startup cost
```

This means you can bundle extensive reference material, large script libraries, and detailed templates — and pay zero context cost for any of it until it's actually needed.

---

## The Four Demo Skills

Each skill demonstrates different spec features:

### 1. `skill-case-lookup/` — The Basics

**Features:** `allowed-tools`, `$ARGUMENTS`, `references/` directory

The simplest possible skill. It names the MCP tools it needs, provides step-by-step instructions, references business rules in `references/api-patterns.md`, and uses `$ARGUMENTS` to accept a case ID.

```yaml
---
name: case-lookup
description: Look up a support case and summarize its status...
allowed-tools:
  - mcp__acme-platform__getCase
  - mcp__acme-platform__getCustomer
---
```

**Key lesson:** A skill is a playbook. It tells the LLM which tools to use, what order to use them in, and what the output should look like. The `references/` directory holds supporting material the LLM can consult if needed.

### 2. `skill-doc-search/` — Dynamic Context

**Features:** `argument-hint`, shell injection (`!`command``), `${CLAUDE_SKILL_DIR}`, `scripts/` directory

This skill shows how to inject dynamic context at load time. The `!`cat ...`` syntax runs a shell command and injects the output before the LLM sees the skill body. The `argument-hint` field tells the IDE what to show in the autocomplete menu.

```yaml
---
name: doc-search
argument-hint: "[search query or topic]"
---

## Available Categories
!`cat ${CLAUDE_SKILL_DIR}/scripts/list_categories.sh | tail -n +3`
```

**Key lesson:** Shell injection bridges the gap between static instructions and dynamic context. The categories list could change over time, but the skill always shows the current version.

### 3. `skill-case-review/` — Isolated Subagent

**Features:** `context: fork`, `paths` restriction, positional `$1`, combined scripts + references

This skill runs as a forked subagent — an isolated context that doesn't pollute the main conversation. The `paths` restriction scopes filesystem access to just this skill's directory. It uses positional arguments (`$1` for the case ID) and combines scripts (for pre-computation) with references (for evaluation criteria).

```yaml
---
name: case-review
context: fork
paths:
  - "02-skills/skill-case-review/**"
---
```

**Key lesson:** `context: fork` is for heavy analysis tasks. The subagent does its work, returns the result, and the main conversation stays clean. `paths` is a security boundary — the subagent can only see what you explicitly allow.

### 4. `skill-deploy/` — Safety Controls

**Features:** `disable-model-invocation` for safety-critical operations

This skill can only be triggered by explicitly typing `/deploy-release`. The LLM cannot auto-invoke it no matter how relevant the conversation seems. The instructions include explicit human confirmation gates.

```yaml
---
name: deploy-release
disable-model-invocation: true
---
```

**Key lesson:** Not every skill should be auto-triggered. For operations that modify production systems, send external communications, or handle financial data, `disable-model-invocation` ensures a human is always in the loop.

---

## Skills + MCP: The Full Picture

Skills reference MCP tools by their fully qualified name: `mcp__<server-name>__<tool-name>`. This creates a layered architecture:

```
User Request
    ↓
IDE matches skill description → loads SKILL.md
    ↓
Skill instructions tell LLM which MCP tools to use and how
    ↓
LLM invokes MCP tools (→ MCP server → Rails API)
    ↓
Results flow back through the skill's instructions
    ↓
LLM formats output per the skill's specification
```

Without skills, the LLM sees a flat list of tools and must figure out workflows on its own. With skills, the LLM has domain-specific guidance: which tools to combine, what business rules to follow, and what the output should look like.

**Distributing skills with your MCP server:** When you ship a Docker image containing your MCP server, you can also include skills in a well-known directory. Users copy them into their IDE's skills directory (`.claude/skills/`, `.cursor/skills/`, etc.). The MCP server provides the tools; the skills provide the context to use them well.

---

## Where Skills Live

| Location | Scope | Discovery |
|----------|-------|-----------|
| `.claude/skills/` | Project | Auto-discovered by Claude Code for this project |
| `~/.claude/skills/` | Global | Available in all Claude Code sessions |
| `.cursor/skills/` | Project | Auto-discovered by Cursor for this project |
| Custom directory | Varies | User copies/symlinks into the above locations |

In this instructional module, the skills live in `02-skills/` for clarity. In a real project, deliverable skills (for your users) would be distributed alongside the MCP server, while developer skills (for your team) would live in `.cursor/skills/` or `.claude/skills/`.

---

## What's Next

These demo skills pair with the MCP server in `01-mcp-server/`. Together they show the full client-side story: tools (MCP) + playbooks (skills) = useful AI capabilities in your users' IDEs.

The `03-intelligence-service/` module covers the other side: server-side AI capabilities that the Rails application calls directly.
