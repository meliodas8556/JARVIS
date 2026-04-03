from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from tkinter import filedialog


def osint_build_report_payload(app: Any, out: Any) -> dict[str, Any] | None:
    report = getattr(out, "_osint_report", None)
    text_content = out.get("1.0", "end-1c").strip() if out else ""
    if not report or not text_content:
        return None
    findings = report.get("findings", []) if isinstance(report.get("findings"), list) else []
    evidence = report.get("evidence", {}) if isinstance(report.get("evidence"), dict) else {}
    http_evidence = evidence.get("http_requests", []) if isinstance(evidence.get("http_requests"), list) else []
    dns_evidence = evidence.get("dns_queries", []) if isinstance(evidence.get("dns_queries"), list) else []
    critical_count = sum(1 for item in findings if item.get("severity") == "critical")
    high_count = sum(1 for item in findings if item.get("severity") == "high")
    per_target_scores: dict[str, Any] = {}
    per_target: dict[str, list] = {}
    http_per_target: dict[str, list] = {}
    dns_per_target: dict[str, list] = {}
    target_candidates: list[str] = []

    for item in http_evidence:
        tgt = str(item.get("target") or report.get("target") or "N/A").strip() or "N/A"
        http_per_target.setdefault(tgt, []).append(item)
        if tgt not in target_candidates:
            target_candidates.append(tgt)
    for item in dns_evidence:
        tgt = str(item.get("target") or report.get("target") or "N/A").strip() or "N/A"
        dns_per_target.setdefault(tgt, []).append(item)
        if tgt not in target_candidates:
            target_candidates.append(tgt)
    for finding in findings:
        tgt = str(finding.get("target") or report.get("target") or "N/A").strip() or "N/A"
        per_target.setdefault(tgt, []).append(finding)
        if tgt not in target_candidates:
            target_candidates.append(tgt)

    if not target_candidates and report.get("target"):
        raw_targets = [x.strip() for x in str(report.get("target", "")).split(",") if x.strip()]
        target_candidates.extend(raw_targets or [str(report.get("target") or "N/A")])

    for tgt in target_candidates:
        flist = per_target.get(tgt, [])
        hlist = http_per_target.get(tgt, [])
        dlist = dns_per_target.get(tgt, [])
        score_info = osint_compute_target_score(app, flist, hlist, dlist)
        per_target_scores[tgt] = score_info

    if per_target_scores:
        score = max(int(info.get("score", 0)) for info in per_target_scores.values())
        score_label = next(
            (info.get("label", "SAFE") for info in per_target_scores.values() if int(info.get("score", 0)) == score),
            "SAFE",
        )
    else:
        empty = osint_compute_target_score(app, findings, http_evidence, dns_evidence)
        score, score_label = int(empty.get("score", 0)), str(empty.get("label", "SAFE"))

    summary = {
        "critical": critical_count,
        "high": high_count,
        "total_findings": len(findings),
        "line_count": len(report.get("lines", [])),
        "http_requests": len(http_evidence),
        "http_errors": sum(1 for item in http_evidence if item.get("error")),
        "dns_queries": len(dns_evidence),
        "dns_errors": sum(1 for item in dns_evidence if item.get("error")),
        "severity_score": score,
        "severity_label": score_label,
    }

    return {
        "module": report.get("module", "OSINT"),
        "target": report.get("target", ""),
        "started_at": report.get("started_at"),
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "pentest_mode_enabled": app.pentest_mode_enabled,
        "pentest_scope_targets": list(app.pentest_scope_targets),
        "summary": summary,
        "per_target_scores": per_target_scores,
        "evidence": evidence,
        "findings": findings,
        "lines": report.get("lines", []),
        "content": text_content,
    }


def osint_compute_severity_score(app: Any, findings: list) -> tuple[int, str]:
    info = osint_compute_target_score(app, findings, [], [])
    score = int(info.get("score", 0))
    if score == 0:
        label = "SAFE"
    elif score <= 2:
        label = "FAIBLE"
    elif score <= 4:
        label = "MODÉRÉ"
    elif score <= 7:
        label = "ÉLEVÉ"
    else:
        label = "CRITIQUE"
    return score, label


