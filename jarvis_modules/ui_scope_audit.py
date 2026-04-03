from __future__ import annotations

import threading
from typing import Any

import tkinter as tk


def build_osint_scope_audit_tab(app: Any, parent: Any) -> dict[str, Any]:
    top = tk.Frame(parent, bg="#010810")
    top.pack(fill="x", padx=10, pady=10)
    status_var = tk.StringVar(value="Campagne scope prête. Active le mode pentest légal avec un scope défini.")
    tk.Label(
        top,
        textvariable=status_var,
        bg="#010810",
        fg="#00d9ff",
        font=("Consolas", 10, "bold"),
        anchor="w",
    ).pack(side="left", fill="x", expand=True)

    dns_mode_var = tk.StringVar(value=app.osint_dns_live_mode.upper())
    tk.Label(top, text="DNS LIVE:", bg="#010810", fg="#7edbff", font=("Consolas", 9, "bold")).pack(side="left", padx=(10, 4))
    mode_menu = tk.OptionMenu(top, dns_mode_var, "OFF", "COMPACT", "VERBOSE")
    mode_menu.configure(
        bg="#001621",
        fg="#9be8ff",
        activebackground="#003344",
        activeforeground="#00e5ff",
        font=("Consolas", 9, "bold"),
        highlightthickness=1,
        highlightbackground="#005f7a",
        bd=0,
    )
    mode_menu["menu"].configure(bg="#001621", fg="#9be8ff", activebackground="#003344", activeforeground="#00e5ff")
    mode_menu.pack(side="left", padx=(0, 6))

    out = tk.Text(
        parent,
        bg="#010810",
        fg="#00ff88",
        font=("Consolas", 10),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground="#005f7a",
        wrap="word",
        padx=12,
        pady=10,
    )
    out.pack(fill="both", expand=True, padx=10, pady=(0, 4))
    app._configure_osint_output_widget(out)

    def sync_dns_mode(*_args):
        mode = dns_mode_var.get().strip().lower()
        app.osint_dns_live_mode = mode if mode in {"off", "compact", "verbose"} else "compact"
        report = getattr(out, "_osint_report", None)
        if isinstance(report, dict):
            report["dns_live_mode"] = app.osint_dns_live_mode

    dns_mode_var.trace_add("write", sync_dns_mode)

    def launch():
        threading.Thread(target=osint_run_full_scope_audit, args=(app, out, status_var), daemon=True).start()

    tk.Button(
        top,
        text="▶ AUDIT COMPLET DU SCOPE",
        command=launch,
        bg="#4a1a10",
        fg="#ffb36a",
        activebackground="#ff8a3d",
        activeforeground="#010810",
        font=("Consolas", 10, "bold"),
        relief="flat",
        padx=16,
        pady=4,
        cursor="hand2",
    ).pack(side="left", padx=(10, 0))

    app._add_osint_export_buttons(top, out)

    tk.Button(
        top,
        text="EXPORT TOUT LE SCOPE",
        command=lambda: threading.Thread(target=app._export_osint_scope_batch, args=(out,), daemon=True).start(),
        bg="#1a1a10",
        fg="#ffdd77",
        activebackground="#ccaa00",
        activeforeground="#010810",
        font=("Consolas", 9, "bold"),
        relief="flat",
        padx=10,
        pady=4,
        cursor="hand2",
    ).pack(side="left", padx=(6, 0))

    return {"out": out, "status_var": status_var, "launch": launch}


def osint_launch_scope_audit_from_header(app: Any, notebook: Any, scope_tab: Any) -> None:
    notebook.select(scope_tab)
    controls = app.osint_panel_state.get("scope_controls", {}) if isinstance(app.osint_panel_state, dict) else {}
    launcher = controls.get("launch") if isinstance(controls, dict) else None
    if callable(launcher):
        launcher()


def osint_run_full_scope_audit(app: Any, out: Any, status_var: Any) -> None:
    if not app.pentest_mode_enabled:
        status_var.set("Mode pentest légal requis pour lancer l'audit complet du scope.")
        app._osint_start_output(out, "Scope Audit", "", "◈ SCOPE AUDIT → refusé")
        app._osint_append(out, "Active d'abord le mode pentest légal.", "err")
        return
    if not app.pentest_scope_targets:
        status_var.set("Aucun scope pentest défini.")
        app._osint_start_output(out, "Scope Audit", "", "◈ SCOPE AUDIT → scope vide")
        app._osint_append(out, "Définis au moins une cible autorisée avant de lancer la campagne.", "err")
        return

    scope_label = ", ".join(app.pentest_scope_targets)
    status_var.set(f"Campagne en cours sur {len(app.pentest_scope_targets)} cible(s)...")
    app._osint_start_output(out, "Scope Audit", scope_label, f"◈ SCOPE AUDIT → {scope_label}")

    modules = [
        ("Exposure Audit", app._osint_run_exposure_audit),
        ("Auth Surface", app._osint_run_auth_surface_audit),
        ("Secrets Exposure", app._osint_run_secret_exposure_audit),
        ("Synthetic Creds", app._osint_run_synthetic_credential_controls),
    ]
    n_targets = len(app.pentest_scope_targets)

    for index, target in enumerate(app.pentest_scope_targets, start=1):
        report = getattr(out, "_osint_report", None)
        if isinstance(report, dict):
            report["current_target"] = target
        status_var.set(f"[{index}/{n_targets}] {target}...")
        app._osint_section(out, f"TARGET {index}/{n_targets} — {target}")
        for module_name, runner in modules:
            if isinstance(report, dict):
                report["current_module"] = module_name
            app._osint_append(out, f"[MODULE] {module_name} — {target}", "hdr")
            try:
                runner(target, out)
            except Exception as exc:
                app._osint_append(out, f"Échec module {module_name} sur {target}: {exc}", "err")

    report = getattr(out, "_osint_report", None)
    if isinstance(report, dict):
        report.pop("current_target", None)
        report.pop("current_module", None)

    def finish_on_main() -> None:
        payload = app._osint_build_report_payload(out)
        if payload:
            score = payload["summary"]["severity_score"]
            label = payload["summary"]["severity_label"]
            score_txt = f" — Score global : {score}/10 {label}"
        else:
            score_txt = ""
        status_var.set(f"Campagne terminée sur {n_targets} cible(s).{score_txt}")
        out.configure(state="normal")
        out.insert("end", f"\n◈ Audit complet du scope terminé.{score_txt}\n", "hdr")
        out.configure(state="disabled")
        out.see("end")

    out.after(600, finish_on_main)


# Backward-compatible aliases kept for external callers.
def launch_osint_scope_audit_from_header(app: Any, notebook: Any, scope_tab: Any) -> None:
    osint_launch_scope_audit_from_header(app, notebook, scope_tab)


def run_full_scope_osint_audit(app: Any, out: Any, status_var: Any) -> None:
    osint_run_full_scope_audit(app, out, status_var)
