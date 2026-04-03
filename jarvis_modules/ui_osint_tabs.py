from __future__ import annotations

# UI builders for OSINT panel, generic tabs and AI routing tab.

import re
import threading
from typing import Any

import tkinter as tk
from tkinter import ttk


# Main OSINT window orchestration.
def osint_open_panel(app: Any) -> None:
    win = tk.Toplevel(app.root)
    win.title("◈ JARVIS — OSINT CONSOLE")
    win.geometry("1260x820")
    win.configure(bg="#010810")
    win.resizable(True, True)

    hdr = tk.Frame(win, bg="#000c18", highlightthickness=1, highlightbackground="#00b8d9")
    hdr.pack(fill="x", padx=8, pady=(8, 0))
    tk.Label(
        hdr,
        text="◈  OSINT  //  ALL SOURCE INTELLIGENCE GATHERING  //  JARVIS RECON MODULE",
        bg="#000c18",
        fg="#00e5ff",
        font=("Consolas", 13, "bold"),
        anchor="w",
    ).pack(side="left", padx=14, pady=8)

    actions = tk.Frame(hdr, bg="#000c18")
    actions.pack(side="right", padx=10)
    legal_label = tk.Label(
        actions,
        text="LEGAL USE ONLY — TARGETS YOU OWN OR HAVE PERMISSION TO QUERY",
        bg="#000c18",
        fg="#ff8844",
        font=("Consolas", 8, "bold"),
    )
    legal_label.pack(side="right", padx=(10, 4))

    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=8, pady=8)

    def tab(title: str) -> Any:
        frame = tk.Frame(nb, bg="#010810")
        nb.add(frame, text=title)
        return frame

    app._build_osint_generic_tab(tab("◈ IP / GeoIP"), "Adresse IP cible", lambda ip, out: app._osint_run_ip(ip, out))
    app._build_osint_generic_tab(tab("◈ Domaine"), "Domaine (ex: example.com)", lambda d, out: app._osint_run_domain(d, out))
    app._build_osint_generic_tab(tab("◈ Username"), "Nom d'utilisateur", lambda u, out: app._osint_run_username(u, out))
    app._build_osint_generic_tab(tab("◈ Email"), "Adresse email", lambda e, out: app._osint_run_email(e, out))
    app._build_osint_cred_research_tab(tab("◈ Cred Research"))
    app._build_osint_port_tab(tab("◈ Port Scanner"))
    app._build_osint_generic_tab(tab("◈ Subdomains"), "Domaine racine (ex: example.com)", lambda d, out: app._osint_run_subdomain(d, out))
    app._build_osint_generic_tab(tab("◈ Hash ID"), "Hash à identifier", lambda h, out: app._osint_run_hash(h, out))
    app._build_osint_generic_tab(tab("◈ MAC Vendor"), "Adresse MAC (ex: AA:BB:CC:DD:EE:FF)", lambda m, out: app._osint_run_mac(m, out))
    app._build_osint_generic_tab(tab("◈ Wayback"), "URL (ex: example.com/page)", lambda u, out: app._osint_run_wayback(u, out))
    app._build_osint_generic_tab(tab("◈ Cert Search"), "Domaine (crt.sh)", lambda d, out: app._osint_run_cert(d, out))
    app._build_osint_dork_tab(tab("◈ Dork Builder"))
    app._build_osint_generic_tab(tab("◈ Phone"), "Numéro (ex: +33612345678)", lambda p, out: app._osint_run_phone(p, out))
    app._build_osint_generic_tab(tab("◈ WHOIS"), "Domaine ou IP", lambda t, out: app._osint_run_whois(t, out))
    app._build_osint_generic_tab(tab("◈ Exposure Audit"), "Email, domaine ou URL autorisé(e)", lambda t, out: app._osint_run_exposure_audit(t, out))
    app._build_osint_generic_tab(tab("◈ Auth Surface"), "Portail auth / domaine / URL autorisé", lambda t, out: app._osint_run_auth_surface_audit(t, out))
    app._build_osint_generic_tab(tab("◈ Secrets Exposure"), "Site / domaine / URL autorisé", lambda t, out: app._osint_run_secret_exposure_audit(t, out))
    app._build_osint_generic_tab(tab("◈ Synthetic Creds"), "Domaine / URL autorisé pour tests", lambda t, out: app._osint_run_synthetic_credential_controls(t, out))

    scope_tab = tab("◈ Scope Audit")
    scope_controls = app._build_osint_scope_audit_tab(scope_tab)
    app._build_osint_ai_tab(tab("◈ AI OSINT"))
    app.osint_panel_state = {"window": win, "notebook": nb, "scope_controls": scope_controls}

    scope_button = tk.Button(
        actions,
        text=f"▶ AUDIT COMPLET DU SCOPE ({len(app.pentest_scope_targets)})",
        command=lambda: app._launch_osint_scope_audit_from_header(nb, scope_tab),
        bg="#4a1a10" if app.pentest_mode_enabled else "#252b33",
        fg="#ffb36a" if app.pentest_mode_enabled else "#7d8fa5",
        activebackground="#ff8a3d" if app.pentest_mode_enabled else "#364252",
        activeforeground="#010810",
        font=("Consolas", 9, "bold"),
        relief="flat",
        padx=12,
        pady=4,
        cursor="hand2",
    )
    scope_button.pack(side="right", padx=(0, 8))


