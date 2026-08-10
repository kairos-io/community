#!/usr/bin/env python3
"""Monthly repo-access audit for the kairos-io org.

Verifies every (non-archived) repo grants the standard governance team access:

    administrators -> admin
    maintainers    -> maintain
    contributors   -> triage

(see GOVERNANCE.md "Mapping Project Roles to GitHub Roles"). On drift, it opens
— or updates the existing open — tracking issue in kairos-io/kairos. When a
previous run's issue is open and drift is now gone, it comments and closes it.

Auth: the GH_TOKEN env var must belong to a kairos-io **org owner** (scopes
`read:org` + `repo`). Org owners have admin on every repo, which the
`/repos/{org}/{repo}/teams` endpoint requires; a lesser token 404s on repos it
can't administer and those are reported as "could not read".
"""
from __future__ import annotations

import json
import subprocess
import sys

ORG = "kairos-io"
ISSUE_REPO = "kairos-io/kairos"
TITLE = "Repo access audit: team-permission drift"
EXPECT = {"administrators": "admin", "maintainers": "maintain", "contributors": "triage"}
GOVERNANCE = ("https://github.com/kairos-io/community/blob/main/GOVERNANCE.md"
              "#mapping-project-roles-to-github-roles")


def gh(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"error: gh {' '.join(args)}\n{r.stderr}")
    return r


def gh_json(path: str):
    r = gh("api", path, "--paginate")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def active_repos() -> list[str]:
    data = gh_json(f"orgs/{ORG}/repos?type=all&per_page=100") or []
    return sorted(r["name"] for r in data if not r.get("archived"))


def audit():
    drift, unreadable = [], []
    for repo in active_repos():
        teams = gh_json(f"repos/{ORG}/{repo}/teams")
        if teams is None:
            unreadable.append(repo)
            continue
        tmap = {t["slug"]: t["permission"] for t in teams}
        problems = []
        for slug, want in EXPECT.items():
            got = tmap.get(slug)
            if got is None:
                problems.append(f"missing `{slug}` (want {want})")
            elif got != want:
                problems.append(f"`{slug}`=`{got}` (want `{want}`)")
        if problems:
            drift.append((repo, problems))
    return drift, unreadable


def build_body(drift, unreadable) -> str:
    out = [
        "## Repo access audit — drift detected",
        "",
        "Automated monthly check from [`kairos-io/community`]"
        "(https://github.com/kairos-io/community/blob/main/.github/workflows/repo-access-audit.yml). "
        f"Every repo should grant `administrators`=admin, `maintainers`=maintain, "
        f"`contributors`=triage ([GOVERNANCE.md]({GOVERNANCE})).",
        "",
    ]
    if drift:
        out.append(f"### ⚠️ Off the mapping ({len(drift)})")
        out += [f"- `{repo}` — " + "; ".join(p) for repo, p in drift]
        out.append("")
    if unreadable:
        out.append(f"### 🔒 Could not read ({len(unreadable)})")
        out.append("The audit token lacks admin on these (or they were removed): "
                   + ", ".join(f"`{r}`" for r in unreadable))
        out.append("")
    out += [
        "Fix each with:",
        "```sh",
        "gh api -X PUT orgs/kairos-io/teams/<administrators|maintainers|contributors>/"
        "repos/kairos-io/<repo> -f permission=<admin|maintain|triage>",
        "```",
    ]
    return "\n".join(out)


def open_audit_issue() -> str | None:
    r = gh("issue", "list", "--repo", ISSUE_REPO, "--state", "open",
           "--search", f'"{TITLE}" in:title', "--json", "number,title")
    if r.returncode != 0:
        return None
    try:
        for it in json.loads(r.stdout):
            if it.get("title") == TITLE:
                return str(it["number"])
    except json.JSONDecodeError:
        pass
    return None


def main() -> None:
    drift, unreadable = audit()
    existing = open_audit_issue()

    if not drift and not unreadable:
        print("All repos match the governance mapping.")
        if existing:
            gh("issue", "comment", existing, "--repo", ISSUE_REPO,
               "--body", "✅ Resolved — all repos now match the governance mapping. Closing.")
            gh("issue", "close", existing, "--repo", ISSUE_REPO)
            print(f"Closed resolved issue #{existing}")
        return

    body = build_body(drift, unreadable)
    print(body)
    if existing:
        gh("issue", "comment", existing, "--repo", ISSUE_REPO, "--body", body, check=True)
        print(f"Updated existing issue #{existing}")
    else:
        r = gh("issue", "create", "--repo", ISSUE_REPO, "--title", TITLE, "--body", body, check=True)
        print(f"Opened issue: {r.stdout.strip()}")


if __name__ == "__main__":
    main()
