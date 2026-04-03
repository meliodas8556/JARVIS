#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("[RUN]", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if check and proc.returncode != 0:
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc


def has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def detect_os_family() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "other"


def install_gh_if_missing() -> None:
    if has_tool("gh"):
        print("[OK] GitHub CLI déjà installée.")
        return

    os_family = detect_os_family()
    print(f"[INFO] gh manquant. Tentative d'installation automatique ({os_family})...")

    if os_family == "linux":
        if has_tool("pacman"):
            run(["sudo", "pacman", "-Sy", "--noconfirm", "github-cli"])
            return
        if has_tool("apt-get"):
            run(["sudo", "apt-get", "update"])
            run(["sudo", "apt-get", "install", "-y", "gh"])
            return
        if has_tool("dnf"):
            run(["sudo", "dnf", "install", "-y", "gh"])
            return
        if has_tool("zypper"):
            run(["sudo", "zypper", "--non-interactive", "install", "gh"])
            return
        raise RuntimeError("Gestionnaire Linux non supporté automatiquement. Installe gh manuellement.")

    if os_family == "macos":
        if has_tool("brew"):
            run(["brew", "install", "gh"])
            return
        raise RuntimeError("Homebrew non détecté. Installe gh manuellement: https://cli.github.com/")

    if os_family == "windows":
        if has_tool("winget"):
            run(["winget", "install", "--id", "GitHub.cli", "-e", "--accept-source-agreements", "--accept-package-agreements"])
            return
        if has_tool("choco"):
            run(["choco", "install", "gh", "-y"])
            return
        raise RuntimeError("Aucun installateur Windows détecté (winget/choco). Installe gh manuellement.")

    raise RuntimeError("OS non supporté automatiquement pour l'installation de gh.")


def ensure_git_repo(root: Path, branch: str) -> None:
    is_repo = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, check=False)
    if is_repo.returncode == 0:
        print("[OK] Dépôt git déjà initialisé.")
        return

    print("[INFO] Initialisation du dépôt git...")
    run(["git", "init"], cwd=root)
    # Assure la branche principale attendue
    run(["git", "checkout", "-B", branch], cwd=root)


def ensure_initial_commit(root: Path) -> None:
    has_commit = run(["git", "rev-parse", "--verify", "HEAD"], cwd=root, check=False)
    if has_commit.returncode == 0:
        print("[OK] Le dépôt contient déjà des commits.")
        return

    print("[INFO] Création du commit initial...")
    run(["git", "add", "."], cwd=root)
    run(["git", "commit", "-m", "chore: initial repository setup"], cwd=root)


def ensure_remote(root: Path, repo: str) -> None:
    remote = run(["git", "remote", "get-url", "origin"], cwd=root, check=False)
    expected = f"https://github.com/{repo}.git"

    if remote.returncode == 0:
        current = (remote.stdout or "").strip()
        if current == expected:
            print(f"[OK] Remote origin déjà configuré: {current}")
            return
        print(f"[INFO] Remote origin existant: {current}")
        print(f"[INFO] Remplacement vers: {expected}")
        run(["git", "remote", "set-url", "origin", expected], cwd=root)
        return

    print(f"[INFO] Ajout du remote origin: {expected}")
    run(["git", "remote", "add", "origin", expected], cwd=root)


def ensure_gh_auth() -> None:
    auth = run(["gh", "auth", "status"], check=False)
    if auth.returncode == 0:
        print("[OK] Auth GitHub CLI déjà active.")
        return

    print("[INFO] Auth GitHub requise. Lancement de 'gh auth login' (interactif)...")
    # Commande interactive: on relance sans capture pour permettre l'interaction.
    proc = subprocess.run(["gh", "auth", "login", "--web", "--git-protocol", "https"])
    if proc.returncode != 0:
        raise RuntimeError("Authentification gh échouée. Relance: gh auth login")


def ensure_remote_repo_exists(root: Path, repo: str, private: bool) -> None:
    view = run(["gh", "repo", "view", repo], check=False)
    if view.returncode == 0:
        print(f"[OK] Repo GitHub existe déjà: {repo}")
        return

    visibility = "--private" if private else "--public"
    print(f"[INFO] Création du repo GitHub: {repo}")
    run(
        [
            "gh",
            "repo",
            "create",
            repo,
            visibility,
            "--source",
            str(root),
            "--remote",
            "origin",
        ]
    )


def push_branch(root: Path, branch: str) -> None:
    print(f"[INFO] Push de la branche {branch} vers origin...")
    run(["git", "push", "-u", "origin", branch], cwd=root)


def main() -> int:
    parser = argparse.ArgumentParser(description="One-click setup: install gh + init git + connect GitHub repo")
    parser.add_argument("repo", nargs="?", default="", help="Repo GitHub cible (owner/name), ex: darkex/JARVIS")
    parser.add_argument("--branch", default="main", help="Branche principale à pousser")
    parser.add_argument("--public", action="store_true", help="Créer le repo en public (par défaut privé)")
    parser.add_argument("--skip-push", action="store_true", help="N'effectue pas de push")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    if not has_tool("git"):
        raise RuntimeError("git introuvable. Installe git avant de continuer.")

    install_gh_if_missing()
    ensure_git_repo(root, args.branch)
    ensure_initial_commit(root)
    ensure_gh_auth()

    if args.repo:
        ensure_remote(root, args.repo)
        ensure_remote_repo_exists(root, args.repo, private=not args.public)
        if not args.skip_push:
            push_branch(root, args.branch)
        print(f"[OK] Setup terminé. Repo prêt: https://github.com/{args.repo}")
    else:
        print("[OK] Setup local terminé (git + gh auth).")
        print("[NEXT] Donne un repo cible pour finaliser:")
        print(f"       python3 {Path(__file__).name} owner/repo")

    print("[NEXT] Publie la release en 1 commande:")
    print("       python3 publish_github_release.py owner/repo --owner darkex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