def osint_compute_target_score(app: Any, findings: list, http_items: list, dns_items: list) -> dict[str, Any]:
    uniq: set[tuple[str, str]] = set()
    for finding in findings:
        sev = str(finding.get("severity", "")).strip().lower()
        txt = str(finding.get("text", "")).strip().lower()
        if sev and txt:
            uniq.add((sev, txt))
    critical = sum(1 for sev, _ in uniq if sev == "critical")
    high = sum(1 for sev, _ in uniq if sev == "high")

    http_checks = len(http_items)
    http_4xx = sum(1 for h in http_items if str(h.get("status", "")).startswith("4"))
    http_5xx = sum(1 for h in http_items if str(h.get("status", "")).startswith("5"))
    http_errors = sum(1 for h in http_items if h.get("error"))

    dns_checks = len(dns_items)
    dns_errors = sum(1 for d in dns_items if str(d.get("status", "")).startswith("error") or d.get("error"))
    dns_empty = sum(1 for d in dns_items if str(d.get("status", "")).startswith("empty"))

    protective_hits = 0
    for _, txt in uniq:
        if "protégé" in txt or "scope validé" in txt:
            protective_hits += 1
        if "mfa: indice" in txt or "captcha: indice" in txt or "lockout: indice" in txt:
            protective_hits += 1
        if "spf/txt : présent" in txt or "dmarc   : présent" in txt:
            protective_hits += 1
    protective_hits = min(protective_hits, 3)

    raw_risk = (
        critical * 3.0
        + min(high, 4) * 1.0
        + min(http_5xx, 2) * 0.7
        + min(http_errors, 3) * 0.3
        + min(dns_errors, 3) * 0.25
        + min(dns_empty, 3) * 0.2
        - protective_hits * 0.6
    )
    raw_risk = max(0.0, raw_risk)

    coverage = min(1.0, (http_checks + dns_checks) / 18.0)
    confidence_factor = 0.65 + 0.35 * coverage
    score = int(round(min(10.0, raw_risk * confidence_factor)))

    if score == 0:
        label = "SAFE"
    elif score <= 2:
        label = "FAIBLE"
    elif score <= 4:
        label = "MODÉRÉ"
    elif score <= 7:
        label = "ÉLEVÉ"
    else:
        label = "CRITIQUE"

    confidence_label = "FAIBLE" if coverage < 0.35 else ("MOYENNE" if coverage < 0.7 else "HAUTE")
    method = (
        "risk=(3*C + H + 0.7*5xx + 0.3*http_err + 0.25*dns_err + 0.2*dns_empty - 0.6*controls)"
        f"; conf={confidence_factor:.2f}"
    )
    return {
        "score": score,
        "label": label,
        "critical": critical,
        "high": high,
        "total": len(uniq),
        "http_checks": http_checks,
        "http_4xx": http_4xx,
        "http_5xx": http_5xx,
        "http_errors": http_errors,
        "dns_checks": dns_checks,
        "dns_errors": dns_errors,
        "dns_empty": dns_empty,
        "controls": protective_hits,
        "coverage": round(coverage, 2),
        "confidence": confidence_label,
        "method": method,
    }


