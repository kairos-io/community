# Agent conventions

Shared instructions for AI coding agents working on kairos-io repositories.
Each repository gets an `AGENTS.md` composed from the sources here, so an agent
arrives already knowing how our repos relate, how we commit, and what usually
goes wrong.

Implements [kairos-io/kairos#4246](https://github.com/kairos-io/kairos/issues/4246).

## Layout

| Path | What it is |
|---|---|
| `base.md` | Org-wide content. Every repository gets this |
| `overlays/` | Per-stack additions (`go`, `dockerfile`), applied only where relevant |
| `repos.json` | Which repositories sync, their default branch, and their overlays |
| `generate.py` | Composes `AGENTS.md`. No dependencies |
| `examples/drift-check.yml` | Optional downstream CI that rejects hand-edits |

## Usage

```sh
./generate.py render kairos              # print what kairos would get
./generate.py apply  kairos ../kairos/AGENTS.md
./generate.py check  kairos ../kairos/AGENTS.md   # exit 1 if stale
```

Adding a repository is one entry in `repos.json`. Adding a rule is one line in
`base.md` or an overlay.

## Why it is built this way

**Why generated files in each repo, rather than a pointer to a central file.**
Both were on the table in #4246. A pointer is always current and costs nothing
to maintain, and that is a real advantage. We went the other way for two
reasons. A pointer resolves over the network at agent-runtime, so it fails
silently — a network hiccup or a moved URL degrades into an agent working with
no conventions at all, and nothing announces that. And the content is only
visible if you already know to go looking, which is backwards for the case that
motivated this: contributors who did not know a requirement existed. A checked-
in file is right there on clone, greppable, and diffable in review.

The cost of pushing is drift and propagation lag. Drift is handled by the
markers plus `examples/drift-check.yml`; the lag is a pull request, which is
visible, rather than a silent gap.

**Why the file is short.** The concern raised in #4246 was context budget: a
large specification loaded at the start of every session is paid for on every
session, before any work happens. The reference implementation cited in that
thread ships a ~120 KB specification — roughly 30,000 tokens up front. `base.md`
is deliberately a couple of hundred lines, and grows only when an agent has
actually got something wrong. Depth belongs in skills, which load on demand.

**Why skills are not in here.** `kairos-io/skills` already exists and holds
real, tested procedures. Duplicating them here would fork them. `base.md`
points at that repository instead. See the open question below.

**Why each repo keeps its own section.** Everything outside the generated
markers survives a sync, so a repository can carry its own "never run X here"
without negotiating with this repo.

## Conventions for changing this

Rules earn their place. Add one when an agent has actually made the mistake,
not when you can imagine it making the mistake — the value of this file is
inversely proportional to its length. Every rule currently in `base.md` traces
to something observed in our repositories.

## Open questions for review

1. **`kairos-io/skills` is private**, so `base.md` names it without linking to
   it — a link would 404 for most readers of this public repo. Making it public
   would be better for contributors and is worth deciding on its own merits.
2. **Which disclosure trailer?** The trailer is in `base.md` now — it was left
   out of the first draft on the grounds that nobody actually used it, and
   review said the team wants it, which settles that. What is still open is the
   spelling: #4246 proposed `Co-developed-by:` following systemd, while
   `Co-Authored-By:` is what GitHub itself recognises and renders. `base.md`
   currently uses the former. Worth picking one deliberately.
3. **The sync workflow needs an `AGENT_CONVENTIONS_TOKEN` secret** with
   `contents:write` and `pull-requests:write` on the target repositories.
   Nothing syncs until that exists.
4. **This lives in `community` rather than a dedicated `agent-conventions`
   repo** as #4246 proposed. `community` already holds `GOVERNANCE.md` and
   `CONTRIBUTING.md`, so org-wide conventions are not out of place, and it
   avoids standing up a repository before we know this is worth keeping. Easy
   to move later if it earns its own home.
