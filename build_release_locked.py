#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env, cwd=str(cwd) if cwd else None)


def _next_quantum_version(current_version: str) -> str:
    current = str(current_version or "").strip()
    m = re.fullmatch(r"3\.QUANTUM(?:\.(\d+))?", current, flags=re.IGNORECASE)
    if m:
        patch = int(m.group(1) or "0") + 1
        return f"3.QUANTUM.{patch}"
    return f"3.QUANTUM.{datetime.now().strftime('%Y%m%d%H%M')}"


def bump_version_file(root: Path, owner: str) -> str:
    version_file = root / "resources" / "version.json"
    version_file.parent.mkdir(parents=True, exist_ok=True)

    current = "3.QUANTUM"
    payload: dict[str, object] = {}
    if version_file.exists():
        try:
            loaded = json.loads(version_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
                maybe_current = str(loaded.get("version") or "").strip()
                if maybe_current:
                    current = maybe_current
        except Exception:
            payload = {}

    new_version = _next_quantum_version(current)
    payload.update(
        {
            "version": new_version,
            "channel": "stable",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "owner": owner,
        }
    )
    version_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return new_version


def main() -> int:
    parser = argparse.ArgumentParser(description="Build locked JARVIS release executable (cross-platform).")
    parser.add_argument("owner_github", nargs="?", default="darkex", help="Owner GitHub username")
    parser.add_argument("release_signature", nargs="?", default="", help="Optional release signature")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    owner = (args.owner_github or "darkex").strip().lstrip("@")
    signature = (args.release_signature or f"REL-{datetime.now().strftime('%Y%m%d')}-{owner}").strip()

    app_name = "JARVIS-release-locked"
    out_dir = root / "release_locked"
    venv_dir = root / ".jarvis_release_venv"

    print(f"[BUILD] Root: {root}")
    print(f"[BUILD] Owner GitHub: {owner}")
    print(f"[BUILD] Signature: {signature}")

    jarvis_version = bump_version_file(root, owner)
    print(f"[BUILD] Version bumped: {jarvis_version}")

    if not (venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python").exists():
        run([sys.executable, "-m", "venv", str(venv_dir)], cwd=root)

    py = venv_dir / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "pyinstaller"], cwd=root)

    for p in [root / "build", root / "dist", out_dir]:
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["JARVIS_RELEASE_MODE"] = "1"
    env["JARVIS_RELEASE_OWNER"] = owner
    env["JARVIS_RELEASE_SIGNATURE"] = signature
    env["JARVIS_VERSION"] = jarvis_version

    data_sep = ";" if os.name == "nt" else ":"
    add_data_1 = f"{root / 'resources'}{data_sep}resources"
    add_data_2 = f"{root / 'jarvis_modules'}{data_sep}jarvis_modules"

    run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            app_name,
            "--add-data",
            add_data_1,
            "--add-data",
            add_data_2,
            str(root / "JARVIS.py"),
        ],
        env=env,
        cwd=root,
    )

    exe_name = f"{app_name}.exe" if os.name == "nt" else app_name
    built_exe = root / "dist" / exe_name
    if not built_exe.exists():
        raise FileNotFoundError(f"Executable not found: {built_exe}")

    target_exe = out_dir / exe_name
    shutil.copy2(built_exe, target_exe)
    if os.name != "nt":
        target_exe.chmod(0o755)

    release_info = out_dir / "RELEASE_INFO.txt"
    release_info.write_text(
        "\n".join(
            [
                f"App: {app_name}",
                "Release mode: ON",
                f"JARVIS version: v{jarvis_version}",
                f"Owner GitHub: {owner}",
                f"Release signature: {signature}",
                f"Built at: {datetime.now().isoformat(timespec='seconds')}",
                "",
                "Distribution notes:",
                "- Share only this release_locked folder.",
                "- Do not share JARVIS.py or source tree.",
                "- In release mode, dev/code-edit/plugin features are locked.",
            ]
        ),
        encoding="utf-8",
    )

    print(f"[OK] Build complete: {target_exe}")
    print(f"[OK] Release info: {release_info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
