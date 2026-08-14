#!/usr/bin/env python3
"""Repo-access audit for the kairos-io org.

Verifies every (non-archived) repo grants the standard governance team access:

    administrators -> admin
    maintainers    -> maintain
    contributors   -> triage

(see GOVERNANCE.md "Mapping Project Roles to GitHub Roles"). On drift it opens,
or updates the existing open, tracking issue in kairos-io/kairos. When a
previous run's issue is open and drift is now gone, it comments and closes it.

Run it whenever you want, not just on the monthly schedule:

    python scripts/repo_access_audit.py --dry-run          # report, touch nothing
    python scripts/repo_access_audit.py --dry-run --repo kairos
    python scripts/repo_access_audit.py                    # manage the issue

--dry-run makes no writes at all and exits 1 if there is drift, so it doubles
as a check you can run locally or wire into another job.

Auth: GH_TOKEN must belong to an organization member and needs `read:org` to
read the teams, plus `public_repo` to file the tracking issue in the (public)
kairos repo. `--dry-run` writes nothing, so `read:org` alone is enough for it.

It asks each governance team which repositories it can reach, rather
than asking each repository which teams reach it. The second form needs admin
on every repository, which in practice means an org owner, and it goes blind on
exactly the repositories the audit exists to find: if a team's grant is
missing, so is your admin, and the repo reads as unreadable instead of as
drift. Asking per team, a missing grant is simply an absent entry.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ORG = "kairos-io"
ISSUE_REPO = "kairos-io/kairos"
TITLE = "Repo access audit: team-permission drift"
EXPECT = {"administrators": "admin", "maintainers": "maintain", "contributors": "triage"}
GOVERNANCE = ("https://github.com/kairos-io/community/blob/main/GOVERNANCE.md"
              "#mapping-project-roles-to-github-roles")

# Repositories the governance mapping deliberately does not apply to. Keep the
# reason next to the name: an unexplained exclusion is how an audit quietly
# stops covering something it should.
EXCLUDE = {
    ".project": "owned by the CNCF, not by the Kairos maintainers",
}

# GitHub spells the same permission differently across endpoints: the base
# roles come back as read/write from some, pull/push from others. Compare on
# one vocabulary so a correct grant is never reported as drift.
NORMALIZE = {"read": "pull", "write": "push"}


def norm(role: str | None) -> str | None:
    return NORMALIZE.get(role, role)


def gh(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"error: gh {' '.join(args)}\n{r.stderr}")
    return r


def _loads(raw: str):
    """Parse gh output, including --paginate's concatenated JSON arrays.

    Past 100 results `gh api --paginate` emits one array per page, back to
    back, which is not valid JSON on its own. Stitch them together rather than
    failing, because the failure mode is silent and bad: an unparsed repo list
    looks like an empty org, which looks like "no drift".
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    decoder, out, idx = json.JSONDecoder(), [], 0
    raw = raw.strip()
    while idx < len(raw):
        value, end = decoder.raw_decode(raw, idx)
        if not isinstance(value, list):
            raise ValueError("expected a JSON array per page")
        out.extend(value)
        idx = end
        while idx < len(raw) and raw[idx].isspace():
            idx += 1
    return out


def gh_json(path: str):
    r = gh("api", path, "--paginate")
    if r.returncode != 0:
        return None
    try:
        return _loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def all_repos() -> dict[str, bool]:
    """Every repository in the org, mapped to whether it is archived."""
    data = gh_json(f"orgs/{ORG}/repos?type=all&per_page=100")
    if data is None:
        # Never treat this as "no repos": that would read as a clean audit and
        # close a legitimately open drift issue.
        sys.exit(f"error: could not list repositories for {ORG}; refusing to "
                 f"report a result. Check GH_TOKEN.")
    return {r["name"]: bool(r.get("archived")) for r in data}


def team_grants(slug: str) -> dict[str, str] | None:
    """Repositories this team can reach, mapped to its role on each."""
    data = gh_json(f"orgs/{ORG}/teams/{slug}/repos?per_page=100")
    if data is None:
        return None
    return {r["name"]: norm(r.get("role_name")) for r in data}