def osint_export_report(app: Any, out: Any, export_format: str) -> None:
    payload = osint_build_report_payload(app, out)
    if not payload:
        app._append_terminal_output("[OSINT] Aucun rapport disponible à exporter.", "term_error")
        return

    base_dir = os.path.join(app._get_user_documents_dir(), "jarvis_osint_reports")
    os.makedirs(base_dir, exist_ok=True)
    slug_module = app._sanitize_slug(str(payload.get("module", "osint")) or "osint")
    slug_target = app._sanitize_slug(str(payload.get("target", "scope")) or "scope")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    ext = ".txt"
    if export_format == "json":
        ext = ".json"
    elif export_format == "html":
        ext = ".html"

    path = filedialog.asksaveasfilename(
        title=f"Exporter rapport OSINT ({export_format.upper()})",
        initialdir=base_dir,
        initialfile=f"osint_{slug_module}_{slug_target}_{timestamp}{ext}",
        defaultextension=ext,
        filetypes=[(f"Rapport {export_format.upper()}", f"*{ext}"), ("Tous les fichiers", "*.*")],
    )
    if not path:
        return

    try:
        if export_format == "json":
            app._write_json_payload(path, payload)
        elif export_format == "html":
            try:
                html_content = osint_build_html_report(app, payload)
            except Exception as html_exc:
                html_content = osint_build_html_error_report(app, payload, html_exc)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(html_content)
        else:
            score = payload.get("summary", {}).get("severity_score", 0)
            score_label = payload.get("summary", {}).get("severity_label", "N/A")
            txt_lines = [
                "=" * 72,
                f"RAPPORT OSINT — {payload['module']}",
                f"Cible       : {payload['target'] or 'N/A'}",
                f"Démarré     : {payload.get('started_at', 'N/A')}",
                f"Exporté     : {payload.get('exported_at', 'N/A')}",
                f"Mode pentest: {'ON' if payload.get('pentest_mode_enabled') else 'OFF'}",
                f"Scope       : {', '.join(payload.get('pentest_scope_targets', [])) or 'non défini'}",
                "=" * 72,
                "",
                "── SYNTHÈSE ──",
                f"Score sévérité : {score}/10 — {score_label}",
                f"Critical: {payload['summary']['critical']}",
                f"High    : {payload['summary']['high']}",
                f"Findings: {payload['summary']['total_findings']}",
                f"HTTP req: {payload['summary'].get('http_requests', 0)}  |  HTTP errors: {payload['summary'].get('http_errors', 0)}",
                f"DNS req : {payload['summary'].get('dns_queries', 0)}  |  DNS errors : {payload['summary'].get('dns_errors', 0)}",
                "",
            ]
            if payload.get("per_target_scores") and len(payload["per_target_scores"]) > 1:
                txt_lines += ["── SCORES PAR CIBLE ──"]
                for tgt, info in payload["per_target_scores"].items():
                    txt_lines.append(
                        f"  {tgt:<32} {info['label']} ({info['score']}/10)"
                        f"  C:{info['critical']} H:{info['high']}"
                        f"  HTTP:{info.get('http_checks',0)} DNS:{info.get('dns_checks',0)}"
                        f"  CONF:{info.get('confidence','N/A')}"
                    )
                txt_lines.append("")

            if payload["findings"]:
                txt_lines += ["── FINDINGS ──"]
                for idx, finding in enumerate(payload["findings"], start=1):
                    tgt_col = f" [{finding.get('target', '')}]" if finding.get("target") else ""
                    txt_lines.append(f"{idx}. [{finding.get('severity', 'info').upper()}]{tgt_col} {finding.get('text', '')}")

            http_items = payload.get("evidence", {}).get("http_requests", [])
            if http_items:
                txt_lines += ["", "── PREUVES COLLECTÉES (HTTP) ──"]
                for idx, item in enumerate(http_items[:60], start=1):
                    status_txt = item.get("status", "ERR")
                    err_txt = f"  error={item.get('error')}" if item.get("error") else ""
                    tgt = item.get("target", "")
                    lbl = item.get("label", "")
                    txt_lines.append(
                        f"{idx:02d}. [{status_txt}] {item.get('method','GET')} {item.get('url','')}  target={tgt}  label={lbl}{err_txt}"
                    )
                if len(http_items) > 60:
                    txt_lines.append(f"... {len(http_items) - 60} preuve(s) supplémentaires dans le JSON")

            dns_items = payload.get("evidence", {}).get("dns_queries", [])
            if dns_items:
                txt_lines += ["", "── PREUVES COLLECTÉES (DNS) ──"]
                for idx, item in enumerate(dns_items[:80], start=1):
                    err_txt = f" error={item.get('error')}" if item.get("error") else ""
                    records = item.get("records", [])
                    rec_txt = " | ".join(records[:3]) if records else "(aucun)"
                    txt_lines.append(
                        f"{idx:02d}. [{item.get('resolver','?')}] {item.get('query_type','?')} {item.get('query_name','')}"
                        f"  status={item.get('status','')}  records={rec_txt}{err_txt}"
                    )
                if len(dns_items) > 80:
                    txt_lines.append(f"... {len(dns_items) - 80} preuve(s) DNS supplémentaires dans le JSON")

            txt_lines += ["", "── CONSOLE ──", payload["content"], "", "Fin du rapport."]
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(txt_lines))

        app._append_terminal_output(f"[OSINT] Rapport exporté: {path}", "term_header")
    except Exception as exc:
        app._append_terminal_output(f"[OSINT] Erreur export rapport: {exc}", "term_error")


