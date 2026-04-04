# Process: How This Module Was Built

This document describes the process we followed to research and build this
instructional module using Claude Code (Opus 4.6). The goal is to help
teammates understand the workflow so they can apply it to their own
AI-assisted research and development projects.

## 1. Write a Clear Brief

We started with `CLAUDE.md` — a plain-English description of the problem,
the two proposed pathways (MCP server and intelligence microservice), and
five specific questions we needed answered. No code, no file structure, just
context and intent.

**Why this matters:** The brief is the single most important input. Claude
can research, plan, and build — but only if it understands what you're trying
to accomplish and why. Spend time on the brief. Include your constraints,
your team's context, and the questions you don't know the answers to.

## 2. Clarifying Questions Before Planning

Claude read the brief and asked four targeted questions before doing any work:

- LLM provider preference (provider-agnostic vs Claude-specific)
- Deployment context (full infra vs local-runnable)
- Scale of the mock OpenAPI spec
- Depth of SKILL.md spec coverage

We answered with clear decisions: provider-agnostic (OpenAI + Gemini),
local-runnable, small mock spec, and full spec feature coverage.

**Why this matters:** These questions surfaced decisions that would have
caused rework if assumed incorrectly. A few minutes of alignment up front
saved hours of revision later.

## 3. Parallel Research Phase

Claude launched three research agents in parallel, each focused on a
different area:

1. **FastMCP + OpenAPI** — Current state of MCP, `FastMCP.from_openapi()`,
   tag filtering, Docker distribution, transport modes, IDE configuration
2. **SKILL.md Specification** — Full spec format, all frontmatter fields,
   Claude Code extensions, shell injection, progressive disclosure
3. **AI Microservice Patterns** — Provider-agnostic LLM access, FastAPI
   patterns, Rails-to-Python communication, the graduation path from simple
   to complex

Each agent searched the web and compiled a structured report. All three ran
concurrently — total wall-clock time was roughly the duration of the slowest
one, not the sum of all three.

**Why this matters:** Research is the foundation. Claude's knowledge has a
cutoff date, and the AI ecosystem moves fast. Web research ensures the demos
reflect current best practices (FastMCP 3.2, Agent Skills open standard,
LangChain's `init_chat_model()`), not patterns from a year ago.

## 4. Plan Mode

Claude entered plan mode — a structured workflow where it explores, designs,
and writes a plan file before touching any code. The plan included:

- Complete directory structure (every file, annotated)
- Module descriptions with specific contents for each file
- Build order showing what could be parallelized
- Key design decisions with rationale
- Verification steps

We reviewed the plan and gave two pieces of feedback:

- Use `uv` instead of `pip` for dependency management
- Developer skills go in `.cursor/skills/`, not `.claude/skills/` — with a
  clear distinction between developer skills (for our team) and deliverable
  skills (for our users)

Claude updated the plan and we approved it.

**Why this matters:** Plan mode catches structural problems before you've
written code. Our feedback about the skill directory distinction would have
required moving files and rewriting docs if caught after implementation.

## 5. Parallel Implementation

With the plan approved, Claude executed in parallel:

- **Background Agent A** — Built the entire MCP server module (9 files:
  OpenAPI spec, two server implementations, Dockerfile, IDE configs,
  pyproject.toml, README)
- **Background Agent B** — Built the entire intelligence service module
  (15 files: config, models, services, routers, sample data, pyproject.toml,
  README)
- **Main thread** — Built the skills module directly (4 skills with
  supporting scripts and references, plus the skills README)

The two background agents worked on completely independent directory trees,
so there were no conflicts. One agent hit a rate limit partway through but
had already finished all its files.

**Why this matters:** The two tracks (MCP server and intelligence service)
had no dependencies on each other. Recognizing this during planning meant
we could build them simultaneously. The skills module depended conceptually
on the MCP server (it references MCP tool names), but since we designed both
in the plan, we already knew the tool names and could build skills in
parallel too.

## 6. Review and Fix

After the agents finished, Claude:

- Verified all expected files were created (file inventory)
- Read key files from each module to check quality
- Fixed one deprecation warning (a FastMCP import path changed in 3.2)
- Built the remaining pieces that depended on both tracks being complete:
  developer skills, architecture diagram, and root README

## 7. Verification

Claude ran automated verification for both modules:

- **MCP server:** Loaded the OpenAPI spec, confirmed 8 operations across 4
  tag groups, tested tag filtering (e.g., `--tag cases` → 3 tools), built
  the FastMCP server instance
- **Intelligence service:** Imported all modules, validated Pydantic models,
  ran a search query against the mock data corpus, booted the FastAPI app
  with a test client, hit the health and search endpoints

This caught the deprecation warning and confirmed everything works.

## Timeline

The entire process — from reading the brief to verified deliverable — took
one conversation session. The rough breakdown:

| Phase | What Happened |
|-------|---------------|
| Brief + Questions | Read CLAUDE.md, asked 4 clarifying questions |
| Research | 3 parallel web research agents |
| Planning | Plan mode with structured plan file, one round of feedback |
| Implementation | 2 parallel background agents + direct skill writing |
| Integration | Developer skills, architecture diagram, root README |
| Verification | Automated tests on both modules |

## Tips for Your Own Projects

**Write the brief first.** Don't jump into code. Describe the problem, the
constraints, and what you need to learn. The brief is your leverage.

**Answer questions decisively.** When Claude asks clarifying questions, give
clear answers with reasoning. "Provider-agnostic because we're using OpenAI
and Gemini" is better than "whatever you think."

**Use plan mode for anything non-trivial.** The plan catches structural
mistakes before they're expensive. Review it carefully — this is where you
have the most leverage over the final result.

**Look for parallelism.** If your project has independent tracks, say so.
Claude can run multiple agents simultaneously. A project with two independent
modules takes roughly the same wall-clock time as one module.

**Verify the output.** Claude can run the code it generates. Ask it to.
Automated verification catches import errors, API changes, and integration
issues that look fine in a code review.

**Give feedback early.** Our feedback about `uv` and `.cursor/skills/`
happened during plan review — a two-line edit to the plan. If we'd caught
it after implementation, it would have meant updating files across multiple
modules.
