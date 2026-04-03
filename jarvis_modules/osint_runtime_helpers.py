from __future__ import annotations

# Runtime helpers for OSINT console output, tagging and target validation.

import re
import threading
import urllib.parse
from datetime import datetime
from typing import Any


# Report lifecycle helpers.
def osint_start_output(app: Any, out: Any, module_name: str, target: str, heading: str) -> None:
    out._osint_report = {
        "module": module_name,
        "target": target,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "findings": [],
        "lines": [],
        "evidence": {"http_requests": [], "dns_queries": []},
        "dns_live_mode": app.osint_dns_live_mode,
        "_dns_live_header_printed": False,
    }
    out.configure(state="normal")
    out.delete("1.0", "end")
    out.insert("end", heading + "\n", "hdr")
    out.insert("end", "─" * 70 + "\n", "sep")
    out.configure(state="disabled")


def osint_update_report_context(app: Any, out: Any, module_name: str, target: str | None = None) -> None:
    report = getattr(out, "_osint_report", None)
    if not isinstance(report, dict):
        out._osint_report = {
            "module": module_name,
            "target": target or "",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "findings": [],
            "lines": [],
            "evidence": {"http_requests": [], "dns_queries": []},
        }
        return
    if report.get("module") == "Generic OSINT":
        report["module"] = module_name
    if target is not None and not report.get("target"):
        report["target"] = target
    if not isinstance(report.get("evidence"), dict):
        report["evidence"] = {"http_requests": [], "dns_queries": []}
    elif not isinstance(report["evidence"].get("http_requests"), list):
        report["evidence"]["http_requests"] = []
    if not isinstance(report["evidence"].get("dns_queries"), list):
        report["evidence"]["dns_queries"] = []
    if report.get("dns_live_mode") not in {"off", "compact", "verbose"}:
        report["dns_live_mode"] = app.osint_dns_live_mode
    if "_dns_live_header_printed" not in report:
        report["_dns_live_header_printed"] = False


# Display tagging and buffered output helpers.
def osint_classify_display_tag(app: Any, text: str, tag: str) -> tuple[str, str | None]:
    raw = (text or "").strip().lower()
    neutral_markers = (
        "aucun vrai mot de passe utilisé",
        "pack identifiants synthétiques prêt",
        "scope validé",
        "mode passif uniquement",
    )
    operational_markers = (
        "impossible de joindre",
        "timeout",
        "dns impossible",
        "indisponible",
        "aucun rapport disponible",
        "erreur export",
    )
    critical_markers = (
        "private key",
        "hors scope autorisé",
        "scope pentest requis",
        "cible invalide",
        "anti-bruteforce visible passivement",
        "credential uri",
    )
    high_markers = (
        "aucun indice mfa", "politique mot de passe non visible", "rate-limit headers: aucun",
        "lockout: aucun", "captcha: aucun", "hibp v3 requiert",
    )
    if any(marker in raw for marker in neutral_markers):
        return tag, None
    if any(marker in raw for marker in operational_markers):
        return tag, None
    if any(marker in raw for marker in critical_markers):
        return "crit", "critical"
    if tag == "err":
        return "high", "high"
    if any(marker in raw for marker in high_markers):
        return "high", "high"
    return tag, None


def osint_append(app: Any, out: Any, text: str, tag: str = "") -> None:
    snapshot = getattr(out, "_osint_report", None)
    snap_target = snapshot.get("current_target") or snapshot.get("target", "") if isinstance(snapshot, dict) else ""
    snap_module = snapshot.get("current_module") or snapshot.get("module", "") if isinstance(snapshot, dict) else ""

    def do_append() -> None:
        display_tag, severity = osint_classify_display_tag(app, text, tag)
        out.configure(state="normal")
        out.insert("end", text + "\n", display_tag if display_tag else ())
        out.configure(state="disabled")
        out.see("end")
        report = getattr(out, "_osint_report", None)
        if isinstance(report, dict):
            report.setdefault("lines", []).append({"text": text, "tag": display_tag or tag or ""})
            if severity:
                finding = {
                    "severity": severity,
                    "text": text,
                    "recorded_at": datetime.now().isoformat(timespec="seconds"),
                    "target": snap_target,
                    "module": snap_module,
                }
                findings = report.setdefault("findings", [])
                if not any(
                    f.get("text") == text and f.get("target") == snap_target and f.get("severity") == severity
                    for f in findings
                ):
                    findings.append(finding)

    if threading.current_thread() is threading.main_thread():
        do_append()
    else:
        out.after(0, do_append)


def osint_section(app: Any, out: Any, title: str) -> None:
    osint_append(app, out, f"\n▶ {title}", "hdr")
    osint_append(app, out, "─" * 60, "sep")


# Target normalization and authorization checks.
def osint_validate_authorized_target(app: Any, target: str, out: Any, module_name: str) -> str | None:
    raw = (target or "").strip()
    if not raw:
        osint_append(app, out, f"[{module_name}] Cible vide.", "err")
        return None
    candidate = raw
    if "@" in raw and "://" not in raw:
        candidate = raw.split("@", 1)[1]
    normalized = app._normalize_pentest_target(candidate)
    if not normalized:
        osint_append(app, out, f"[{module_name}] Cible invalide: {raw}", "err")
        return None
    if app.pentest_mode_enabled:
        if not app.pentest_scope_targets:
            osint_append(app, out, f"[{module_name}] Scope pentest requis mais non configuré.", "err")
            return None
        if not app._is_target_in_pentest_scope(normalized):
            osint_append(app, out, f"[{module_name}] Hors scope autorisé: {normalized}", "err")
            return None
        osint_append(app, out, f"[{module_name}] Scope validé: {normalized}", "ok")
    else:
        osint_append(app, out, f"[{module_name}] Mode passif uniquement. Active le pentest légal pour un audit borné au scope.", "warn")
    return normalized


def osint_prepare_http_target(app: Any, target: str) -> tuple[str, str]:
    raw = (target or "").strip()
    if "@" in raw and "://" not in raw:
        raw = raw.split("@", 1)[1]
    if not re.match(r"^[a-z]+://", raw, flags=re.IGNORECASE):
        raw = f"https://{raw}"
    parsed = urllib.parse.urlparse(raw)
    scheme = parsed.scheme if parsed.scheme in ("http", "https") else "https"
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    base_url = f"{scheme}://{netloc}" if netloc else raw
    return base_url, host
