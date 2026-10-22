"""Turn a Leaver Impact Check result (JSON) into a one-page HTML report for an admin."""
import html

STATE_LABEL = {"Started": "On", "Stopped": "Off", "Suspended": "Suspended"}
CONNECTOR = {"shared_office365": "Office 365 Outlook", "shared_sharepointonline": "SharePoint",
             "shared_excelonlinebusiness": "Excel Online (Business)", "shared_teams": "Microsoft Teams",
             "shared_microsoftforms": "Microsoft Forms", "shared_approvals": "Approvals",
             "shared_sql": "SQL Server", "shared_onedriveforbusiness": "OneDrive for Business",
             "shared_commondataserviceforapps": "Microsoft Dataverse"}


def _conn(c):
    return CONNECTOR.get(c, c)


def _e(x):
    return html.escape(str(x if x is not None else ""))


def _norm(s):
    return (s or "").strip().lower()


def classify(report):
    leaver = _norm(report.get("leaver"))
    will_break, owned_safe = [], []
    for env in report.get("environments", []):
        for f in env.get("flows", []):
            f.setdefault("environment", env.get("environment"))
            on_leaver = [c for c in f.get("connections", []) if _norm(c.get("runs_as")) == leaver]
            if on_leaver:
                will_break.append((f, on_leaver))
            elif _norm(f.get("creator")) == leaver:
                owned_safe.append(f)
    return will_break, owned_safe


def next_owner(f, leaver):
    others = [o["who"] for o in f.get("co_owners", []) if _norm(o.get("who")) != _norm(leaver)]
    if others:
        return others[0], "Already a co-owner. Needs their own connection, not just co-ownership."
    return None, "No co-owner. Pick someone before the last day."


def render_html(report):
    leaver = report.get("leaver", "")
    will_break, owned_safe = classify(report)
    owned_breaking = [f for f, _ in will_break if _norm(f.get("creator")) == _norm(leaver)]
    owner_filter = len(owned_breaking) + len(owned_safe)
    envs = len(report.get("environments", []))
    sample = report.get("sample")

    rows = []
    for f, conns in will_break:
        who, note = next_owner(f, leaver)
        via = "".join(f'<li>{_e(_conn(c["connector"]))}{" (through connection reference " + _e(c["via_reference"]) + ")" if c.get("via_reference") else ""}</li>' for c in conns)
        rows.append(f"""<tr>
<td><b>{_e(f["flow"])}</b><div class="sub">{_e(f["environment"])}</div></td>
<td><ul class="plain">{via}</ul></td>
<td><span class="chip ok">{_e(STATE_LABEL.get(f.get("state"), f.get("state")))}</span><div class="sub">shows as healthy</div></td>
<td>{_e(who) if who else '<span class="chip warn">None</span>'}<div class="sub">{_e(note)}</div></td>
</tr>""")

    safe_rows = "".join(f"""<tr><td><b>{_e(f["flow"])}</b><div class="sub">{_e(f["environment"])}</div></td>
<td>{", ".join(_e(c["runs_as"]) for c in f.get("connections", [])) or "No connections"}</td>
<td>Keeps running after the block. Still needs a new owner on paper.</td></tr>""" for f in owned_safe)

    banner = ('<div class="banner">Sample report. The company, people and flows are made up. '
              'It was produced by the same script that was tested against a real trial tenant.</div>') if sample else ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Leaver Impact Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--bg:#f4f5f2;--surface:#fff;--fg:#1d2320;--muted:#5d6862;--line:#d9ded9;--accent:#2e5c8a;--accent-soft:#e3ecf5;