def osint_build_html_report(app: Any, payload: dict[str, Any]) -> str:
    import html as html_lib

    def esc(value: str) -> str:
        return html_lib.escape(str(value or ""))

    score = payload.get("summary", {}).get("severity_score", 0)
    score_label = payload.get("summary", {}).get("severity_label", "N/A")
    colors = {"SAFE": "#00ff88", "FAIBLE": "#66ffaa", "MODÉRÉ": "#ffcc00", "ÉLEVÉ": "#ffb347", "CRITIQUE": "#ff778f"}
    score_color = colors.get(score_label, "#ffffff")
    pentest_color = "#ff8844" if payload.get("pentest_mode_enabled") else "#556677"
    pentest_txt = "ON" if payload.get("pentest_mode_enabled") else "OFF"
    scope_txt = esc(", ".join(payload.get("pentest_scope_targets", [])) or "non défini")

    findings_rows = ""
    for finding in payload.get("findings", []):
        sev = finding.get("severity", "info").upper()
        sev_class = "crit" if sev == "CRITICAL" else ("high" if sev == "HIGH" else "info")
        findings_rows += (
            f'<tr class="{sev_class}">'
            f'<td>{esc(sev)}</td>'
            f'<td>{esc(finding.get("target", ""))}</td>'
            f'<td>{esc(finding.get("module", ""))}</td>'
            f'<td>{esc(finding.get("text", ""))}</td>'
            "</tr>\n"
        )

    pts_rows = ""
    for tgt, info in payload.get("per_target_scores", {}).items():
        lb = info.get("label", "")
        lc = colors.get(lb, "#ffffff")
        pts_rows += (
            f"<tr><td>{esc(tgt)}</td>"
            f'<td style="color:{lc};font-weight:bold">{esc(lb)} ({info.get("score",0)}/10)</td>'
            f'<td>{info.get("critical",0)}</td>'
            f'<td>{info.get("high",0)}</td>'
            f'<td>{info.get("total",0)}</td>'
            f'<td>{info.get("http_checks",0)}</td>'
            f'<td>{info.get("dns_checks",0)}</td>'
            f'<td>{esc(info.get("confidence","N/A"))}</td></tr>\n'
        )

    console_html = ""
    for line in payload.get("lines", []):
        tag = line.get("tag", "")
        console_html += f'<span class="l-{esc(tag)}">{esc(line.get("text", ""))}</span>\n'

    per_target_section = ""
    if payload.get("per_target_scores") and len(payload["per_target_scores"]) > 1:
        per_target_section = (
            "<h2>Scores par cible</h2>"
            "<table><tr><th>Cible</th><th>Score</th><th>Critical</th><th>High</th><th>Total</th><th>HTTP checks</th><th>DNS checks</th><th>Confiance</th></tr>\n"
            + pts_rows
            + "</table>\n"
        )

    findings_section = ""
    if findings_rows:
        findings_section = (
            f"<h2>Findings ({len(payload.get('findings',[]))})</h2>"
            "<table><tr><th>Sévérité</th><th>Cible</th><th>Module</th><th>Détail</th></tr>\n"
            + findings_rows
            + "</table>\n"
        )

    evidence_rows = ""
    for item in payload.get("evidence", {}).get("http_requests", [])[:120]:
        status = item.get("status", "ERR")
        cls = "crit" if str(status).startswith("5") else ("high" if str(status).startswith("4") else "info")
        err_txt = esc(item.get("error", ""))
        headers_txt = esc(", ".join(item.get("security_headers", [])))
        evidence_rows += (
            f'<tr class="{cls}">'
            f'<td>{esc(item.get("recorded_at", ""))}</td>'
            f'<td>{esc(item.get("target", ""))}</td>'
            f'<td>{esc(item.get("label", ""))}</td>'
            f'<td>{esc(item.get("method", "GET"))}</td>'
            f'<td>{esc(str(status))}</td>'
            f'<td>{esc(item.get("url", ""))}</td>'
            f'<td>{headers_txt}</td>'
            f'<td>{err_txt}</td>'
            "</tr>\n"
        )

    evidence_section = ""
    if evidence_rows:
        evidence_section = (
            "<h2>Preuves collectées (HTTP)</h2>"
            "<table><tr><th>Horodatage</th><th>Cible</th><th>Label</th><th>Méthode</th><th>Status</th><th>URL</th><th>Security Headers</th><th>Erreur</th></tr>\n"
            + evidence_rows
            + "</table>\n"
        )

    dns_rows = ""
    for item in payload.get("evidence", {}).get("dns_queries", [])[:160]:
        status = str(item.get("status", ""))
        cls = "high" if status.startswith("error") else "info"
        recs = ", ".join(item.get("records", [])[:3])
        dns_rows += (
            f'<tr class="{cls}">'
            f'<td>{esc(item.get("recorded_at", ""))}</td>'
            f'<td>{esc(item.get("target", ""))}</td>'
            f'<td>{esc(item.get("label", ""))}</td>'
            f'<td>{esc(item.get("resolver", ""))}</td>'
            f'<td>{esc(item.get("query_type", ""))}</td>'
            f'<td>{esc(item.get("query_name", ""))}</td>'
            f'<td>{esc(recs)}</td>'
            f'<td>{esc(item.get("error", ""))}</td>'
            "</tr>\n"
        )

    dns_section = ""
    if dns_rows:
        dns_section = (
            "<h2>Preuves collectées (DNS)</h2>"
            "<table><tr><th>Horodatage</th><th>Cible</th><th>Label</th><th>Resolver</th><th>Type</th><th>Nom</th><th>Records</th><th>Erreur</th></tr>\n"
            + dns_rows
            + "</table>\n"
        )

    return f"""<!DOCTYPE html>
<html lang=\"fr\">
<head><meta charset=\"UTF-8\"><title>JARVIS OSINT — {esc(payload.get('module','OSINT'))} — {esc(payload.get('target',''))}</title><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #010810; color: #00ff88; font-family: Consolas, 'Courier New', monospace; font-size: 13px; padding: 24px; line-height: 1.6; }}
h1 {{ color: #00e5ff; font-size: 20px; margin-bottom: 6px; }}
h2 {{ color: #00e5ff; font-size: 14px; margin: 22px 0 8px; border-bottom: 1px solid #003344; padding-bottom: 4px; }}
.hdr {{ border: 1px solid #00b8d9; padding: 16px 20px; margin-bottom: 20px; background: #000c18; }}
.meta {{ color: #7dc8e0; font-size: 12px; margin: 3px 0; }}
.score-block {{ display: inline-block; padding: 6px 16px; border-radius: 4px; font-size: 18px; font-weight: bold; color: {score_color}; border: 1px solid {score_color}; margin: 12px 0 6px; }}
.counts {{ color: #aaddff; margin-top: 8px; font-size: 12px; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 12px; }}
th {{ color: #00e5ff; background: #000c18; padding: 6px 10px; text-align: left; border-bottom: 1px solid #003344; }}
td {{ padding: 5px 10px; border-bottom: 1px solid #001a26; vertical-align: top; }}
tr.crit td {{ color: #ff778f; background: #290611; }}
tr.high td {{ color: #ffb347; background: #231208; }}
tr.info td {{ color: #8df5ff; }}
tr:hover td {{ filter: brightness(1.3); }}
.console {{ background: #000c18; padding: 14px; white-space: pre-wrap; font-size: 11px; border: 1px solid #002233; max-height: 620px; overflow-y: auto; }}
.l-hdr {{ color: #00e5ff; font-weight: bold; display: block; }}
.l-ok {{ color: #00ff88; display: block; }}
.l-warn {{ color: #ffcc00; display: block; }}
.l-high {{ color: #ffb347; background: #231208; display: block; padding: 1px 2px; }}
.l-crit {{ color: #ff778f; background: #290611; display: block; padding: 1px 2px; }}
.l-err {{ color: #ff4466; display: block; }}
.l-dim {{ color: #336688; display: block; }}
.l-val {{ color: #ffffff; display: block; }}
.l-sep {{ color: #0a3d52; display: block; }}
.l-bold {{ color: #ffffff; font-weight: bold; display: block; }}
.l-link {{ color: #56d4ff; display: block; }}
.l- {{ color: #00ff88; display: block; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-right: 6px; }}
.badge-c {{ background: #290611; color: #ff778f; border: 1px solid #ff778f; }}
.badge-h {{ background: #231208; color: #ffb347; border: 1px solid #ffb347; }}
footer {{ color: #223344; font-size: 11px; margin-top: 24px; border-top: 1px solid #001a26; padding-top: 8px; }}
</style></head>
<body>
<div class=\"hdr\">
  <h1>◈ JARVIS OSINT — {esc(payload.get('module','OSINT'))}</h1>
  <div class=\"meta\">Cible : <strong style=\"color:#fff\">{esc(payload.get('target','N/A'))}</strong></div>
  <div class=\"meta\">Démarré : {esc(str(payload.get('started_at','')))} &nbsp;|&nbsp; Exporté : {esc(str(payload.get('exported_at','')))}</div>
  <div class=\"meta\">Mode pentest : <strong style=\"color:{pentest_color}\">{pentest_txt}</strong> &nbsp;|&nbsp; Scope : {scope_txt}</div>
</div>
<h2>Synthèse</h2>
<div class=\"score-block\">Score : {score}/10 — {esc(score_label)}</div>
<div class=\"counts\">
    <span class=\"badge badge-c\">CRITICAL : {payload.get('summary', {}).get('critical',0)}</span>
    <span class=\"badge badge-h\">HIGH : {payload.get('summary', {}).get('high',0)}</span>
    Findings : {payload.get('summary', {}).get('total_findings',0)} &nbsp;|&nbsp; Lignes : {payload.get('summary', {}).get('line_count',0)}
</div>
{per_target_section}
{findings_section}
{evidence_section}
{dns_section}
<h2>Console</h2>
<div class=\"console\">{console_html}</div>
<footer>JARVIS OSINT &nbsp;|&nbsp; {esc(str(payload.get('exported_at','')))} &nbsp;|&nbsp; LEGAL USE ONLY — AUTHORIZED TARGETS ONLY</footer>
</body></html>"""


