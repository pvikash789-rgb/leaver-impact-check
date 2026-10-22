#!/usr/bin/env python3
"""
Leaver Impact Check (spike version): before someone leaves, see which flows run on their login.

Read-only. Signs in as a Power Platform admin through a normal browser sign-in,
lists flows and connections in every environment, joins them, and reports which
flows depend on the given person's connections.

Usage:
    python leaver_impact_check.py --tenant yourtenant.onmicrosoft.com --leaver person@yourtenant.onmicrosoft.com

Writes the full result to out/ (keep that folder out of git).
Spike only: uses the public client ID that Microsoft's own Power Apps admin
PowerShell module uses. A real release would use its own app registration.
"""
import argparse
import datetime
import json
import os
import sys

from report import render_html

CLIENT_ID = "1950a258-227b-4e31-a9cf-717495945fc2"
SCOPE_PA = ["https://service.powerapps.com//.default"]
SCOPE_FLOW = ["https://service.flow.microsoft.com//.default"]

ENVS_URL = ("https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform"
            "/scopes/admin/environments?api-version=2020-10-01")
FLOWS_URL = ("https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"
             "/scopes/admin/environments/{env}/v2/flows?api-version=2016-11-01")
FLOW_URL = ("https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"
            "/scopes/admin/environments/{env}/flows/{flow}?api-version=2016-11-01")
FLOW_PERMS_URL = ("https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"
                  "/scopes/admin/environments/{env}/flows/{flow}/permissions?api-version=2016-11-01")
CONNS_URL = ("https://api.powerapps.com/providers/Microsoft.PowerApps"
             "/scopes/admin/environments/{env}/connections?api-version=2016-11-01")


def say(msg=""):
    print(msg, flush=True)


class Session:
    def __init__(self, tenant):
        import msal  # only needed for a live scan
        self.app = msal.PublicClientApplication(
            CLIENT_ID, authority=f"https://login.microsoftonline.com/{tenant}")
        self.account = None

    def first_login(self, login_hint):
        # Normal browser sign-in (auth code + PKCE on localhost). Device code sign-in
        # is blocked by security defaults (error 530035), so we do not use it.
        say()
        say("=" * 70)
        say("A browser window will open. Sign in as the ADMIN account and approve")
        say("in Authenticator. When the page says you can close it, come back here.")
        say("=" * 70)
        result = self.app.acquire_token_interactive(
            scopes=SCOPE_PA, login_hint=login_hint, prompt="select_account")
        if "access_token" not in result:
            sys.exit("Sign-in failed: " + result.get("error_description", str(result)))
        self.account = self.app.get_accounts()[0]
        say(f"Signed in as {self.account.get('username')}")

    def token(self, scopes):
        result = self.app.acquire_token_silent(scopes, account=self.account)
        if not result or "access_token" not in result:
            return None
        return result["access_token"]


def get_all(url, token, label):
    """GET with paging. Returns list of items, or None if the call failed."""
    import requests  # only needed for a live scan
    items = []
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        if r.status_code != 200:
            say(f"  ! {label}: HTTP {r.status_code} {r.text[:300]}")
            return None
        data = r.json()
        if "value" in data:
            items.extend(data["value"])
            url = data.get("nextLink") or data.get("@odata.nextLink")
        else:
            return data
    return items


def norm(s):
    return (s or "").strip().lower()


