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


def write_windows_installer_script(root: Path, out_dir: Path, app_name: str, owner: str, version: str) -> Path:
    installer_script = root / "JARVIS-windows-installer.iss"
    output_dir = str(out_dir).replace("\\", "\\\\")
    source_glob = str(out_dir / "*").replace("\\", "\\\\")
    setup_text = "\n".join(
        [
            '#define MyAppName "JARVIS"',
            f'#define MyAppVersion "{version}"',
            f'#define MyAppPublisher "{owner}"',
            f'#define MyAppExeName "{app_name}.exe"',
            "",
            "[Setup]",
            "AppId={{7A892C77-95C4-4FD4-9D3A-4A7AA5C6620D}}",
            "AppName={#MyAppName}",
            "AppVersion={#MyAppVersion}",
            "AppPublisher={#MyAppPublisher}",
            "DefaultDirName={localappdata}\\Programs\\JARVIS",
            "DefaultGroupName=JARVIS",
            "UninstallDisplayIcon={app}\\{#MyAppExeName}",
            "Compression=lzma2/max",
            "SolidCompression=yes",
            "WizardStyle=modern",
            f"OutputDir={output_dir}",
            "OutputBaseFilename=JARVIS-setup-windows",
            "ArchitecturesAllowed=x64compatible",
            "ArchitecturesInstallIn64BitMode=x64compatible",
            "PrivilegesRequired=lowest",
            "PrivilegesRequiredOverridesAllowed=dialog",
            "SetupLogging=yes",
            "",
            "[Languages]",
            'Name: "english"; MessagesFile: "compiler:Default.isl"',
            "",
            "[Tasks]",
            'Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked',
            "",
            "[Files]",
            f'Source: "{source_glob}"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs',
            "",
            "[Icons]",
            'Name: "{group}\\JARVIS"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"',
            'Name: "{autodesktop}\\JARVIS"; Filename: "{app}\\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon',
            "",
            "[Run]",
            'Filename: "{app}\\{#MyAppExeName}"; Description: "Launch JARVIS"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent',
            "",
        ]
    )
    installer_script.write_text(setup_text, encoding="utf-8")
    return installer_script


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

    pyinstaller_cmd = [
        str(py),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        app_name,
        "--add-data",
        add_data_1,
        "--add-data",
        add_data_2,
        str(root / "JARVIS.py"),
    ]

    if os.name == "nt":
        # onedir is larger but significantly more stable on Windows than onefile self-extraction.
        pyinstaller_cmd.insert(4, "--onedir")
    else:
        pyinstaller_cmd.insert(4, "--onefile")

    run(pyinstaller_cmd, env=env, cwd=root)

    exe_name = f"{app_name}.exe" if os.name == "nt" else app_name
    build_output_path = out_dir / exe_name
    if os.name == "nt":
        built_dir = root / "dist" / app_name
        built_exe = built_dir / exe_name
        if not built_exe.exists():
            raise FileNotFoundError(f"Executable not found: {built_exe}")
        shutil.copytree(built_dir, out_dir, dirs_exist_ok=True)
        build_output_path = out_dir

        launcher = out_dir / "LANCER_JARVIS.bat"
        launcher.write_text(
            "@echo off\n"
            "cd /d %~dp0\n"
            f'start "" "{exe_name}"\n',
            encoding="utf-8",
        )

        install_help = out_dir / "INSTALL_WINDOWS.txt"
        install_help.write_text(
            "JARVIS Windows - installation\r\n"
            "================================\r\n"
            "1. Extraire tout le contenu du fichier ZIP dans un dossier normal.\r\n"
            "2. Ne pas lancer JARVIS directement depuis l'archive ZIP.\r\n"
            "3. Ouvrir le dossier extrait.\r\n"
            "4. Double-cliquer sur LANCER_JARVIS.bat.\r\n"
            "5. Si Windows SmartScreen affiche un avertissement, cliquer sur Informations complementaires puis Executer quand meme.\r\n"
            "\r\n"
            "Cette version utilise un package onedir plus stable pour eviter les crashs lies a l'extraction onefile.\r\n",
            encoding="utf-8",
        )
    else:
        built_exe = root / "dist" / exe_name
        if not built_exe.exists():
            raise FileNotFoundError(f"Executable not found: {built_exe}")

        target_exe = out_dir / exe_name
        shutil.copy2(built_exe, target_exe)
        target_exe.chmod(0o755)
        build_output_path = target_exe

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
                "- On Windows: extract the ZIP first, then run LANCER_JARVIS.bat.",
            ]
        ),
        encoding="utf-8",
    )

    if os.name == "nt":
        installer_script = write_windows_installer_script(root, out_dir, app_name, owner, jarvis_version)
        print(f"[OK] Windows installer script: {installer_script}")

    print(f"[OK] Build complete: {build_output_path}")
    print(f"[OK] Release info: {release_info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
