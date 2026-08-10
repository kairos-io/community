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
| `kcrypt-discovery-challenger` | Network-based unlock for encrypted partitions |
| `kairos-operator` | The Kubernetes operator |
| `provider-kairos`, `osbuilder` | Kubernetes provider and image build tooling |
| `mudler/yip` | The cloud-config engine Kairos runs on. Outside the org, same people |

**Dependency direction:** `kairos-sdk` → (`kairos-agent`, `immucore`, `AuroraBoot`) → `kairos`.
A change to the SDK is not finished until the consuming repos are bumped to a
released SDK version. Do not pin a consumer to an unreleased pseudo-version.

**Fix things where they are broken.** Every repository above is maintained by
the same people, `mudler/yip` included. If the correct fix belongs upstream,
send it upstream. Do not work around it locally because you assume getting
it merged will be slow. It will not be.

**Issues live in `kairos-io/kairos`.** Most other repos have their issue
tracker disabled. File and search there, not in the repo you are editing.

## Is a human driving?

Some rules below depend on the answer. If you do not know, assume the first and
ask.

**A human is driving.** They review as you go. Do not push anything, to any
remote: not a fork, not upstream. Pushing is theirs to do once they have read
the commits. They add the sign-off at that point.

**Nobody is watching.** Push to a fork and open a pull request from it, never
to a branch on the upstream repository. Say plainly in the pull request body
that no human read the code before it was opened, so the reviewer knows what
they are looking at.

## Commits and pull requests

- **`Signed-off-by:` is a human's certification, not a formality.** DCO is
  enforced by a required check, so nothing merges without it. The person whose
  name is on it is stating they reviewed the result. An agent must not add it
  on someone's behalf; whoever reviews adds it when they have read the diff.
  Note that `-s` (the DCO trailer) is a different thing from `-S` (GPG
  signing). Never enable GPG signing yourself: it blocks waiting for a
  passphrase nobody is there to type.
- **Disclose AI involvement** with a `Co-developed-by:` trailer naming the
  model. The two trailers say different things. This one says AI was used; the
  sign-off says a human drove it and vouches for the result.
- **Conventional Commits** for the subject line: `fix(iso): ...`, `docs: ...`.
- **Set a new branch to track a remote branch of the same name.** A local
  branch left tracking `main` turns a later bare `git push` into a push
  straight to `main`.
- **Add a test** for any behaviour change. Boot-path changes need a boot test,
  not only a unit test. See the skills below. New tests follow the
  ginkgo/gomega style used across the kairos repositories.
- **Keep pull requests small and single-purpose.** Reviewer attention is the
  scarce resource here.
- **Never force-push or rebase someone else's branch**, and never stack a pull
  request on another unmerged branch.

## Writing

Text you write into files, commits and pull request descriptions should not
advertise itself as machine-written. No em dashes, no emojis. Prefer plain
words to acronyms and jargon, and do not assume the reader already knows the
system by heart.

## Things that will trip you up

- **The default branch is not the same everywhere.** `kairos` and `osbuilder`
  use `master`; every other repo uses `main`. Check before branching.
- **Pull requests from forks cannot read repository secrets.** Image-build jobs
  fail within seconds at "Login to registry". That failure is structural, not
  something your change caused. Do not try to fix it, and do not tell a
  contributor their patch broke the build.
- **Do not fetch sources from upstream during a build.** Upstream mirrors go
  down and rate-limit, and a red mirror is usually throttling rather than a
  dead URL, so swapping in another single hardcoded URL fixes nothing. Builds
  pull from our own cache instead. In `hadron`, add the tarball to
  `sources.yaml` and the `populate-sources` workflow republishes it under
  `ghcr.io/kairos-io/hadron-sources`.
- **Unit tests cannot prove a boot works.** If you changed anything in the boot
  path, boot it.

## Shared skills

Reusable, tested procedures for the hard parts live in the `kairos-io/skills`
repository: driving QEMU headlessly, testing immucore in a real boot, cutting a
backport release. Prefer an existing skill over improvising.

## AI-assisted contributions

Whoever signs off on a pull request is responsible for every line in it,
however it was produced. Read generated output before vouching for it: the
common failure is code that is locally correct but misreads why the system is
the way it is.

Be explicit rather than leaving a reader to wonder. `Co-developed-by:` records
that AI was involved; `Signed-off-by:` records that a human drove the work and
reviewed the result. A change that has had no human review yet should say so in
the pull request and should not carry anyone's sign-off until it has.
