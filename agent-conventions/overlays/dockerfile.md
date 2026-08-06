## Dockerfiles

- Keep one logical step per `RUN`. Do not collapse unrelated commands into a
  single long line to save a layer — it makes the diff unreadable and the
  failure unattributable.
- Pin versions with a build argument rather than inlining them, so Renovate can
  see and update them.
- Fetching sources from an upstream mirror: provide a fallback. Mirrors
  rate-limit, and a single hardcoded URL turns a transient failure into red CI
  for everyone.
- `hadolint` runs in CI. Run it locally before pushing.