# Generic single-target tab builder.
def build_osint_generic_tab(app: Any, parent: Any, label: str, run_func: Any) -> None:
    top = tk.Frame(parent, bg="#010810")
    top.pack(fill="x", padx=10, pady=10)
    tk.Label(top, text=label, bg="#010810", fg="#00d9ff", font=("Consolas", 10, "bold"), width=46, anchor="w").pack(side="left")

    entry = tk.Entry(
        top,
        bg="#020f1c",
        fg="#d6f5ff",
        font=("Consolas", 12),
        insertbackground="#00e5ff",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground="#005f7a",
        highlightcolor="#00ccee",
    )
    entry.pack(side="left", fill="x", expand=True, padx=(6, 0), ipady=6)

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

    scroll = ttk.Scrollbar(parent, orient="vertical", command=out.yview)
    scroll.pack_forget()
    out.configure(yscrollcommand=scroll.set)
    app._configure_osint_output_widget(out)

    def launch() -> None:
        target = entry.get().strip()
        if not target:
            return
        app._osint_start_output(out, "Generic OSINT", target, f"◈ OSINT QUERY → {target}")
        threading.Thread(target=run_func, args=(target, out), daemon=True).start()

    btn = tk.Button(
        top,
        text="▶ LAUNCH",
        command=launch,
        bg="#003344",
        fg="#00e5ff",
        activebackground="#00b8d9",
        activeforeground="#010810",
        font=("Consolas", 10, "bold"),
        relief="flat",
        padx=16,
        pady=4,
        cursor="hand2",
    )
    btn.pack(side="left", padx=(8, 0))
    app._add_osint_export_buttons(top, out)
    entry.bind("<Return>", lambda _e: launch())


# AI-assisted OSINT tab builder.
def build_osint_ai_tab(app: Any, parent: Any) -> None:
    tk.Label(
        parent,
        text="Décris ta recherche OSINT — JARVIS détecte la cible et lance les outils automatiquement.",
        bg="#010810",
        fg="#00d9ff",
        font=("Consolas", 10, "bold"),
        wraplength=900,
        justify="left",
    ).pack(padx=12, pady=8, anchor="w")

    top = tk.Frame(parent, bg="#010810")
    top.pack(fill="x", padx=10, pady=(0, 6))
    entry = tk.Text(
        top,
        bg="#020f1c",
        fg="#d6f5ff",
        font=("Consolas", 11),
        height=3,
        insertbackground="#00e5ff",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground="#005f7a",
        padx=8,
        pady=6,
        wrap="word",
    )
    entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

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

    def launch() -> None:
        query = entry.get("1.0", "end").strip()
        if not query:
            return
        app._osint_start_output(out, "AI OSINT", query[:120], f"◈ AI OSINT → {query}")
        threading.Thread(target=app._osint_auto_route, args=(query, out), daemon=True).start()

    tk.Button(
        top,
        text="▶ ANALYSER",
        command=launch,
        bg="#003344",
        fg="#00e5ff",
        activebackground="#00b8d9",
        font=("Consolas", 10, "bold"),
        relief="flat",
        padx=14,
        pady=4,
        cursor="hand2",
    ).pack(side="left", anchor="n")
    app._add_osint_export_buttons(top, out)
    entry.bind("<Control-Return>", lambda _e: launch())


