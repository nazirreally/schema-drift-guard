"""Self-contained HTML audit output. All external data is escaped."""
from collections import Counter
from html import escape
from pathlib import Path


def render_html(report, baseline, current):
    counts = Counter(item["severity"] for item in report["changes"])
    rows = []
    for item in report["changes"]:
        severity = item["severity"]
        if severity not in ("breaking", "informational"):
            raise ValueError("Invalid report severity")
        rows.append(
            '<tr><td><code>{}</code></td><td>{}</td><td><span class="tag {}">{}</span></td></tr>'.format(
                escape(item["column"], quote=True),
                escape(item["change"], quote=True),
                severity, severity.title()
            )
        )
    if not rows:
        rows.append('<tr><td colspan="3" class="empty">No reportable schema changes.</td></tr>')
    status = "ACTION REQUIRED" if report["breaking"] else "CONTRACT ACCEPTED"
    state = "bad" if report["breaking"] else "good"
    css = """
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#e8f2ff;background:#0a1220}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 80% 0,#18334c,#0a1220 55%);min-height:100vh}
main{max-width:1060px;margin:0 auto;padding:56px 24px 90px}
.eyebrow{letter-spacing:.21em;color:#7ddbd2;font-size:12px;font-weight:800}
h1{font-size:clamp(30px,5vw,56px);letter-spacing:-.055em;margin:12px 0 8px}
p{color:#adc2d5;line-height:1.7}.hero{display:flex;justify-content:space-between;gap:20px;align-items:center;flex-wrap:wrap}
.status{padding:11px 16px;border:1px solid;border-radius:40px;font-weight:800;font-size:12px;letter-spacing:.08em}
.good{color:#75f1c7;border-color:#327d6a;background:#12392f}.bad{color:#ffb9aa;border-color:#92564e;background:#412a2c}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:36px 0}
.card,.panel{background:#101f31;border:1px solid #29425b;border-radius:18px;padding:22px}
.card small{display:block;color:#a9c0d5;font-weight:700;font-size:12px}.card strong{display:block;font-size:30px;margin-top:12px;letter-spacing:-.04em}
.panel{padding:0;overflow:hidden}h2{padding:24px 25px 10px;margin:0;font-size:19px}table{border-collapse:collapse;width:100%}
th,td{padding:15px 25px;border-top:1px solid #2a4055;text-align:left}th{color:#a9c0d5;font-size:12px;text-transform:uppercase;letter-spacing:.1em}
td{overflow-wrap:anywhere}code{color:#9bece1;font-size:13px}.tag{border-radius:8px;padding:5px 9px;font-size:12px;font-weight:700}
.tag.breaking{background:#482f33;color:#ffb9aa}.tag.informational{background:#233f54;color:#b8e4ff}
.empty{text-align:center;color:#adc2d5;padding:42px}.foot{margin-top:24px;font-size:12px}
@media(max-width:700px){.grid{grid-template-columns:repeat(2,1fr)}th,td{padding:13px 10px}main{padding:30px 12px}}
"""
    def card(label, value):
        return '<div class="card"><small>{}</small><strong>{}</strong></div>'.format(label, value)
    cards = ''.join([
        card("BREAKING FINDINGS", counts["breaking"]),
        card("INFORMATIONAL", counts["informational"]),
        card("BASELINE COLUMNS", len(baseline["columns"])),
        card("CURRENT COLUMNS", len(current["columns"])),
    ])
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="dark"><title>Schema Drift Guard | Audit</title>'
        '<style>' + css + '</style></head><body><main>'
        '<div class="eyebrow">SCHEMA DRIFT GUARD / CONTRACT AUDIT</div>'
        '<div class="hero"><div><h1>Schema integrity report</h1>'
        '<p>Offline audit of observed CSV structure against a versioned baseline.</p></div>'
        '<div class="status ' + state + '">' + status + '</div></div>'
        '<section class="grid">' + cards + '</section>'
        '<section class="panel"><h2>Change register</h2><table><thead><tr>'
        '<th>Column</th><th>Observed change</th><th>Severity</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></section>'
        '<p class="foot">Based on {:,} sampled baseline rows and {:,} sampled current rows. '
        'This report embeds no external resources or executable scripts. '
        'Missing observations are never imputed.</p></main></body></html>'.format(
            baseline["rows_sampled"], current["rows_sampled"])
    )


def write_html(path, report, baseline, current):
    """Write portable HTML; propagate filesystem failures to the CLI."""
    Path(path).write_text(render_html(report, baseline, current), encoding="utf-8")
