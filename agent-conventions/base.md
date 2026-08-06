# Working on kairos-io

Kairos builds immutable Linux distributions for edge and Kubernetes. Changes
usually cross repository boundaries, so orient yourself before editing.

## Repository map

| Repo | What it is |
|---|---|
| `kairos` | Umbrella repo: docs entry point, e2e tests, release orchestration, **and the issue tracker for the whole org** |
| `kairos-sdk` | Shared Go library. Changes here ripple everywhere downstream |
| `kairos-agent` | The in-system agent: install, upgrade, reset |
| `immucore` | Initramfs and mount logic. Boot-critical |
| `AuroraBoot` | Builds ISOs, raw disks and netboot artifacts |
| `kairos-init` | Turns a base image into a Kairos image |
| `hadron` | Minimal base OS built from source |
| `provider-kairos`, `osbuilder` | Kubernetes provider and image build tooling |

**Dependency direction:** `kairos-sdk` → (`kairos-agent`, `immucore`, `AuroraBoot`) → `kairos`.
A change to the SDK is not finished until the consuming repos are bumped to a
released SDK version. Do not pin a consumer to an unreleased pseudo-version.

**Issues live in `kairos-io/kairos`.** Most other repos have their issue
tracker disabled. File and search there, not in the repo you are editing.

## Before you open a pull request

- **Sign off every commit.** DCO is enforced by a required check; a commit
  without `Signed-off-by:` cannot merge. Use `git commit -s`.
- **Conventional Commits** for the subject line: `fix(iso): ...`, `docs: ...`.
- **Add a test** for any behaviour change. Boot-path changes need a boot test,
  not only a unit test — see the skills below.
- **Keep pull requests small and single-purpose.** Reviewer attention is the
  scarce resource here.
- **Never force-push or rebase someone else's branch**, and never stack a pull
  request on another unmerged branch.

## Things that will trip you up

- **The default branch is not the same everywhere.** `kairos` and `osbuilder`
  use `master`; every other repo uses `main`. Check before branching.
- **Pull requests from forks cannot read repository secrets.** Image-build jobs
  fail within seconds at "Login to registry". That failure is structural, not
  something your change caused — do not try to fix it, and do not tell a
  contributor their patch broke the build.
- **A red mirror is usually rate-limiting, not a dead URL.** Upstream source
  fetches fail transiently. Add a fallback; do not hardcode a different single
  point of failure.
- **Unit tests cannot prove a boot works.** If you changed anything in the boot
  path, boot it.

## Shared skills

Reusable, tested procedures for the hard parts — driving QEMU headlessly,
testing immucore in a real boot, cutting a backport release — live in the
`kairos-io/skills` repository. Prefer an existing skill over improvising.

## AI-assisted contributions

Whoever opens the pull request is responsible for every line in it, however it
was produced. The DCO sign-off is that certification — it is not a formality.
Review generated output before submitting it: the common failure is code that
is locally correct but misreads why the system is the way it is.