def osint_build_html_error_report(app: Any, payload: dict[str, Any], exc: Exception) -> str:
    import html as html_lib

    def esc(value: str) -> str:
        return html_lib.escape(str(value or ""))

    module = esc(payload.get("module", "OSINT"))
    target = esc(payload.get("target", "N/A"))
    exported = esc(payload.get("exported_at", datetime.now().isoformat(timespec="seconds")))
    reason = esc(exc)
    console = esc(payload.get("content", ""))
    return f"""<!DOCTYPE html>
<html lang=\"fr\"><head><meta charset=\"UTF-8\"><title>JARVIS OSINT — Export Error</title><style>
body {{ background:#010810; color:#8df5ff; font-family:Consolas, monospace; padding:24px; }}
h1 {{ color:#ff778f; margin-bottom:12px; }}
.meta {{ color:#7dc8e0; font-size:12px; margin:2px 0; }}
.err {{ color:#ff4466; background:#290611; border:1px solid #ff4466; padding:10px; margin:14px 0; white-space:pre-wrap; }}
pre {{ background:#000c18; border:1px solid #002233; padding:10px; color:#00ff88; white-space:pre-wrap; }}
</style></head><body>
<h1>Rapport HTML incomplet (fallback)</h1>
<div class=\"meta\">Module: {module}</div>
<div class=\"meta\">Cible: {target}</div>
<div class=\"meta\">Exporté: {exported}</div>
<div class=\"err\">Erreur de rendu HTML: {reason}</div>
<h2 style=\"color:#00e5ff\">Console brute</h2>
<pre>{console}</pre>
</body></html>"""


