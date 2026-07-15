#!/usr/bin/env python3
"""Annotate CONTRIBUTORS.md with each contributor's most recent activity.

For every contributor listed in CONTRIBUTORS.md, this queries the public
GitHub Search API for the most recent thing they were involved in across the
kairos-io org (issues, PRs, comments, reviews, mentions) and their most recent
commit. The newer of the two determines a coarse recency bucket and a link to
that activity, which is written back into the table as a "Last activity" column.

Purely informational: it supports the GOVERNANCE.md off-boarding review, it does
not take any action on its own. See .github/workflows/contributor-activity.yml.
"""

import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ORG = "kairos-io"
CONTRIBUTORS_FILE = os.environ.get("CONTRIBUTORS_FILE", "CONTRIBUTORS.md")
API = "https://api.github.com"
ACTIVITY_HEADER = "Last activity"

# Minimum spacing between Search API requests, to stay clear of the secondary
# rate limits (~30 req/min authenticated). Applied once per request.
SLEEP_BETWEEN_CALLS = float(os.environ.get("ACTIVITY_SLEEP", "2"))
# Retries for transient failures (network blips, rate limiting).
MAX_RETRIES = 4

# Bucket thresholds in days, evaluated in order; first match wins.
BUCKETS = [
    (7, "🟢 This week"),
    (31, "🟢 This month"),
    (92, "🟡 This quarter"),
    (183, "🟡 This half-year"),
    (365, "🟠 This year"),
]
OLDER_LABEL = "🔴 Over a year"
NONE_LABEL = "⬜ No activity found"

# Matches a "[@handle](url)" cell, capturing the handle.
HANDLE_RE = re.compile(r"\[@([A-Za-z0-9-]+)\]")
FOOTER_RE = re.compile(r"^_Last activity refreshed .*_$")


def _is_rate_limited(exc):
    """True if an HTTPError represents primary/secondary rate limiting."""
    if exc.code == 429:
        return True
    if exc.code == 403:
        headers = exc.headers or {}
        # Secondary limit signals a Retry-After; primary limit exhausts the
        # remaining budget. A permission/auth 403 has neither.
        if headers.get("Retry-After") is not None:
            return True
        if headers.get("X-RateLimit-Remaining") == "0":
            return True
    return False


def _retry_wait(exc, attempt):
    """How long to sleep before retrying a rate-limited request."""
    headers = exc.headers or {}
    retry_after = headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return int(retry_after)
    # Fall back to exponential-ish backoff.
    return min(60, 5 * (attempt + 1))


