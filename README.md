# AI Hands

AI Hands is a personal collection of agent skills and reusable engineering rules.
It is meant to be read by coding agents, copied into agent environments, and used
as a shared operating manual for recurring product, engineering, and workflow
tasks.

The repository is intentionally lightweight: the Markdown files are the product.
There is no application runtime, build step, or package manager setup.

## Repository Layout

```text
.
├── README.md
├── rules/
│   ├── main.md
│   ├── context7.md
│   ├── folders.md
│   ├── git.md
│   └── web/
└── skills/
    ├── engineering/
    ├── personal/
    └── productivity/
```

## Skills

Skills live under `skills/<category>/<skill-name>/SKILL.md`. A skill can also
include nearby reference documents or scripts when the workflow needs more than
one file.

### Engineering

| Skill | Purpose |
| --- | --- |
| [`diagnose`](skills/engineering/diagnose/SKILL.md) | Debug hard bugs and performance regressions through a disciplined reproduce, instrument, fix, and regression-test loop. |
| [`grill-with-docs`](skills/engineering/grill-with-docs/SKILL.md) | Stress-test a plan against project language, `CONTEXT.md`, and ADRs. |
| [`improve-codebase-architecture`](skills/engineering/improve-codebase-architecture/SKILL.md) | Find refactoring and deepening opportunities that make a codebase easier to test and navigate. |
| [`prototype`](skills/engineering/prototype/SKILL.md) | Build throwaway logic or UI prototypes before committing to a design. |
| [`tdd`](skills/engineering/tdd/SKILL.md) | Build features and fixes with a red-green-refactor loop. |
| [`to-issues`](skills/engineering/to-issues/SKILL.md) | Convert a plan, spec, or PRD into independently grabbable implementation issues. |
| [`to-prd`](skills/engineering/to-prd/SKILL.md) | Turn conversation context into a PRD and publish it to an issue tracker. |
| [`triage`](skills/engineering/triage/SKILL.md) | Triage issues through explicit roles, states, and handoff briefs. |
| [`zoom-out`](skills/engineering/zoom-out/SKILL.md) | Ask the agent to explain how an unfamiliar area fits into the broader system. |

See [`skills/engineering/README.md`](skills/engineering/README.md) for the
engineering skill index.

### Productivity

| Skill | Purpose |
| --- | --- |
| [`caveman`](skills/productivity/caveman/SKILL.md) | Switch to an ultra-compressed communication style for token-sensitive work. |
| [`grill-me`](skills/productivity/grill-me/SKILL.md) | Interrogate a plan or design until the decision tree is clear. |
| [`handoff`](skills/productivity/handoff/SKILL.md) | Compact a conversation into a handoff document for another agent. |
| [`write-a-skill`](skills/productivity/write-a-skill/SKILL.md) | Create new skills with clear triggers, progressive disclosure, and optional bundled resources. |

See [`skills/productivity/README.md`](skills/productivity/README.md) for the
productivity skill index.

### Personal

| Skill | Purpose |
| --- | --- |
| [`edit-article`](skills/personal/edit-article/SKILL.md) | Edit article drafts for structure, clarity, and tone. |
| [`obsidian-vault`](skills/personal/obsidian-vault/SKILL.md) | Search, create, and organize notes in an Obsidian vault. |

See [`skills/personal/README.md`](skills/personal/README.md) for the personal
skill index.

## Rules

Rules are reusable implementation guidance for agents. They are broader than
skills: a skill defines a workflow, while a rule defines standing project
preferences or architecture patterns.

| File | Purpose |
| --- | --- |
| [`rules/main.md`](rules/main.md) | Entry point that lists the rule set agents should load. |
| [`rules/context7.md`](rules/context7.md) | Requires Context7 for current library, framework, SDK, API, CLI, and cloud-service documentation. |
| [`rules/folders.md`](rules/folders.md) | Keeps new project code in subfolders instead of the repository root. |
| [`rules/git.md`](rules/git.md) | Defines default Git and GitHub workflow expectations. |
| [`rules/credits-and-limits.md`](rules/credits-and-limits.md) | Architecture guidance for credits, limits, account balances, and spend reservations. |

Web-specific rules live in [`rules/web/`](rules/web/):

| File | Purpose |
| --- | --- |
| [`analytics.md`](rules/web/analytics.md) | Consent-aware analytics setup with Plausible, Google Tag Manager, and Yandex.Metrika. |
| [`api.md`](rules/web/api.md) | API implementation guidance. |
| [`async-jobs-and-workers.md`](rules/web/async-jobs-and-workers.md) | Background job, worker, retry, idempotency, and observability patterns. |
| [`auth.md`](rules/web/auth.md) | Google OAuth authentication architecture and security requirements. |
| [`frontend.md`](rules/web/frontend.md) | Frontend stack and design expectations. |
| [`lemonsqueezy.md`](rules/web/lemonsqueezy.md) | Lemon Squeezy checkout, webhook, entitlement, and local data model guidance. |
| [`testing.md`](rules/web/testing.md) | Full-stack testing strategy with Vitest and Playwright expectations. |

## Using This Repository

Use the repository as a source of truth for agent behavior:

1. Point an agent at the relevant `SKILL.md` when a task matches that skill.
2. Load `rules/main.md` when starting a project that should follow these defaults.
3. Copy or symlink selected skills and rules into the agent environment if your
   tool expects skills in a specific local directory.
4. Keep category README files updated whenever you add, rename, or remove a skill.

## Adding A Skill

Use the [`write-a-skill`](skills/productivity/write-a-skill/SKILL.md) workflow.
At minimum, every skill should include:

- A `SKILL.md` file.
- Frontmatter with `name` and `description`.
- A description that says exactly when the agent should use the skill.
- Concise instructions in the main file.
- Supporting references or scripts only when they keep the main skill easier to
  read.

Recommended structure:

```text
skills/<category>/<skill-name>/
├── SKILL.md
├── REFERENCE.md
└── scripts/
```

## Maintenance Notes

- Keep instructions concrete and current.
- Prefer short skill files with links to focused references.
- Avoid time-sensitive claims unless the skill also tells the agent how to verify
  them.
- Do not commit or push changes unless the user explicitly asks for it.
- When a rule depends on current third-party documentation, use Context7 instead
  of relying on memory.
