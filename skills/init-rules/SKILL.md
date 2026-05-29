---
name: init-rules
description: Install the cloudofgeorge/ai-rules GitHub repository into the current project's rules/ directory. Use when the user invokes /init-rules or asks to initialize, download, copy, sync, or set up ai-rules rules in a project.
---

# Init Rules

## Overview

Use this skill to populate a project's `rules/` directory from `https://github.com/cloudofgeorge/ai-rules`.

Treat `/init-rules` as a request to install those rules into the project where the command is being executed. If the project path is unclear, use the current working directory.

## Workflow

1. Resolve the target project directory.
2. Run the bundled installer script:

```bash
python3 <skill-dir>/scripts/init_rules.py <project-dir>
```

3. If `rules/` already exists and is not empty, the script stops without changing files. Ask whether to replace it, then rerun with `--force` if the user agrees:

```bash
python3 <skill-dir>/scripts/init_rules.py <project-dir> --force
```

4. If the command fails because network access or GitHub access is sandboxed, request approval and rerun the same command.
5. Report the installed `rules/` path and any backup path printed by the script.

## Installer Behavior

The script clones the GitHub repository into a temporary directory, copies all repository contents except `.git/` and the repository root `readme.md` file into `<project-dir>/rules`, and removes the temporary clone when finished.

With `--force`, it replaces an existing non-empty `rules/` directory. By default it first moves the old directory to a timestamped sibling such as `rules.backup.20260505-183000`. Use `--no-backup` only when the user explicitly wants no backup.
