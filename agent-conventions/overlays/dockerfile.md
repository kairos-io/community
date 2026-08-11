## Dockerfiles

- Keep one logical step per `RUN`. Do not collapse unrelated commands into a
  single long line to save a layer. It makes the diff unreadable and the
  failure unattributable.
- Pin versions with a build argument rather than inlining them, so Renovate can
  see and update them.
- **Do not add a `wget` or `curl` of an upstream tarball to a build.** Source
  fetching is deliberately off the critical path: sources are mirrored into our
  own registry and pulled from there. In `hadron`, add the tarball to
  `sources.yaml` with its checksum and candidate URLs, and the
  `populate-sources` workflow publishes it as
  `ghcr.io/kairos-io/hadron-sources/<pkg>:<version>` for the build to consume.
- `hadolint` runs in CI. Run it locally before pushing.