def api_get(path, params):
    """GET a GitHub API endpoint, returning parsed JSON.

    Returns None when the query is rejected (HTTP 422 — e.g. the account no
    longer exists). Retries transient network errors and genuine rate limiting.
    Fails loudly (exits) on auth/permission errors, since those are a workflow
    misconfiguration that silently degrading the output would hide.
    """
    query = urllib.parse.urlencode(params)
    url = f"{API}{path}?{query}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    for attempt in range(MAX_RETRIES):
        # Throttle before every request (no wasted trailing sleep elsewhere).
        time.sleep(SLEEP_BETWEEN_CALLS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if _is_rate_limited(exc):
                wait = _retry_wait(exc, attempt)
                print(f"  rate limited, sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if exc.code == 422:
                return None  # query rejected / account gone
            if exc.code in (401, 403):
                sys.exit(
                    f"error: {exc.code} from {path} — check the token's "
                    f"permissions; refusing to silently degrade output."
                )
            print(f"  warning: {exc.code} for {url}", file=sys.stderr)
            return None
        except (urllib.error.URLError, socket.timeout) as exc:
            print(f"  transient error ({exc}); retrying", file=sys.stderr)
            time.sleep(min(60, 5 * (attempt + 1)))

    sys.exit(f"error: giving up on {path} after {MAX_RETRIES} attempts")


def parse_ts(value):
    """Parse an ISO-8601 timestamp (e.g. 2026-07-09T06:00:00Z) as aware UTC."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def latest_involvement(handle):
    """Most recent issue/PR the user is involved in, org-wide. -> (ts, url)."""
    data = api_get(
        "/search/issues",
        {
            "q": f"org:{ORG} involves:{handle}",
            "sort": "updated",
            "order": "desc",
            "per_page": 1,
        },
    )
    items = (data or {}).get("items") or []
    if not items:
        return None, None
    return parse_ts(items[0].get("updated_at")), items[0].get("html_url")


def latest_commit(handle):
    """Most recent commit authored by the user, org-wide. -> (ts, url)."""
    data = api_get(
        "/search/commits",
        {
            "q": f"org:{ORG} author:{handle}",
            "sort": "author-date",
            "order": "desc",
            "per_page": 1,
        },
    )
    items = (data or {}).get("items") or []
    if not items:
        return None, None
    commit = items[0].get("commit", {})
    ts = parse_ts(commit.get("author", {}).get("date"))
    return ts, items[0].get("html_url")


def bucket_for(now, ts):
    """Return the recency label for a (non-None) last-activity timestamp."""
    age_days = (now - ts).total_seconds() / 86400
    for threshold, label in BUCKETS:
        if age_days <= threshold:
            return label
    return OLDER_LABEL


def last_activity_cell(handle, now):
    """Compute the linked recency cell for a single contributor."""
    inv_ts, inv_url = latest_involvement(handle)
    commit_ts, commit_url = latest_commit(handle)

    candidates = [(t, u) for t, u in ((inv_ts, inv_url), (commit_ts, commit_url)) if t]
    if not candidates:
        return NONE_LABEL

    ts, url = max(candidates, key=lambda c: c[0])
    label = bucket_for(now, ts)
    return f"[{label}]({url})" if url else label


def split_row(line):
    """Split a markdown table row into its trimmed cell values."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def make_row(cells):
    return "| " + " | ".join(cells) + " |"


def is_separator(line):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}", line)) and set(line.strip()) <= set("|-: ")


def rewrite(text, now):
    """Rewrite the contributor table in-place, adding the activity column.

    Preserves whatever base columns the table already has (Contributor,
    GitHub ID, and any future additions) and (re)appends "Last activity" as the
    final column. Fails loudly on a malformed table rather than corrupting it.
    """
    lines = text.splitlines()

    # Locate the header row: a table row naming both required columns.
    header_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and "Contributor" in line and "GitHub ID" in line:
            header_idx = i
            break
    if header_idx is None:
        sys.exit("error: could not find the contributor table header")

    sep_idx = header_idx + 1
    if sep_idx >= len(lines) or not is_separator(lines[sep_idx]):
        sys.exit("error: expected a separator row under the table header")

    header_cells = split_row(lines[header_idx])
    # If we've run before, the last column is ours — strip it to get the base.
    has_activity = bool(header_cells) and header_cells[-1] == ACTIVITY_HEADER
    base_header = header_cells[:-1] if has_activity else header_cells
    n_base = len(base_header)

    gh_idx = next((i for i, c in enumerate(base_header) if "GitHub ID" in c), None)
    if gh_idx is None:
        sys.exit("error: could not find the 'GitHub ID' column in the header")

    # Collect contiguous data rows.
    start = sep_idx + 1
    end = start
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1

    new_rows = []
    for line in lines[start:end]:
        cells = split_row(line)
        base_cells = cells[:-1] if has_activity else cells
        if len(base_cells) != n_base:
            sys.exit(
                f"error: malformed table row (expected {n_base} columns, "
                f"got {len(base_cells)}): {line!r}"
            )
        github_id = base_cells[gh_idx]
        match = HANDLE_RE.search(github_id)
        if not match:
            cell = NONE_LABEL
        else:
            handle = match.group(1)
            print(f"  {handle} ...", file=sys.stderr)
            cell = last_activity_cell(handle, now)
        new_rows.append(make_row(base_cells + [cell]))

    header = make_row(base_header + [ACTIVITY_HEADER])
    separator = make_row(["---"] * (n_base + 1))

    rebuilt = lines[:header_idx] + [header, separator] + new_rows + lines[end:]

    # Update or insert the footer line.
    stamp = now.strftime("%Y-%m-%d")
    footer = f"_Last activity refreshed {stamp} (UTC)._"
    for i, line in enumerate(rebuilt):
        if FOOTER_RE.match(line):
            rebuilt[i] = footer
            break
    else:
        insert_at = header_idx + 2 + len(new_rows)
        rebuilt.insert(insert_at, "")
        rebuilt.insert(insert_at + 1, footer)

    return "\n".join(rebuilt) + "\n"


def main():
    with open(CONTRIBUTORS_FILE, encoding="utf-8") as fh:
        text = fh.read()
    now = datetime.now(timezone.utc)
    updated = rewrite(text, now)
    with open(CONTRIBUTORS_FILE, "w", encoding="utf-8") as fh:
        fh.write(updated)
    print("CONTRIBUTORS.md updated.", file=sys.stderr)


if __name__ == "__main__":
    main()