def osint_export_scope_batch(app: Any, out: Any) -> None:
    payload = osint_build_report_payload(app, out)
    if not payload or (not payload.get("findings") and not payload.get("lines")):
        app._append_terminal_output(
            "[OSINT] Aucun rapport scope disponible. Lance d'abord l'audit complet du scope.",
            "term_error",
        )
        return

    base_dir = os.path.join(app._get_user_documents_dir(), "jarvis_osint_reports")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    campaign_dir = os.path.join(base_dir, f"{timestamp}_scope_campaign")

    try:
        os.makedirs(campaign_dir, exist_ok=True)
        app._write_json_payload(os.path.join(campaign_dir, "scope_full_report.json"), payload)
        try:
            full_html = osint_build_html_report(app, payload)
        except Exception as html_exc:
            full_html = osint_build_html_error_report(app, payload, html_exc)
        with open(os.path.join(campaign_dir, "scope_full_report.html"), "w", encoding="utf-8") as handle:
            handle.write(full_html)

        per_target: dict[str, list] = {}
        for finding in payload.get("findings", []):
            tgt = finding.get("target") or payload.get("target") or "unknown"
            per_target.setdefault(tgt, []).append(finding)

        for tgt, tgt_findings in per_target.items():
            slug = app._sanitize_slug(tgt) or "scope"
            tgt_http = [h for h in payload.get("evidence", {}).get("http_requests", []) if (h.get("target") or "") == tgt]
            tgt_dns = [d for d in payload.get("evidence", {}).get("dns_queries", []) if (d.get("target") or "") == tgt]
            score_info = osint_compute_target_score(app, tgt_findings, tgt_http, tgt_dns)
            score = int(score_info.get("score", 0))
            label = str(score_info.get("label", "SAFE"))
            tgt_payload = dict(payload)
            tgt_payload["target"] = tgt
            tgt_payload["module"] = f"Scope Audit — {tgt}"
            tgt_payload["findings"] = tgt_findings
            tgt_payload["summary"] = {
                "critical": sum(1 for f in tgt_findings if f.get("severity") == "critical"),
                "high": sum(1 for f in tgt_findings if f.get("severity") == "high"),
                "total_findings": len(tgt_findings),
                "line_count": len(payload.get("lines", [])),
                "severity_score": score,
                "severity_label": label,
            }
            tgt_payload["per_target_scores"] = {tgt: score_info}

            try:
                target_html = osint_build_html_report(app, tgt_payload)
            except Exception as html_exc:
                target_html = osint_build_html_error_report(app, tgt_payload, html_exc)

            with open(os.path.join(campaign_dir, f"target_{slug}.html"), "w", encoding="utf-8") as handle:
                handle.write(target_html)
            app._write_json_payload(os.path.join(campaign_dir, f"target_{slug}.json"), tgt_payload)

        osint_write_scope_index_html(app, campaign_dir, payload, per_target)
        count = sum(1 for _ in os.scandir(campaign_dir))
        app._append_terminal_output(
            f"[OSINT] EXPORT SCOPE: {count} fichier(s) généré(s) dans: {campaign_dir}",
            "term_header",
        )
    except Exception as exc:
        app._append_terminal_output(f"[OSINT] Erreur export scope batch: {exc}", "term_error")