# Query router used by the AI OSINT tab.
def osint_auto_route(app: Any, query: str, out: Any) -> None:
    ip_re = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    email_re = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
    hash_re = re.compile(r"\b[0-9a-fA-F]{32,128}\b")
    mac_re = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b")
    domain_re = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b")

    lowered = query.lower()
    ips = ip_re.findall(query)
    emails = email_re.findall(query)
    hashes = hash_re.findall(query)
    macs = mac_re.findall(query)
    domains = [
        d for d in domain_re.findall(query)
        if d not in emails and not any(c.isdigit() for c in d.split(".")[-1]) and d not in (ips or [])
    ]

    dispatched = False
    for email in emails[:2]:
        app._osint_append(out, f"[EMAIL] → {email}", "hdr")
        app._osint_run_email(email, out)
        dispatched = True
    for ip in ips[:2]:
        app._osint_append(out, f"[IP] → {ip}", "hdr")
        app._osint_run_ip(ip, out)
        dispatched = True
    for mac in macs[:2]:
        app._osint_append(out, f"[MAC] → {mac}", "hdr")
        app._osint_run_mac(mac, out)
        dispatched = True
    for h in hashes[:2]:
        app._osint_append(out, f"[HASH] → {h[:16]}...", "hdr")
        app._osint_run_hash(h, out)
        dispatched = True

    if domains and not ips:
        for domain in domains[:2]:
            app._osint_append(out, f"[DOMAINE] → {domain}", "hdr")
            app._osint_run_domain(domain, out)
            dispatched = True

    primary_target = emails[0] if emails else (domains[0] if domains else "")
    if primary_target and re.search(r"\b(fuite|breach|leak|expos[ée]|credential|compromis)\b", lowered):
        app._osint_append(out, f"[EXPOSURE AUDIT] → {primary_target}", "hdr")
        app._osint_run_exposure_audit(primary_target, out)
        dispatched = True

    if domains and re.search(r"\b(mfa|2fa|otp|totp|reset|lockout|bruteforce|connexion|login|auth)\b", lowered):
        app._osint_append(out, f"[AUTH SURFACE] → {domains[0]}", "hdr")
        app._osint_run_auth_surface_audit(domains[0], out)
        dispatched = True

    if domains and re.search(r"\b(secret|secrets|token|api key|apikey|env|\.env|git|private key|jwt)\b", lowered):
        app._osint_append(out, f"[SECRETS EXPOSURE] → {domains[0]}", "hdr")
        app._osint_run_secret_exposure_audit(domains[0], out)
        dispatched = True

    if domains and re.search(r"\b(synthetic|synth[eé]tique|test identity|identifiant de test|credential control)\b", lowered):
        app._osint_append(out, f"[SYNTHETIC CREDS] → {domains[0]}", "hdr")
        app._osint_run_synthetic_credential_controls(domains[0], out)
        dispatched = True

    for pat in [
        r"(?:username|user|pseudo|nick|compte|profil)[\s:]+([a-zA-Z0-9_\-\.]{3,30})",
        r"(?:user)\s+([a-zA-Z0-9_\-\.]{4,20})\b",
    ]:
        match = re.search(pat, query, re.IGNORECASE)
        if match and not dispatched:
            username = match.group(1).strip()
            app._osint_append(out, f"[USERNAME] → {username}", "hdr")
            app._osint_run_username(username, out)
            dispatched = True
            break

    if not dispatched:
        app._osint_append(out, "Aucune cible détectée automatiquement.", "warn")
        app._osint_append(out, "Entre une IP, domaine, email, hash, MAC ou 'username: <name>'.", "dim")


# Backward-compatible alias kept for external callers.
def open_osint_panel(app: Any) -> None:
    osint_open_panel(app)
