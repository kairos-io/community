## Go

- Build and test the whole tree before opening a pull request. Use the
  repository's `Makefile` target where there is one: `go build ./...` on its
  own can fail on a fresh clone in repositories whose packages embed generated
  files. If a module proxy is unreachable in your environment, say so in the
  pull request rather than claiming the tests passed.
- Do not bump the Go version or dependencies as a side effect of an unrelated
  change. Renovate handles routine bumps and a manual bump buried in a feature
  branch is hard to review and hard to revert.
- When adding a dependency, check whether the SDK, `kairos/sdk`, already
  wraps it.
- When creating new tests, follow the ginkgo/gomega style as the rest of the
  tests in kairos projects do.