def conn_refs(flow_detail):
    """Return list of (connector, connectionName or None, logicalName or None)."""
    props = flow_detail.get("properties", {}) if isinstance(flow_detail, dict) else {}
    refs = props.get("connectionReferences") or {}
    values = refs.values() if isinstance(refs, dict) else refs
    out = []
    for v in values:
        if not isinstance(v, dict):
            continue
        api = v.get("id") or v.get("apiId") or v.get("api", {}).get("id") or ""
        connector = api.rstrip("/").split("/")[-1] if api else v.get("displayName", "?")
        out.append((connector,
                    v.get("connectionName") or v.get("connection", {}).get("name"),
                    v.get("connectionReferenceLogicalName")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", help="tenant domain, e.g. contoso.onmicrosoft.com (live scan)")
    ap.add_argument("--leaver", help="UPN of the person leaving (live scan)")
    ap.add_argument("--admin", default=None, help="admin UPN to pre-fill on the sign-in page")
    ap.add_argument("--from-json", help="render a report from a saved result instead of scanning")
    ap.add_argument("--html", help="also write an HTML report to this path")
    args = ap.parse_args()

    if args.from_json:
        with open(args.from_json) as fh:
            report = json.load(fh)
        write_html(report, args.html or "out/report.html")
        return
    if not (args.tenant and args.leaver):
        ap.error("--tenant and --leaver are required for a live scan")
    leaver = norm(args.leaver)

    s = Session(args.tenant)
    s.first_login(args.admin)
    tok_pa = s.token(SCOPE_PA)
    tok_flow = s.token(SCOPE_FLOW)
    if not tok_flow:
        sys.exit("Could not get a token for Power Automate. Send this message to Claude.")

    envs = get_all(ENVS_URL, tok_pa, "environments") or []
    say(f"\nEnvironments found: {len(envs)}")

    report = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
              "leaver": args.leaver, "environments": []}
    at_risk = []

    for env in envs:
        env_id = env["name"]
        env_name = env.get("properties", {}).get("displayName", env_id)
        instance = (env.get("properties", {}).get("linkedEnvironmentMetadata") or {}).get("instanceUrl")
        say(f"\n--- {env_name} ---")

        conns = get_all(CONNS_URL.format(env=env_id), tok_pa, "connections") or []
        by_conn = {}
        users = {}
        for c in conns:
            p = c.get("properties", {})
            cb = p.get("createdBy") or {}
            who = cb.get("userPrincipalName") or cb.get("email") or cb.get("displayName") or cb.get("id")
            statuses = [st.get("status") for st in (p.get("statuses") or [])]
            by_conn[c["name"]] = {
                "connector": (p.get("apiId") or "").rstrip("/").split("/")[-1],
                "display": p.get("displayName"),
                "owner": who,
                "owner_id": cb.get("id"),
                "status": ",".join(s for s in statuses if s) or "?",
            }
            if cb.get("id"):
                users[cb["id"]] = who
        say(f"  connections: {len(conns)}")

        # Solution flows point to connection references, resolve them in Dataverse if we can.
        ref_to_conn = {}
        if instance:
            dv_scope = [instance.rstrip("/") + "/.default"]
            tok_dv = s.token(dv_scope)
            if tok_dv:
                rows = get_all(instance.rstrip("/") + "/api/data/v9.2/connectionreferences"
                               "?$select=connectionreferencelogicalname,connectionid",
                               tok_dv, "connection references") or []
                for row in rows:
                    ref_to_conn[row.get("connectionreferencelogicalname")] = row.get("connectionid")
                say(f"  connection references (Dataverse): {len(rows)}")
            else:
                say("  ! no Dataverse token, solution flows may show as unresolved")

        flows = get_all(FLOWS_URL.format(env=env_id), tok_flow, "flows") or []
        say(f"  flows: {len(flows)}")
        env_out = {"environment": env_name, "flows": []}

        for f in flows:
            fp = f.get("properties", {})
            detail = get_all(FLOW_URL.format(env=env_id, flow=f["name"]), tok_flow,
                             f"flow {fp.get('displayName')}") or {}
            creator_id = (fp.get("creator") or {}).get("objectId") or (fp.get("creator") or {}).get("userId")
            perms = get_all(FLOW_PERMS_URL.format(env=env_id, flow=f["name"]), tok_flow,
                            f"owners of {fp.get('displayName')}") or []
            owners = []
            for pm in perms if isinstance(perms, list) else []:
                pp = pm.get("properties", {})
                pid = (pp.get("principal") or {}).get("id")
                if pid and pid != creator_id:
                    owners.append({"who": users.get(pid, pid), "role": pp.get("roleName")})
            row = {"flow": fp.get("displayName"), "environment": env_name, "state": fp.get("state"),
                   "creator": users.get(creator_id, creator_id), "co_owners": owners, "connections": []}
            for connector, cname, logical in conn_refs(detail):
                if not cname and logical:
                    cname = ref_to_conn.get(logical)
                c = by_conn.get(cname, {})
                row["connections"].append({
                    "connector": connector, "connection": cname, "via_reference": logical,
                    "runs_as": c.get("owner") or "UNRESOLVED", "status": c.get("status", "?")})
            row["runs_on_leaver"] = any(norm(x["runs_as"]) == leaver for x in row["connections"])
            env_out["flows"].append(row)
            if row["runs_on_leaver"]:
                at_risk.append((env_name, row))

            mark = "  <-- RUNS ON LEAVER'S LOGIN" if row["runs_on_leaver"] else ""
            say(f"  * {row['flow']}  [{row['state']}]  creator: {row['creator']}{mark}")
            for x in row["connections"]:
                via = f" via ref {x['via_reference']}" if x["via_reference"] else ""
                say(f"      {x['connector']}: runs as {x['runs_as']} (status {x['status']}){via}")

        report["environments"].append(env_out)

    say("\n" + "=" * 70)
    say(f"Flows that run on {args.leaver}'s login: {len(at_risk)}")
    for env_name, row in at_risk:
        say(f"  - {row['flow']}  ({env_name}, {row['state']})")
    say("=" * 70)

    os.makedirs("out", exist_ok=True)
    path = os.path.join("out", f"leaver-impact-{datetime.datetime.now():%Y%m%d-%H%M}.json")
    with open(path, "w") as fh:
        json.dump(report, fh, indent=2)
    say(f"Full result saved to {path} (local only, do not commit).")
    write_html(report, args.html or path.replace(".json", ".html"))


def write_html(report, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(render_html(report))
    say(f"Report written to {path}")


if __name__ == "__main__":
    main()