def osint_write_scope_index_html(app: Any, campaign_dir: str, payload: dict[str, Any], per_target: dict[str, list]) -> None:
    import html as html_lib

    def esc(value: str) -> str:
        return html_lib.escape(str(value or ""))

    colors = {"SAFE": "#00ff88", "FAIBLE": "#66ffaa", "MODÉRÉ": "#ffcc00", "ÉLEVÉ": "#ffb347", "CRITIQUE": "#ff778f"}
    score = payload.get("summary", {}).get("severity_score", 0)
    score_label = payload.get("summary", {}).get("severity_label", "N/A")
    score_color = colors.get(score_label, "#ffffff")

    rows = ""
    for tgt, flist in per_target.items():
        slug = app._sanitize_slug(tgt) or "scope"
        tgt_http = [h for h in payload.get("evidence", {}).get("http_requests", []) if (h.get("target") or "") == tgt]
        tgt_dns = [d for d in payload.get("evidence", {}).get("dns_queries", []) if (d.get("target") or "") == tgt]
        info = osint_compute_target_score(app, flist, tgt_http, tgt_dns)
        sc = int(info.get("score", 0))
        lb = str(info.get("label", "SAFE"))
        lc = colors.get(lb, "#ffffff")
        critical = sum(1 for f in flist if f.get("severity") == "critical")
        high = sum(1 for f in flist if f.get("severity") == "high")
        rows += (
            f'<tr><td><a href="target_{slug}.html" style="color:#56d4ff">{esc(tgt)}</a></td>'
            f'<td style="color:{lc};font-weight:bold">{esc(lb)} ({sc}/10)</td>'
            f"<td>{critical}</td><td>{high}</td><td>{len(flist)}</td></tr>\n"
        )

    html_index = f"""<!DOCTYPE html>
<html lang=\"fr\"><head><meta charset=\"UTF-8\"><title>JARVIS OSINT — Scope Index</title><style>
body {{ background: #010810; color: #00ff88; font-family: Consolas, monospace; padding: 24px; }}
h1 {{ color: #00e5ff; margin-bottom: 16px; }}
.score {{ font-size: 22px; font-weight: bold; color: {score_color}; margin: 10px 0 20px; }}
table {{ width: 100%; border-collapse: collapse; }} th {{ color: #00e5ff; background: #000c18; padding: 8px 12px; text-align: left; border-bottom: 1px solid #003344; }}
td {{ padding: 6px 12px; border-bottom: 1px solid #001a26; }}
a {{ text-decoration: none; }} a:hover {{ text-decoration: underline; }}
footer {{ color: #223344; font-size: 11px; margin-top: 24px; border-top: 1px solid #001a26; padding-top: 8px; }}
</style></head><body>
<h1>◈ JARVIS OSINT — Scope Campaign</h1>
<div style=\"color:#7dc8e0;font-size:12px\">Exporté : {esc(str(payload.get('exported_at','')))} &nbsp;|&nbsp; Mode pentest : {'ON' if payload.get('pentest_mode_enabled') else 'OFF'}</div>
<div class=\"score\">Score global : {score}/10 — {esc(score_label)}</div>
<table><tr><th>Cible</th><th>Score</th><th>Critical</th><th>High</th><th>Total findings</th></tr>
{rows}</table>
<p style=\"margin-top:16px;color:#7dc8e0\">Rapport complet : <a href=\"scope_full_report.html\" style=\"color:#56d4ff\">scope_full_report.html</a></p>
<footer>JARVIS OSINT &nbsp;|&nbsp; LEGAL USE ONLY</footer>
</body></html>"""

    with open(os.path.join(campaign_dir, "index.html"), "w", encoding="utf-8") as handle:
        handle.write(html_index)


# Backward-compatible aliases kept for external callers.
def export_osint_report(app: Any, out: Any, export_format: str) -> None:
    osint_export_report(app, out, export_format)


def export_osint_scope_batch(app: Any, out: Any) -> None:
    osint_export_scope_batch(app, out)
