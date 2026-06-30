# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# StyleMatch

AI pipeline: Pinterest boards → aesthetic extraction → Vinted secondhand listings.

## Learning
This project's primary purpose is learning AI-assisted programming and agentic workflows. 
Proactively explain design decisions and surface relevant Claude Code commands, 
shortcuts, and patterns as they apply.

## Agents
When a task involves repeated, parallelizable, or context-heavy work, flag whether 
it warrants a Claude Code subagent. Recommend name, description, model, and tool 
scope if so.


## Stack
- Frontend: Next.js (App Router) + Tailwind
- Backend: Python FastAPI
- DB: Supabase
- AI: Anthropic API direct (claude-sonnet-4-6) — no framework
- See @ARCHITECTURE.md for full pipeline, ADRs, and data model

## Commands

### Setup
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### Dev servers
```bash
cd backend && uvicorn main:app --reload
cd frontend && npm run dev
```

### Tests
```bash
# All tests
cd backend && pytest
cd frontend && npm test

# Single test
cd backend && pytest agents/test_style_analyst.py::test_aggregates_sub_agent_results -v
cd frontend && npm test -- --testPathPattern=results
```

### Lint
```bash
cd backend && ruff check .
cd frontend && npm run lint
```

## Architecture
```
backend/agents/       # 4 agents — style_analyst, query_translator, results_evaluator, learning_loop
backend/sources/      # SearchSource interface + vinted/apify implementations
backend/lib/          # pinterest OAuth, style_context.md I/O, pydantic models
frontend/app/         # 3 screens: setup, results, profile (StyleProfile debug)
data/style_context.md # Living correction log — injected into agents at runtime
```

Key flow: Style Analyst spawns parallel sub-agents (ADR-003) → aggregates into StyleProfile → Query Translator outputs search strategies → SearchSource executes (never agents directly, ADR-002) → Results Evaluator scores listings with anchor pin images (ADR-005) → Learning Loop writes corrections to `style_context.md`, which is re-injected on the next run (ADR-004).

## Non-negotiables
- Agents never call Vinted directly — always through `SearchSource` interface (ADR-002)
- `style_context.md` is the learning layer — every feedback loop writes to it; every agent run reads it
- Raw Anthropic API only — no LangChain, no Mastra, no wrappers (ADR-001)
- Pinterest OAuth token stored locally only, never server-side

## Workflow rules
- Always write a plan before implementing. For any agent change: describe input/output/context before code.
- After implementing an agent stage, write a verification test before moving to the next stage.
- When you make a mistake worth remembering, append it to `learning.md` immediately.
- Use `IMPORTANT:` prefix for rules that have been violated before.

## Learning Log
Append to `learning.md` immediately when any of these occur:
- A fix is needed because an earlier approach was wrong (not just incomplete)
- A subagent's output failed acceptance criteria and had to be redone
- You catch yourself about to repeat a previously-logged mistake — check 
  learning.md before non-trivial changes to agents/, sources/, or prompts/
- The user corrects your output or says "that's wrong" / "don't do that"

Format: `## [date] — [component]\n[what happened] → [what to do instead]`

Do not wait to be asked. Do not batch corrections for later — write them 
as they happen, in the same turn.

## Git
See @.claude/skills/git-issues/SKILL.md for issue creation
See @.claude/skills/pr-workflow/SKILL.md for PR workflow
See @.claude/rules/branch-naming.md for branch naming conventions
See @.claude/rules/commit-conventions.md for commit message conventions

## Common mistakes
See `learning.md` — appended throughout development.
