#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    print("[RUN]", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)


def ensure_git_repo(root: Path) -> None:
    proc = run(["git", "rev-parse", "--is-inside-work-tree"], root)
    if proc.returncode != 0:
        raise RuntimeError("Ce dossier n'est pas un dépôt git. Initialise git ou ouvre le vrai repo.")


def ensure_gh() -> None:
    proc = subprocess.run(["gh", "--version"], text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError("GitHub CLI (gh) introuvable. Installe gh puis connecte-toi avec 'gh auth login'.")


def read_version(root: Path) -> str:
    version_file = root / "resources" / "version.json"
    if not version_file.exists():
        return "3.QUANTUM"
    try:
        payload = json.loads(version_file.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return str(payload.get("version") or "3.QUANTUM").strip()
    except Exception:
        pass
    return "3.QUANTUM"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build + publish GitHub release for JARVIS.")
    parser.add_argument("repo", help="GitHub repo in owner/name format")
    parser.add_argument("--owner", default="darkex", help="Owner GitHub username for build metadata")
    parser.add_argument("--notes", default="", help="Optional release notes")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    ensure_git_repo(root)
    ensure_gh()

    build = subprocess.run(
        [sys.executable, str(root / "build_release_locked.py"), args.owner],
        cwd=str(root),
        text=True,
        capture_output=True,
    )
    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr)
        raise RuntimeError("Build release failed.")

    version = read_version(root)
    tag = f"v{version}"

    add_proc = run(["git", "add", "resources/version.json"], root)
    if add_proc.returncode != 0:
        raise RuntimeError(add_proc.stderr.strip() or "git add failed")

    commit_msg = f"release: {tag}"
    commit_proc = run(["git", "commit", "-m", commit_msg], root)
    if commit_proc.returncode != 0 and "nothing to commit" not in (commit_proc.stdout + commit_proc.stderr).lower():
        raise RuntimeError(commit_proc.stderr.strip() or "git commit failed")

    run(["git", "push", "origin", "HEAD"], root)

    release_asset = root / "release_locked"
    notes = args.notes.strip() or f"JARVIS {tag} released on {datetime.now().isoformat(timespec='seconds')}"

    gh_cmd = [
        "gh",
        "release",
        "create",
        tag,
        str(release_asset / "JARVIS-release-locked"),
        str(release_asset / "RELEASE_INFO.txt"),
        "--repo",
        args.repo,
        "--title",
        f"JARVIS {tag}",
        "--notes",
        notes,
    ]
    rel_proc = run(gh_cmd, root)
    if rel_proc.returncode != 0:
        raise RuntimeError(rel_proc.stderr.strip() or "gh release create failed")

    print(f"[OK] GitHub release published: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
