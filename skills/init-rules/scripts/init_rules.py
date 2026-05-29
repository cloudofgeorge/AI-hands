#!/usr/bin/env python3
"""Install cloudofgeorge/ai-rules into a project's rules directory."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


DEFAULT_REPO = "https://github.com/cloudofgeorge/ai-rules.git"


def run_git_clone(repo: str, destination: Path, ref: str | None) -> None:
    command = ["git", "clone", "--depth", "1"]
    if ref:
        command.extend(["--branch", ref])
    command.extend([repo, str(destination)])

    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        raise SystemExit("git is required but was not found on PATH") from None
    except subprocess.CalledProcessError as error:
        output = error.stdout.strip() if error.stdout else "git clone failed"
        raise SystemExit(output) from None

    if completed.stdout.strip():
        print(completed.stdout.strip())


def directory_has_entries(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def backup_path_for(destination: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = destination.with_name(f"{destination.name}.backup.{timestamp}")
    suffix = 1
    while candidate.exists():
        candidate = destination.with_name(f"{destination.name}.backup.{timestamp}.{suffix}")
        suffix += 1
    return candidate


def copy_repository_contents(source: Path, destination: Path) -> None:
    source = source.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name == ".git"}
        if Path(directory).resolve() == source:
            ignored.update(name for name in names if name.lower() == "readme.md")
        return ignored

    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)


def install_rules(
    project_dir: Path,
    repo: str,
    ref: str | None,
    force: bool,
    no_backup: bool,
) -> int:
    project_dir = project_dir.expanduser().resolve()
    if not project_dir.exists():
        raise SystemExit(f"Project directory does not exist: {project_dir}")
    if not project_dir.is_dir():
        raise SystemExit(f"Project path is not a directory: {project_dir}")

    destination = project_dir / "rules"
    backup_path: Path | None = None

    if destination.exists() and not destination.is_dir():
        raise SystemExit(f"Destination exists and is not a directory: {destination}")

    if directory_has_entries(destination) and not force:
        print(f"rules directory already exists and is not empty: {destination}", file=sys.stderr)
        print("Rerun with --force to replace it. A backup is created by default.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="init-rules-") as tmp:
        clone_dir = Path(tmp) / "repo"
        run_git_clone(repo, clone_dir, ref)

        if directory_has_entries(destination):
            if no_backup:
                shutil.rmtree(destination)
            else:
                backup_path = backup_path_for(destination)
                shutil.move(str(destination), str(backup_path))

        destination.mkdir(parents=True, exist_ok=True)

        try:
            copy_repository_contents(clone_dir, destination)
        except Exception:
            if backup_path and backup_path.exists():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.move(str(backup_path), str(destination))
            raise

    print(f"Installed ai-rules into: {destination}")
    if backup_path:
        print(f"Backup created at: {backup_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install cloudofgeorge/ai-rules into <project-dir>/rules.",
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Project directory to receive the rules/ folder. Defaults to the current directory.",
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"Git repository to clone. Defaults to {DEFAULT_REPO}",
    )
    parser.add_argument(
        "--ref",
        default=None,
        help="Optional branch, tag, or ref to clone.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing non-empty rules/ directory.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not back up an existing rules/ directory when using --force.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return install_rules(
        project_dir=Path(args.project_dir),
        repo=args.repo,
        ref=args.ref,
        force=args.force,
        no_backup=args.no_backup,
    )


if __name__ == "__main__":
    raise SystemExit(main())
