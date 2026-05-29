---
name: find-ideas
description: Use when the user wants to find what to work on next in an existing project, audit progress, brainstorm a backlog, surface bugs and tech debt, or generate a prioritized list of ideas. Triggers on "/find-ideas", "what should I build next", "find me ideas", "audit what's left", "find bugs", "what's missing".
---

# Find Ideas

## Overview

Survey an existing project, then produce a prioritized backlog as a markdown doc in the repo. Three sections of ideas (features, bugs, tech debt) plus an inventory of what's already done.

The completed-features inventory comes first because it grounds every later judgment — you can't tell what's missing without seeing what's there.

## When to Use

- User asks for ideas, a backlog, a roadmap, or "what to work on next"
- User wants to audit a project's state
- User mentions surfacing bugs or tech debt
- Slash command `/find-ideas` invoked

**Don't use for:**
- Brand-new projects with no code — use brainstorming instead
- Single-file scripts — overkill
- When user already has a specific task in mind

## Workflow

### 1. Research

Read in this order. Stop when you have enough signal — don't exhaustively read everything.

- `README.md`, `AGENTS.md` if present
- `package.json` / `pyproject.toml` / `Cargo.toml` / equivalent — names, scripts, dependencies
- Top-level directory listing (one level deep)
- `docs/` tree — list files, read specs/ADRs/design docs that look load-bearing
- Sample 3-8 key source files: route definitions, main entry points, schema/model files, recent feature directories

If the project is a monorepo, do this per app/package that looks relevant.

### 2. Synthesize

Build the four lists in order:

1. **Completed features** — what's shipped. Group by area (auth, billing, UI, etc.). One bullet per feature.
2. **New feature ideas** — gaps, natural extensions, things the docs hint at but haven't been built
3. **Bugs / known issues** — edge cases, missing validation, broken flows you noticed while reading
4. **Tech debt / refactors** — duplication, missing tests, fragile patterns, stale dependencies

Assign every item in lists 2–4 a priority:

- **P0** — critical, blocking, data-loss risk, security
- **P1** — important, ship next
- **P2** — nice-to-have
- **P3** — someday / speculative

If you can't justify a priority in one short clause, the item is too vague — sharpen it or drop it.

### 3. Write the doc

Path: `docs/ideas/YYYY-MM-DD-ideas.md` (use today's date, create the folder if missing).

Use this structure exactly:

```markdown
# Project Ideas — YYYY-MM-DD

## Priority Legend

- **P0** — critical / blocking / data-loss / security
- **P1** — important, ship next
- **P2** — nice-to-have
- **P3** — someday / speculative

## Completed Features

### <Area>
- Feature — one-line description

## New Feature Ideas

- **[P1] Title** — what it is. _Why: rationale._
- **[P2] Title** — what it is. _Why: rationale._

## Bugs / Known Issues

- **[P0] Title** — symptom and where. _Why: impact._

## Tech Debt / Refactors

- **[P2] Title** — what's wrong. _Why: cost of leaving it._
```

Sort each priority section by priority (P0 → P3), then alphabetically inside a tier.

### 4. Wrap up

Print the doc path and a 3-bullet summary (top P0/P1 item from each list, if any). Then ask:

> "Want me to refine any section, add detail, or convert top items into GitHub issues?"

### 5. Offer to split into task files

After delivering the ideas doc, ask the user if they want the lists split into actionable task files under `docs/tasks/` (create the folder if missing):

> "Want me to split these into task files under `docs/tasks/`? I'd create `new_features_ideas.md`, `bugs.md`, `tech_debt.md` (and any other sections that exist) as numbered checklists."

If the user agrees, write one file per non-empty idea section. Map sections to filenames:

- **New Feature Ideas** → `new_features_ideas.md`
- **Bugs / Known Issues** → `bugs.md`
- **Tech Debt / Refactors** → `tech_debt.md`
- Any other section → `<snake_case_of_section_title>.md`

Do **not** create a task file for "Completed Features" — that's reference, not actionable.

**File format** — each task file must be:

- An H1 matching the source section title
- A numbered list (`1.`, `2.`, …) of all items from that section, preserving priority order
- Each item prefixed with an empty checkbox: `- [ ]`
- Item body copied verbatim from the ideas doc (title, priority tag, description, _Why:_)

Example:

```markdown
# Bugs / Known Issues

1. - [ ] **[P0] Title** — symptom and where. _Why: impact._
2. - [ ] **[P1] Title** — symptom and where. _Why: impact._
```

After writing the files, print the list of paths created.

## Quick Reference

| Step | Output |
|------|--------|
| Research | Mental model of project state |
| Synthesize | 4 lists (completed + 3 prioritized) |
| Write | `docs/ideas/YYYY-MM-DD-ideas.md` |
| Wrap | Path + 3-bullet summary + offer to refine |
| Split (on request) | `docs/tasks/{new_features_ideas,bugs,tech_debt,…}.md` as numbered checklists |

## Common Mistakes

- **Skipping the completed-features inventory** — without it, "new ideas" overlap with what's already shipped. Always do it first.
- **Listing every possible TODO** — the value is prioritization. If everything is P1, nothing is. Aim for ~5-15 items per list, not 50.
- **Vague priorities** — "P1: improve performance" is useless. Say what specifically is slow and why it matters.
- **Inventing bugs you can't ground in code** — only list bugs you can point to a file/area for. Speculation belongs in "New feature ideas" or "Tech debt".
- **Exhaustively reading the codebase** — research until you have enough signal, then synthesize. The doc is the deliverable, not a complete audit.

## Converting to Issues

If the user wants to push items to GitHub after reviewing the doc, hand off to the `to-issues` or `triage` skill rather than creating issues directly here.
