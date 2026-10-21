# Leaver Impact Check

Before someone leaves, see which Power Automate flows run on their login and will stop working the day their account is switched off.

Works with Microsoft Power Automate and Power Platform. Independent project, not affiliated with or endorsed by Microsoft.

**Build journal:** https://pvikash789-rgb.github.io/leaver-impact-check/
**Decision log:** https://pvikash789-rgb.github.io/leaver-impact-check/decisions.html

## Why

A cloud flow signs in to services through connections, and a connection usually belongs to the person who created it. When that person's sign-in is blocked, flows that run on their connections fail. Adding a co-owner doesn't change which connection a flow uses.

In a test tenant, after blocking one user's sign-in:

- 6 of 6 test flows behaved as predicted. The four that ran on that user's connections failed, the two that didn't kept working.
- A co-owned flow failed on its first run after the block and stayed switched on.
- The error said the connection "needs to be signed-in again" and blamed a changed password or a policy. It didn't mention that the owner had left.

Details and caveats are in the build journal.

## What it does today

`leaver_impact_check.py` signs in as a Power Platform admin, reads environments, flows, connections and (for solution flows) connection references, and lists the flows that run on the given person's connections. It only reads. Results are saved to a local `out/` folder, which is ignored by git.

In the test tenant it named exactly the four flows that later broke and left out the two that didn't.

## Run it

Needs Python 3.10 or later and a Power Platform admin account.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install msal requests
python leaver_impact_check.py --tenant yourtenant.onmicrosoft.com --leaver person@yourtenant.onmicrosoft.com
```

A browser window opens for sign-in. No passwords or tokens are stored.

## Limits (spike version)

- Signs in with the public client ID that Microsoft's Power Apps admin PowerShell module uses. A release will use its own app registration with read-only permissions.
- Matches the leaver by the sign-in name recorded on each connection.
- Flows only. Copilot Studio agents come next.
- Tested on one small trial tenant.

## Lab

The test cases are described in [`lab/README.md`](lab/README.md).

---

Microsoft, Power Automate, Power Platform and Copilot Studio are trademarks of the Microsoft group of companies.
