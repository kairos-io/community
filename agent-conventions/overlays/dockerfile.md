## Dockerfiles

- One logical step per `RUN`. Do not collapse unrelated commands to save a
  layer.
- Pin versions with a build argument rather than inlining them, so Renovate can
  see them.
- Do not add a `wget` or `curl` of an upstream tarball. In `hadron`, add it to
  `sources.yaml` with its checksum and candidate URLs, and the
  `populate-sources` workflow publishes it as
  `ghcr.io/kairos-io/hadron-sources/<pkg>:<version>`.
- `hadolint` runs in CI. Run it locally before pushing.
