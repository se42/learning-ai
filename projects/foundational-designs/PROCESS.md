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

## 8. Review, Questions, and Iteration

After the initial build was complete, we shifted into a review cycle. This
is where the human leads and the AI assists:

- Read through the generated material — READMEs, code, architecture docs
- Asked questions about design decisions ("Would it make sense to offer
  both Docker and uv as distribution paths?")
- Discussed trade-offs (Docker vs uv vs Go binaries) and made decisions
- Fed those decisions back as concrete change requests ("Update the
  project material to present Docker and uv consistently")

Claude then made targeted edits across 9 files to align the entire project
with the new "Docker or uv" distribution strategy — updating READMEs, IDE
configs, the architecture diagram, pyproject.toml entry points, and the
skills distribution guidance.

**Why this matters:** The initial build is a draft, not a deliverable. The
review cycle is where domain knowledge, user empathy, and strategic thinking
shape the output into something that actually fits your team and users. AI
can research and build quickly, but the human's job is to ask "does this
make sense for our people?" and steer accordingly. This phase is also where
you catch assumptions that seemed reasonable in isolation but don't hold up
when you read the whole thing end-to-end — like the assumption that all
users would be willing to run Docker.

## Timeline

The entire process — from reading the brief to verified deliverable — took
one conversation session. The review and iteration phase started in a second
session. The rough breakdown:

| Phase | What Happened | Human Time | AI Time |
|-------|---------------|------------|---------|
| Brief + Questions | Read CLAUDE.md, asked 4 clarifying questions | ~15 min writing, ~5-10 min answering | Minutes |
| Research | 3 parallel web research agents | Waiting | ~15 min |
| Planning | Plan mode with structured plan file, one round of feedback | ~5 min reviewing | ~10 min |
| Implementation | 2 parallel background agents + direct skill writing | Waiting | ~30 min |
| Integration | Developer skills, architecture diagram, root README | Waiting | ~10 min |
| Verification | Automated tests on both modules | Waiting | Minutes |
| Review + Iteration | Human-led review, questions, and targeted edits | ~1+ hours reading, ongoing discussion | Minutes per edit |

## The Real Time Investment

The asymmetry in the timeline above is striking: **~15 minutes of
writing the brief produced ~1 hour of AI work, which then required
over an hour of human review** just to read through all the output and
begin asking questions. The brief is the highest-leverage artifact in
the entire process. Every minute spent clarifying your intent saves
multiples of that in review and rework.

### What the brief got right

Looking back at the original `CLAUDE.md`, several choices paid
outsized dividends:

**Explained the "why" behind the architecture, not just the "what."**
The brief didn't just say "build an MCP server." It explained that the
team chose SOA for three specific reasons (focus hub, Python access,
auth safety) and that they'd eventually graduate to agentic workloads.
This context shaped everything — from how the READMEs explained the
architecture to how the intelligence service was scoped. Without it,
Claude would have built a generic demo instead of one framed around a
real team's migration path.

**Named specific technologies as starting points.** Mentioning FastMCP,
OpenAPI specs, and the SKILL.md spec gave Claude concrete research
targets. The brief even suggested the `FastMCP.from_openapi()` approach.
This meant the research phase was focused and efficient rather than
exploratory. If you know the tools exist, say so — even if you're not
sure they're the right choice.

**Asked specific questions instead of open-ended ones.** The five
numbered questions each became a concrete section of the final README.
"Are these solid first steps?" produced a direct yes/no with evidence.
"What next-step complexities justify the microservice?" produced a
ranked list that the team can actually reference when debating YAGNI.
Vague prompts get vague output; specific questions get specific answers.

**Described the "naive to curated" progression explicitly.** The brief
said "start with a naive MCP server that mirrors the API, then build
curated tools." This directly produced the two-server demo
(`server_from_spec.py` and `server_curated.py`) which became one of
the most instructive parts of the module. The progression was already
in the brief — Claude just had to build it.

**Set clear scope boundaries.** Phrases like "focus on FUNDAMENTALS"
and "I didn't tell you all about the details of our service, so just
focus on FUNDAMENTALS" appeared multiple times. This kept the output
from sprawling into advanced topics (RAG pipelines, agent
checkpointing, OAuth flows) that would have diluted the learning value.

### What the brief missed — and what it cost

**Distribution was framed as Docker-only.** The brief said "a Docker
image our users can run in their IDE" — a reasonable starting point,
but it didn't consider users who can't or won't run Docker. This
assumption propagated through every file Claude produced: READMEs, IDE
configs, architecture diagrams, even the Dockerfile header comments.
When the review cycle surfaced this gap, fixing it required edits
across 9 files. If the brief had said "distributed via Docker or
Python package," the dual-path approach would have been baked in from
the start.

**Tooling preferences weren't stated.** The brief didn't mention `uv`,
`pip`, or any preference for dependency management. Claude had to ask.
The answer ("use uv") then required a plan revision. Similarly, the
brief didn't say where developer skills should live vs. deliverable
skills — that distinction came up during plan review and required
another revision. These weren't hard to fix at the planning stage, but
they're examples of decisions you already know the answer to. If you
know, say so upfront.

**LLM provider preference wasn't specified.** Should the demos use
Claude? OpenAI? Be provider-agnostic? This was another clarifying
question that could have been preempted. The answer (provider-agnostic,
using OpenAI and Gemini) affected the intelligence service's entire
architecture — its model routing, its config structure, its
dependencies. One sentence in the brief would have eliminated one
round-trip.

### The lesson

None of the post-hoc clarifications were fatal. They were caught early
(during planning or review) and fixed with modest effort. But they
illustrate a pattern: **things you already know but don't write down
become questions you have to answer later, and then edits you have to
review.** Each one is a small cost, but they compound.

The brief doesn't need to be perfect. But if you find yourself thinking
"Claude will probably figure this out" — stop and write it down. The 30
seconds it takes to type "use uv, not pip" or "some users can't run
Docker" saves minutes of clarification and review later. When you're
asking an AI to produce 30+ files in parallel, those small ambiguities
multiply.

**The heuristic:** If a teammate would ask you about it in a design
review, put it in the brief.

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