--bad:#9a3b2f;--bad-soft:#f6e6e3;--ok:#2c6b3f;--ok-soft:#e3f1e6;--warn:#8a5a00;--warn-soft:#fbf0d9;
--display:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;--body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#131614;--surface:#1b201d;--fg:#e5e9e6;--muted:#9ca8a1;--line:#2d3530;--accent:#8db8e3;--accent-soft:#1b2a3a;--bad:#e8988c;--bad-soft:#33201d;--ok:#7fc994;--ok-soft:#18291d;--warn:#e8b65c;--warn-soft:#2e2615;color-scheme:dark}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 var(--body)}}
.wrap{{max-width:980px;margin:0 auto;padding:36px 16px 64px;display:flex;flex-direction:column;gap:28px}}
h1,h2{{font-family:var(--display);margin:0;line-height:1.2;text-wrap:balance}} h1{{font-size:2rem}} h2{{font-size:1.3rem}}
.eyebrow{{font-family:var(--mono);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
.banner{{background:var(--warn-soft);color:var(--warn);border-radius:6px;padding:10px 14px;font-size:.9rem}}
.tiles{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}} @media (max-width:640px){{.tiles{{grid-template-columns:1fr}}}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:14px 16px}}
.tile .n{{font-family:var(--display);font-size:2rem;font-weight:600;font-variant-numeric:tabular-nums}}
.tile.bad{{border-color:var(--bad)}} .tile.bad .n{{color:var(--bad)}}
.tablewrap{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:6px}}
table{{border-collapse:collapse;width:100%;min-width:680px;font-size:.92rem}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}} tr:last-child td{{border-bottom:none}}
th{{font-family:var(--mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:500}}
.sub{{font-size:.8rem;color:var(--muted)}} ul.plain{{margin:0;padding-left:16px}}
.chip{{font-family:var(--mono);font-size:.72rem;padding:2px 8px;border-radius:99px}} .chip.ok{{background:var(--ok-soft);color:var(--ok)}} .chip.warn{{background:var(--warn-soft);color:var(--warn)}}
.note{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:4px;padding:12px 16px;font-size:.92rem}}
ol{{margin:0;padding-left:20px}} p{{margin:0;max-width:72ch}}
footer{{font-size:.78rem;color:var(--muted)}}
</style></head><body><div class="wrap">
{banner}
<header style="display:flex;flex-direction:column;gap:6px">
<div class="eyebrow">Leaver Impact Check · generated {_e(str(report.get("generated", "")).replace("T", " "))}</div>
<h1>Before {_e(leaver)} leaves</h1>
<p>Flows that run on this person's login stop working when their account is blocked. Co-owners don't change that. This report lists them so they can be handed over before the last day.</p>
</header>

<div class="tiles">
<div class="tile bad"><div class="n">{len(will_break)}</div><div>flows will stop working</div></div>
<div class="tile"><div class="n">{len(owned_safe)}</div><div>owned by them but safe</div></div>
<div class="tile"><div class="n">{envs}</div><div>environments checked</div></div>
</div>

<section style="display:flex;flex-direction:column;gap:10px">
<h2>Will stop working</h2>
<div class="tablewrap"><table>
<thead><tr><th>Flow</th><th>Runs on their login through</th><th>Status shown today</th><th>Suggested next owner</th></tr></thead>
<tbody>{"".join(rows) or '<tr><td colspan="4">None found.</td></tr>'}</tbody></table></div>
</section>

<section style="display:flex;flex-direction:column;gap:10px">
<h2>Owned by them, but safe</h2>
<p class="sub">An owner-based list would flag these too. They run on someone else's login, so they keep working.</p>
<div class="tablewrap"><table>
<thead><tr><th>Flow</th><th>Runs as</th><th>What happens</th></tr></thead>
<tbody>{safe_rows or '<tr><td colspan="3">None found.</td></tr>'}</tbody></table></div>
</section>

<div class="note"><b>Why the owner list isn't enough.</b> Filtering by owner gives {owner_filter} flows here, and only {len(owned_breaking)} of those depend on this person's login{f". {len(will_break) - len(owned_breaking)} more that they don't own would be missed" if len(will_break) > len(owned_breaking) else ""}. In testing, flows that lost their owner's login kept showing as On, and the error asked for the connection to be "signed in again", blaming a changed password or a policy.</div>

<section style="display:flex;flex-direction:column;gap:10px">
<h2>Before the last day</h2>
<ol>
<li>For each flow above, agree who takes it over.</li>
<li>That person opens the flow, uses Change connection on each step listed, picks their own connection, and saves. For flows in a solution, update the connection reference instead.</li>
<li>Run each flow once and check it succeeds.</li>
<li>Run this report again. The list should be empty.</li>
</ol>
</section>

<footer>Read-only report. Microsoft, Power Automate and Power Platform are trademarks of the Microsoft group of companies. Independent project, not affiliated with Microsoft.</footer>
</div></body></html>
"""
