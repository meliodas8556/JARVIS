#!/usr/bin/env python3
"""
publish_multi_os_release.py
===========================
One-click script to:
  1. Bump the version (resources/version.json)
  2. Commit + push all pending code changes
  3. Trigger the GitHub Actions multi-OS build workflow
  4. Wait for the workflow run to complete
  5. Download the 3 binary artifacts (linux, macos, windows)
  6. Create a new GitHub release and upload the 3 assets

Usage:
    python3 publish_multi_os_release.py
    python3 publish_multi_os_release.py --repo meliodas8556/JARVIS --notes "Bug fixes"
    python3 publish_multi_os_release.py --no-bump   # keep current version, only publish
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_DEFAULT = "meliodas8556/JARVIS"
OWNER_DEFAULT = "meliodas8556"
WORKFLOW_FILE = "build-multi-os.yml"
POLL_INTERVAL = 20   # seconds between status polls
POLL_TIMEOUT = 1800  # 30 min max wait


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("[RUN]", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)


def _run_ok(cmd: list[str], cwd: Path | None = None) -> bool:
    return _run(cmd, cwd=cwd, check=False).returncode == 0


def _check(proc: subprocess.CompletedProcess[str], label: str) -> str:
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"[FAIL] {label}: {err}")
    return (proc.stdout or "").strip()


def read_version(root: Path) -> str:
    vf = root / "resources" / "version.json"
    if vf.exists():
        try:
            data = json.loads(vf.read_text(encoding="utf-8"))
            v = str(data.get("version", "")).strip()
            if v:
                return v
        except Exception:
            pass
    return "3.QUANTUM"


def bump_version(root: Path, owner: str) -> str:
    """Bump the patch counter in resources/version.json and return the new version string."""
    import re
    vf = root / "resources" / "version.json"
    current = read_version(root)
    m = re.fullmatch(r"3\.QUANTUM(?:\.(\d+))?", current, flags=re.IGNORECASE)
    if m:
        patch = int(m.group(1) or "0") + 1
        new_version = f"3.QUANTUM.{patch}"
    else:
        new_version = f"3.QUANTUM.{datetime.now().strftime('%Y%m%d%H%M')}"

    payload: dict = {}
    if vf.exists():
        try:
            payload = json.loads(vf.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    payload.update({
        "version": new_version,
        "channel": "stable",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "owner": owner,
    })
    vf.parent.mkdir(parents=True, exist_ok=True)
    vf.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[VERSION] {current} → {new_version}")
    return new_version


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def commit_and_push(root: Path, version: str) -> None:
    # Safety: this repository may contain many unrelated tracked files.
    # Only commit the version bump file produced by this release flow.
    _run(["git", "add", "resources/version.json"], root, check=False)

    staged = _run(["git", "diff", "--cached", "--name-only"], root)
    if not (staged.stdout or "").strip():
        print("[GIT] No staged release metadata changes; skipping commit.")
    else:
        msg = f"release: v{version} - multi-OS build"
        result = _run(["git", "commit", "-m", msg], root)
        stdout_stderr = (result.stdout + result.stderr).lower()
        if result.returncode != 0 and "nothing to commit" not in stdout_stderr:
            raise RuntimeError(f"git commit failed: {result.stderr.strip()}")
        print(f"[GIT] Committed: {msg}")
    _check(_run(["git", "push", "origin", "HEAD"], root), "git push")
    print("[GIT] Pushed to origin.")


# ---------------------------------------------------------------------------
# GitHub Actions
# ---------------------------------------------------------------------------

def trigger_workflow(repo: str, root: Path) -> str:
    """Trigger the multi-OS workflow and return its run ID."""
    before = _get_latest_run_id(repo)

    proc = _run(["gh", "workflow", "run", WORKFLOW_FILE, "--repo", repo], root)
    _check(proc, "gh workflow run")
    print(f"[WORKFLOW] Triggered {WORKFLOW_FILE} on {repo}")

    # Wait for GitHub to register the new run (up to 60 s)
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(5)
        run_id = _get_latest_run_id(repo)
        if run_id and run_id != before:
            print(f"[WORKFLOW] Run ID: {run_id}")
            return run_id
    raise RuntimeError("Could not detect new workflow run within 60 s. Check GitHub Actions manually.")


def _get_latest_run_id(repo: str) -> str:
    proc = _run([
        "gh", "api",
        f"repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs",
        "--jq", ".workflow_runs[0].id | tostring",
    ])
    return (proc.stdout or "").strip()


def wait_for_run(repo: str, run_id: str) -> None:
    """Poll until the workflow run finishes, then raise if it failed."""
    print(f"[WORKFLOW] Polling run {run_id} (timeout {POLL_TIMEOUT}s)...")
    deadline = time.time() + POLL_TIMEOUT
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}"

    while time.time() < deadline:
        proc = _run([
            "gh", "api",
            f"repos/{repo}/actions/runs/{run_id}",
            "--jq", "{status:.status,conclusion:.conclusion}",
        ])
        try:
            info = json.loads(proc.stdout.strip())
        except Exception:
            time.sleep(POLL_INTERVAL)
            continue

        status = info.get("status", "")
        conclusion = info.get("conclusion", "")
        print(f"[WORKFLOW] Status: {status} | Conclusion: {conclusion or '…'}")

        if status == "completed":
            if conclusion == "success":
                print("[WORKFLOW] Build succeeded!")
                return
            raise RuntimeError(
                f"Workflow run {run_id} ended with conclusion '{conclusion}'.\n"
                f"Details: {run_url}"
            )
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(
        f"Workflow run {run_id} timed out after {POLL_TIMEOUT}s.\n"
        f"Details: {run_url}"
    )


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

def download_artifacts(run_id: str, dest: Path) -> list[Path]:
    """Download all artifacts from a run into dest/, return list of asset paths."""
    dest.mkdir(parents=True, exist_ok=True)
    proc = _run(["gh", "run", "download", run_id, "-D", str(dest)])
    _check(proc, "gh run download")
    print(f"[ARTIFACTS] Downloaded to {dest}")

    # Collect actual files recursively because upload-artifact may preserve subdirectories.
    assets: list[Path] = []
    for item in sorted(dest.iterdir()):
        if item.is_dir():
            for f in sorted(path for path in item.rglob("*") if path.is_file()):
                assets.append(f)
                print(f"[ARTIFACTS]   {f.relative_to(dest)}")
        elif item.is_file():
            assets.append(item)
            print(f"[ARTIFACTS]   {item.name}")
    if not assets:
        raise RuntimeError(f"No artifact files found inside {dest}")
    return assets


# ---------------------------------------------------------------------------
# GitHub Release
# ---------------------------------------------------------------------------

def create_or_update_release(repo: str, tag: str, notes: str, assets: list[Path], root: Path) -> None:
    """Create the GitHub release (or update if already exists) and upload all assets."""
    # Delete existing release + tag if present (to allow re-publish cleanly)
    existing = _run(["gh", "release", "view", tag, "--repo", repo], root)
    if existing.returncode == 0:
        print(f"[RELEASE] Existing release {tag} found — deleting before re-create.")
        _run(["gh", "release", "delete", tag, "--repo", repo, "--yes", "--cleanup-tag"], root)

    cmd = [
        "gh", "release", "create", tag,
        "--repo", repo,
        "--title", f"JARVIS {tag}",
        "--notes", notes,
    ]
    for asset in assets:
        cmd.append(str(asset))

    _check(_run(cmd, root), "gh release create")
    print(f"[RELEASE] Published: https://github.com/{repo}/releases/tag/{tag}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="One-click multi-OS JARVIS release publisher.")
    parser.add_argument("--repo", default=REPO_DEFAULT, help=f"GitHub repo (default: {REPO_DEFAULT})")
    parser.add_argument("--owner", default=OWNER_DEFAULT, help=f"Owner name for version metadata (default: {OWNER_DEFAULT})")
    parser.add_argument("--notes", default="", help="Release notes (optional)")
    parser.add_argument("--no-bump", action="store_true", help="Skip version bump, use current version as-is")
    parser.add_argument("--no-push", action="store_true", help="Skip git commit/push (useful if already pushed)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    # Preflight checks
    if not _run_ok(["git", "rev-parse", "--is-inside-work-tree"], root):
        print("[ERROR] Not inside a git repository.")
        return 1
    if not _run_ok(["gh", "--version"]):
        print("[ERROR] GitHub CLI (gh) not found. Install it and run 'gh auth login'.")
        return 1

    # 1. Bump version
    if args.no_bump:
        version = read_version(root)
        print(f"[VERSION] Using current version: {version}")
    else:
        version = bump_version(root, args.owner)

    tag = f"v{version}"

    # 2. Commit + push
    if not args.no_push:
        commit_and_push(root, version)

    # 3. Trigger multi-OS workflow
    run_id = trigger_workflow(args.repo, root)

    # 4. Wait for completion
    wait_for_run(args.repo, run_id)

    # 5. Download artifacts
    artifacts_dir = root / "multi_os_binaries" / f"run_{run_id}"
    assets = download_artifacts(run_id, artifacts_dir)

    # 6. Create release + upload
    notes = args.notes.strip() or (
        f"JARVIS {tag} — release automatique multi-OS\n"
        f"Plateformes: Linux, macOS, Windows\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    create_or_update_release(args.repo, tag, notes, assets, root)

    print()
    print(f"✓ Release {tag} publiée avec {len(assets)} assets.")
    print(f"  → https://github.com/{args.repo}/releases/tag/{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
