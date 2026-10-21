"""Assemble the public pages. Usage: python3 tools/site/build.py "<Product name>" "<repo url>" <out_dir>"""
import sys
from pathlib import Path

SRC = Path(__file__).parent  # templates live next to this script
name, repo, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)

HEAD = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'

FOOT = ('<footer style="max-width:860px;margin:0 auto;padding:0 16px 40px;font-size:.8rem;color:var(--muted)">'
        'Microsoft, Power Automate, Power Platform and Copilot Studio are trademarks of the Microsoft group of companies. '
        'This is an independent project and is not affiliated with, sponsored or endorsed by Microsoft.</footer>\n')


def nav(other, label):
    return (f'<nav style="max-width:860px;margin:0 auto;padding:16px 16px 0;font-family:var(--mono);font-size:.8rem">'
            f'<a href="{other}">{label} &rarr;</a> &middot; <a href="{repo}">Code on GitHub</a></nav>\n')


def fill(s):
    return s.replace("{{NAME}}", name).replace("{{REPO}}", repo)


def page(head, body, other, label):
    return (HEAD + (SRC / head).read_text() + "</head>\n<body>\n" + nav(other, label)
            + fill((SRC / body).read_text()) + FOOT + "</body>\n</html>\n")


(out / "index.html").write_text(page("journal-head.html", "journal-body.html", "decisions.html", "Decision log"))
(out / "decisions.html").write_text(page("log-head.html", "log-body.html", "index.html", "Build journal"))
print("built", out)
