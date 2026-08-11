#!/usr/bin/env python3
"""Compose a repository's AGENTS.md from the shared sources in this directory.

The generated block is delimited by markers. Anything a repository's own
maintainers write outside those markers is preserved on every sync, so a repo
can add "never run X here, always build with Y" without fighting the generator.

Usage:
    generate.py render <repo>                 print the generated block
    generate.py apply  <repo> <path>          write/splice AGENTS.md at <path>
    generate.py check  <repo> <path>          exit 1 if <path> is out of date
    generate.py repos                         print the sync matrix as JSON

No third-party dependencies: this runs in CI and on a laptop with a bare
Python 3.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = "kairos-io/community/agent-conventions"

BEGIN = f"<!-- BEGIN GENERATED FROM {SOURCE} — DO NOT EDIT THIS BLOCK BY HAND -->"
END = "<!-- END GENERATED -->"

CUSTOM_HEADER = """
<!-- Anything below this line belongs to this repository and is preserved on sync. -->
"""


def load_repos():
    return json.loads((HERE / "repos.json").read_text())


def render(repo):
    repos = load_repos()
    if repo not in repos:
        sys.exit(f"unknown repo {repo!r}; add it to agent-conventions/repos.json")

    parts = [(HERE / "base.md").read_text().rstrip()]
    for overlay in repos[repo]["overlays"]:
        path = HERE / "overlays" / f"{overlay}.md"
        if not path.exists():
            sys.exit(f"missing overlay {path}")
        parts.append(path.read_text().strip())

    body = "\n\n".join(parts)
    return f"{BEGIN}\n<!-- Edit the sources there, not this file. -->\n\n{body}\n\n{END}\n"


def splice(existing, generated):
    """Replace the generated block, keeping whatever the repo added around it."""
    if BEGIN in existing and END in existing:
        head, rest = existing.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        return f"{head}{generated.rstrip()}{tail}"
    if existing.strip():
        # Pre-existing hand-written file: keep it below the generated block.
        return f"{generated}{CUSTOM_HEADER}\n{existing.strip()}\n"
    return generated


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]

    if cmd == "repos":
        repos = load_repos()
        matrix = [
            {"repo": name, "branch": repos[name]["branch"]} for name in sorted(repos)
        ]
        print(json.dumps(matrix))
        return

    if len(sys.argv) < 3:
        sys.exit(__doc__)
    repo = sys.argv[2]
    generated = render(repo)

    if cmd == "render":
        print(generated, end="")
        return

    if len(sys.argv) < 4:
        sys.exit(__doc__)
    target = pathlib.Path(sys.argv[3])
    existing = target.read_text() if target.exists() else ""
    wanted = splice(existing, generated)

    if cmd == "apply":
        target.write_text(wanted)
        return

    if cmd == "check":
        if existing != wanted:
            sys.exit(
                f"{target} is out of date with {SOURCE}.\n"
                f"Do not edit the generated block by hand — it is overwritten on "
                f"every sync.\nRegenerate with: generate.py apply {repo} {target}"
            )
        return

    sys.exit(__doc__)


if __name__ == "__main__":
    main()
