from __future__ import annotations

# UI builders and runners for Cred Research, Port Scan and Dork tabs.

import re
import socket
import threading
import urllib.parse
from typing import Any

import requests
import tkinter as tk


# Credential research tab.
def build_osint_cred_research_tab(app: Any, parent: Any) -> None:
    hdr = tk.Frame(parent, bg="#010810")
    hdr.pack(fill="x", padx=10, pady=(10, 0))
    row1 = tk.Frame(hdr, bg="#010810")
    row1.pack(fill="x", pady=(0, 4))
    tk.Label(row1, text="Username :", bg="#010810", fg="#00d9ff", font=("Consolas", 10, "bold"), width=12, anchor="w").pack(side="left")
    e_user = tk.Entry(row1, bg="#020f1c", fg="#d6f5ff", font=("Consolas", 12), insertbackground="#00e5ff", relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a")
    e_user.pack(side="left", fill="x", expand=True, padx=(6, 8), ipady=6)
    tk.Label(row1, text="@", bg="#010810", fg="#00e5ff", font=("Consolas", 14, "bold")).pack(side="left")
    e_domain = tk.Entry(row1, bg="#020f1c", fg="#d6f5ff", font=("Consolas", 12), insertbackground="#00e5ff", relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a")
    e_domain.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=6)
    row2 = tk.Frame(hdr, bg="#010810")
    row2.pack(fill="x", pady=(0, 6))
    out = tk.Text(parent, bg="#010810", fg="#00ff88", font=("Consolas", 10), relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a", wrap="word", padx=12, pady=10)
    out.pack(fill="both", expand=True, padx=10, pady=(0, 4))
    app._configure_osint_output_widget(out)

    def launch() -> None:
        username = e_user.get().strip()
        domain = e_domain.get().strip().lower().lstrip("@").strip()
        if not username or not domain:
            return
        app._osint_start_output(out, "Cred Research", f"{username}@{domain}", f"◈ CRED RESEARCH → {username} @ {domain}")
        threading.Thread(target=app._osint_run_cred_research, args=(username, domain, out), daemon=True).start()

    tk.Button(row2, text="▶ RECHERCHER", command=launch, bg="#003344", fg="#00e5ff", activebackground="#00b8d9", activeforeground="#010810", font=("Consolas", 10, "bold"), relief="flat", padx=16, pady=4, cursor="hand2").pack(side="left")
    app._add_osint_export_buttons(row2, out)
    e_user.bind("<Return>", lambda _e: launch())
    e_domain.bind("<Return>", lambda _e: launch())


def osint_run_cred_research(app: Any, username: str, domain: str, out: Any) -> None:
    email = f"{username}@{domain}"
    app._osint_section(out, "SCOPE & AUTORISATION")
    if app.pentest_mode_enabled:
        normalized = app._normalize_pentest_target(domain)
        if not normalized or not app._is_target_in_pentest_scope(normalized):
            app._osint_append(out, f"Domaine hors scope autorisé: {domain}", "err")
            return
        app._osint_append(out, f"Scope validé: {domain}", "ok")
    else:
        app._osint_append(out, "Mode passif — active le pentest légal pour un audit borné au scope.", "warn")

    app._osint_section(out, "IDENTIFIANTS GÉNÉRÉS")
    formats: list[str] = [email]
    parts = re.split(r'[._\-]', username.lower())
    if len(parts) >= 2:
        fn, ln = parts[0], parts[-1]
        for fmt in [
            f"{fn}@{domain}", f"{ln}@{domain}", f"{fn}.{ln}@{domain}", f"{ln}.{fn}@{domain}",
            f"{fn[0]}{ln}@{domain}", f"{fn}{ln[0]}@{domain}", f"{fn[0]}.{ln}@{domain}",
        ]:
            if fmt != email and fmt not in formats:
                formats.append(fmt)
    for candidate in formats:
        app._osint_append(out, f"  Candidat: {candidate}", "val")

    app._osint_section(out, "PRÉSENCE USERNAME — PLATEFORMES")
    corporate_platforms = {
        "LinkedIn": f"https://www.linkedin.com/in/{username}",
        "GitHub": f"https://github.com/{username}",
        "GitLab": f"https://gitlab.com/{username}",
        "HackerOne": f"https://hackerone.com/{username}",
        "Bugcrowd": f"https://bugcrowd.com/{username}",
        "Twitter/X": f"https://twitter.com/{username}",
        "Keybase": f"https://keybase.io/{username}",
        "Dev.to": f"https://dev.to/{username}",
        "Medium": f"https://medium.com/@{username}",
        "HackerNews": f"https://news.ycombinator.com/user?id={username}",
    }
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    neg_signals = ["page not found", "user not found", "404", "doesn't exist", "not exist", "nothing here", "account not found"]
    found = 0
    for name, url in corporate_platforms.items():
        try:
            response = requests.get(url, timeout=6, headers=headers, allow_redirects=True)
            if response.status_code == 200:
                if not any(s in response.text.lower()[:2000] for s in neg_signals):
                    app._osint_append(out, f"  [✓] {name:<16} → {url}", "ok")
                    found += 1
                else:
                    app._osint_append(out, f"  [--] {name:<16} → 200 (faux positif)", "dim")
            elif response.status_code == 404:
                app._osint_append(out, f"  [✗] {name:<16} → 404", "dim")
            else:
                app._osint_append(out, f"  [?] {name:<16} → HTTP {response.status_code}", "warn")
        except Exception as exc:
            app._osint_append(out, f"  [E] {name:<16} → {str(exc)[:55]}", "dim")

    app._osint_append(out, f"\n  {found} profil(s) trouvé(s) sur {len(corporate_platforms)} plateformes.", "hdr")
    app._osint_section(out, "DOMAINE CORPORATIF — INFRASTRUCTURE")
    try:
        mx_vals, mx_src = app._osint_dns_lookup_records(domain, "MX", out, label="Cred:MX", limit=6)
        mx = " | ".join(mx_vals)
        if mx:
            app._osint_append(out, f"  MX ({mx_src}): {mx[:160]}", "ok")
            mx_low = mx.lower()
            if "google" in mx_low or "googlemail" in mx_low:
                app._osint_append(out, "  ► Google Workspace détecté — Auth: https://accounts.google.com", "val")
                app._osint_append(out, f"  ► SSO: https://accounts.google.com/o/saml2/idp?idpid={domain}", "link")
            elif "outlook" in mx_low or "microsoft" in mx_low or "protection.outlook" in mx_low:
                app._osint_append(out, "  ► Microsoft 365 / Exchange détecté", "val")
                app._osint_append(out, f"  ► Auth: https://login.microsoftonline.com/{domain}", "link")
                app._osint_append(out, f"  ► OWA: https://outlook.office365.com/owa/{domain}", "link")
            elif "zoho" in mx_low:
                app._osint_append(out, "  ► Zoho Mail — Auth: https://accounts.zoho.com", "val")
            else:
                app._osint_append(out, f"  ► Fournisseur: {mx[:80]}", "dim")
        else:
            app._osint_append(out, "  Aucun enregistrement MX trouvé.", "warn")
    except Exception as exc:
        app._osint_append(out, f"  MX: {exc}", "dim")

    for rtype, qname in [("SPF", domain), ("DMARC", f"_dmarc.{domain}")]:
        values, source = app._osint_dns_lookup_records(qname, "TXT", out, label=f"Cred:{rtype}", limit=6)
        value_text = " | ".join(values)
        app._osint_append(out, f"  {rtype} ({source}): {value_text[:120] if value_text else '(absent)'}", "ok" if value_text else "warn")

    app._osint_section(out, "BREACH EXPOSURE")
    app._osint_append(out, f"  HIBP     : https://haveibeenpwned.com/account/{urllib.parse.quote(email)}", "dim")
    app._osint_append(out, f"  BreachDir: https://breachdirectory.org/?q={urllib.parse.quote(username)}", "dim")
    app._osint_section(out, "RESSOURCES OPEN SOURCE")
    app._osint_append(out, f"  Hunter.io  @{domain}: https://hunter.io/search/{urllib.parse.quote(domain)}", "link")
    app._osint_append(out, f"  Phonebook  : https://phonebook.cz/?q={urllib.parse.quote(domain)}", "link")
    app._osint_append(out, f"  IntelX     : https://intelx.io/?s={urllib.parse.quote(email)}", "link")
    app._osint_append(out, f"  Dehashed   : https://www.dehashed.com/search?query={urllib.parse.quote(email)}", "link")
    app._osint_append(out, f"\n◈ Recherche d'identifiant terminée: {email}", "hdr")


# Port scanner tab.
def build_osint_port_tab(app: Any, parent: Any) -> None:
    top = tk.Frame(parent, bg="#010810")
    top.pack(fill="x", padx=10, pady=10)
    tk.Label(top, text="Hôte / IP:", bg="#010810", fg="#00d9ff", font=("Consolas", 10, "bold"), width=12, anchor="w").pack(side="left")
    e_host = tk.Entry(top, bg="#020f1c", fg="#d6f5ff", font=("Consolas", 12), insertbackground="#00e5ff", relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a")
    e_host.pack(side="left", fill="x", expand=True, padx=(6, 8), ipady=6)
    tk.Label(top, text="Ports:", bg="#010810", fg="#00d9ff", font=("Consolas", 10), anchor="w").pack(side="left")
    e_ports = tk.Entry(top, bg="#020f1c", fg="#d6f5ff", font=("Consolas", 12), insertbackground="#00e5ff", relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a", width=20)
    e_ports.insert(0, "1-1024")
    e_ports.pack(side="left", padx=(6, 8), ipady=6)
    out = tk.Text(parent, bg="#010810", fg="#00ff88", font=("Consolas", 10), relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a", wrap="none", padx=12, pady=10)
    out.pack(fill="both", expand=True, padx=10, pady=(0, 4))
    app._configure_osint_output_widget(out)

    def launch() -> None:
        host = e_host.get().strip()
        ports_raw = e_ports.get().strip()
        if not host:
            return
        app._osint_start_output(out, "Port Scanner", f"{host}:{ports_raw}", f"◈ PORT SCAN → {host}  Ports: {ports_raw}")
        threading.Thread(target=app._osint_run_portscan, args=(host, ports_raw, out), daemon=True).start()

    tk.Button(top, text="▶ SCAN", command=launch, bg="#003344", fg="#00e5ff", activebackground="#00b8d9", font=("Consolas", 10, "bold"), relief="flat", padx=14, pady=4, cursor="hand2").pack(side="left")
    app._add_osint_export_buttons(top, out)


def osint_run_portscan(app: Any, host: str, ports_raw: str, out: Any) -> None:
    try:
        ip = socket.gethostbyname(host)
    except Exception as exc:
        app._osint_append(out, f"Résolution DNS impossible: {exc}", "err")
        return

    if ip != host:
        app._osint_append(out, f"Résolu: {host} → {ip}", "ok")

    ports: list[int] = []
    try:
        for part in ports_raw.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                ports.extend(range(int(a), min(int(b) + 1, 65536)))
            else:
                ports.append(int(part))
    except Exception as exc:
        app._osint_append(out, f"Format ports invalide: {exc}", "err")
        return

    app._osint_append(out, f"Scan de {len(ports)} port(s) sur {ip}...", "warn")
    open_ports: list[tuple[Any, Any, Any]] = []
    lock = threading.Lock()
    svc_map = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
        443: "HTTPS", 445: "SMB", 587: "SMTPTLS", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
        3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-alt",
        8443: "HTTPS-alt", 27017: "MongoDB",
    }

    def check_port(port: int) -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.6)
            if sock.connect_ex((ip, port)) == 0:
                banner = ""
                try:
                    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock2.settimeout(1)
                    sock2.connect((ip, port))
                    if port in (80, 8080):
                        sock2.send(b"HEAD / HTTP/1.0\\r\\nHost: " + ip.encode() + b"\\r\\n\\r\\n")
                    else:
                        sock2.send(b"\\r\\n")
                    banner = sock2.recv(128).decode("utf-8", errors="ignore").strip().split("\n")[0][:55]
                    sock2.close()
                except Exception:
                    pass
                with lock:
                    open_ports.append((port, svc_map.get(port, "?"), banner))
            sock.close()
        except Exception:
            pass

    threads = [threading.Thread(target=check_port, args=(p,), daemon=True) for p in ports]
    max_threads = 200
    for i in range(0, len(threads), max_threads):
        batch = threads[i:i + max_threads]
        for thread in batch:
            thread.start()
        for thread in batch:
            thread.join(timeout=3)

    open_ports.sort(key=lambda x: x[0])
    if open_ports:
        app._osint_append(out, f"\n{len(open_ports)} port(s) OUVERT(s):", "hdr")
        for port, svc, banner in open_ports:
            app._osint_append(out, f"  {port:<7} {svc:<14} {banner}", "ok")
    else:
        app._osint_append(out, "Aucun port ouvert détecté.", "warn")
    app._osint_append(out, f"\n◈ Scan terminé. {len(open_ports)}/{len(ports)} ports ouverts.", "hdr")


# Dork generator tab.
def build_osint_dork_tab(app: Any, parent: Any) -> None:
    top = tk.Frame(parent, bg="#010810")
    top.pack(fill="x", padx=10, pady=10)
    tk.Label(top, text="Cible / Domaine:", bg="#010810", fg="#00d9ff", font=("Consolas", 10, "bold"), width=18, anchor="w").pack(side="left")
    e_target = tk.Entry(top, bg="#020f1c", fg="#d6f5ff", font=("Consolas", 12), insertbackground="#00e5ff", relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a")
    e_target.pack(side="left", fill="x", expand=True, padx=(6, 8), ipady=6)
    out = tk.Text(parent, bg="#010810", fg="#00ff88", font=("Consolas", 10), relief="flat", bd=0, highlightthickness=1, highlightbackground="#005f7a", wrap="word", padx=12, pady=10)
    out.pack(fill="both", expand=True, padx=10, pady=(0, 4))
    app._configure_osint_output_widget(out)

    def launch() -> None:
        target = e_target.get().strip()
        app._osint_start_output(out, "Dork Builder", target or "generic", f"◈ DORK BUILDER — cible: {target or '(générique)'}")
        threading.Thread(target=app._osint_run_dork, args=(target, out), daemon=True).start()

    tk.Button(top, text="▶ GÉNÉRER", command=launch, bg="#003344", fg="#00e5ff", activebackground="#00b8d9", font=("Consolas", 10, "bold"), relief="flat", padx=14, pady=4, cursor="hand2").pack(side="left")
    app._add_osint_export_buttons(top, out)


def osint_run_dork(app: Any, target: str, out: Any) -> None:
    site = f"site:{target}" if target else ""
    dorks = {
        "Fichiers sensibles": [
            f'{site} ext:pdf "confidentiel" OR "password" OR "secret"',
            f"{site} ext:sql OR ext:db OR ext:mdb",
            f"{site} ext:env OR ext:cfg OR ext:conf OR ext:config",
            f"{site} ext:bak OR ext:backup OR ext:old",
            f'{site} ext:log "error" OR "exception" OR "password"',
            f'{site} filetype:xls OR filetype:xlsx "password" OR "login"',
        ],
        "Panneaux admin": [
            f"{site} inurl:admin OR inurl:administrator OR inurl:wp-admin",
            f"{site} inurl:login OR inurl:signin OR inurl:auth",
            f"{site} inurl:dashboard OR inurl:panel OR inurl:cpanel",
            f"{site} inurl:phpmyadmin OR inurl:adminer",
            f'{site} intitle:"admin panel" OR intitle:"control panel"',
            f"{site} inurl:webmail OR inurl:roundcube",
        ],
        "Caméras & IoT": [
            'inurl:"/view/index.shtml" intitle:"Live View"',
            'intitle:"Axis 2.x" OR intitle:"Network Camera"',
            'inurl:"/mjpg/video.mjpg"',
            'intitle:"D-Link" "Live Video"',
            'intitle:"webcamXP" inurl:",8080"',
            "inurl:top.htm inurl:currenttime",
        ],
        "Credentials & Leaks": [
            f'{site} intext:"password" filetype:txt OR filetype:log',
            f'{site} intext:"api_key" OR intext:"api_secret" ext:json OR ext:env',
            f'{site} intext:"BEGIN PRIVATE KEY" OR intext:"BEGIN RSA PRIVATE KEY"',
            f'{site} intext:"DB_PASSWORD" OR intext:"DB_PASS"',
            f'site:pastebin.com "{target}"' if target else 'site:pastebin.com "password"',
            f'site:github.com "password" OR "secret" "{target}"' if target else "",
        ],
        "Configuration exposée": [
            f'{site} intitle:"index of" ".htpasswd" OR ".htaccess"',
            f'{site} intitle:"index of" "config"',
            f'{site} inurl:".git" intitle:"index of"',
            f'{site} inurl:"wp-config.php" filetype:txt',
            f'{site} inurl:"docker-compose.yml"',
            f'{site} inurl:".env" "DB_PASSWORD"',
        ],
        "Injection SQLi/LFI": [
            f'{site} inurl:"?id=" OR inurl:"?cat=" OR inurl:"?page="',
            f'{site} inurl:"?file=" OR inurl:"?path=" OR inurl:"?include="',
            f'{site} inurl:".php?id=" "error" OR "warning"',
        ],
        "Email & Social": [
            f'site:linkedin.com "{target}" employee' if target else "",
            f'site:github.com "{target}"' if target else "",
            f'{site} intext:"@" ext:txt OR ext:csv',
        ],
    }
    google = "https://www.google.com/search?q="
    for category, dork_list in dorks.items():
        app._osint_append(out, f"\n▶ {category}", "hdr")
        app._osint_append(out, "─" * 60, "sep")
        for dork in dork_list:
            if not dork:
                continue
            app._osint_append(out, f"  {dork}", "ok")
            app._osint_append(out, f"    ↳ {google}{urllib.parse.quote(dork)}", "link")
    app._osint_append(out, "\n◈ Dork generation terminée. Usage sur cibles autorisées uniquement.", "warn")