def audit(only: str | None = None):
    repos = all_repos()
    active = sorted(n for n, archived in repos.items()
                    if not archived and n not in EXCLUDE)
    if only:
        if only not in repos:
            sys.exit(f"error: {ORG}/{only} not found")
        if only in EXCLUDE:
            sys.exit(f"note: {ORG}/{only} is excluded from the audit "
                     f"({EXCLUDE[only]})")
        if repos[only]:
            sys.exit(f"note: {ORG}/{only} is archived; the audit skips "
                     f"archived repositories")
        active = [only]

    grants, unreadable_teams = {}, []
    for slug in EXPECT:
        got = team_grants(slug)
        if got is None:
            unreadable_teams.append(slug)
        else:
            grants[slug] = got

    if unreadable_teams:
        # Without a team's grants every repo would look like it is missing that
        # team. Report nothing rather than a page of false positives.
        sys.exit("error: could not read the repository list for team(s): "
                 + ", ".join(unreadable_teams)
                 + ". GH_TOKEN needs read:org and org membership.")

    drift = []
    for repo in active:
        problems = []
        for slug, want in EXPECT.items():
            got = grants[slug].get(repo)
            if got is None:
                problems.append(f"missing `{slug}` (want `{want}`)")
            elif got != norm(want):
                problems.append(f"`{slug}`=`{got}` (want `{want}`)")
        if problems:
            drift.append((repo, problems))
    return drift, len(active)


def build_body(drift, checked: int) -> str:
    out = [
        "## Repo access audit: drift detected",
        "",
        "Automated check from [`kairos-io/community`]"
        "(https://github.com/kairos-io/community/blob/main/.github/workflows/repo-access-audit.yml). "
        "Every repo should grant `administrators`=admin, `maintainers`=maintain, "
        f"`contributors`=triage ([GOVERNANCE.md]({GOVERNANCE})).",
        "",
        f"### Off the mapping ({len(drift)} of {checked} active repos)",
    ]
    out += [f"- `{repo}`: " + "; ".join(p) for repo, p in drift]
    out += [
        "",
        "Fix each with:",
        "```sh",
        "gh api -X PUT orgs/kairos-io/teams/<administrators|maintainers|contributors>/"
        "repos/kairos-io/<repo> -f permission=<admin|maintain|triage>",
        "```",
    ]
    if EXCLUDE:
        out += [
            "",
            "Archived repositories are skipped, as are these, deliberately: "
            + "; ".join(f"`{r}` ({why})" for r, why in sorted(EXCLUDE.items())) + ".",
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


def summarize(text: str) -> None:
    """Mirror the report into the Actions run summary, so an on-demand run is
    readable without opening the logs."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; do not open, update or close the tracking issue. "
                         "Exits 1 if drift was found.")
    ap.add_argument("--repo", metavar="NAME",
                    help="audit a single repository instead of the whole org")
    args = ap.parse_args()

    drift, checked = audit(args.repo)

    if not drift:
        msg = f"All {checked} active repos match the governance mapping."
        print(msg)
        summarize(f"## Repo access audit\n\n{msg}")
        if args.dry_run:
            return
        existing = open_audit_issue()
        if existing:
            gh("issue", "comment", existing, "--repo", ISSUE_REPO,
               "--body", "Resolved: all repos now match the governance mapping. Closing.",
               check=True)
            gh("issue", "close", existing, "--repo", ISSUE_REPO, check=True)
            print(f"Closed resolved issue #{existing}")
        return

    body = build_body(drift, checked)
    print(body)
    summarize(body)

    if args.dry_run:
        print("\n(dry run: no issue was opened, updated or closed)")
        sys.exit(1)

    existing = open_audit_issue()
    if existing:
        gh("issue", "comment", existing, "--repo", ISSUE_REPO, "--body", body, check=True)
        print(f"Updated existing issue #{existing}")
    else:
        r = gh("issue", "create", "--repo", ISSUE_REPO, "--title", TITLE, "--body", body, check=True)
        print(f"Opened issue: {r.stdout.strip()}")


if __name__ == "__main__":
    main()
