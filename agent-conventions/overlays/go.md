## Go

- Follow [Effective Go](https://go.dev/doc/effective_go); `CONTRIBUTING.md` in
  `kairos-io/kairos` names it as the standard the core team holds to.
- Run `go build ./...` and `go test ./...` before opening a pull request. If a
  module proxy is unreachable in your environment, say so in the pull request
  rather than claiming the tests passed.
- Do not bump the Go version or dependencies as a side effect of an unrelated
  change. Renovate handles routine bumps and a manual bump buried in a feature
  branch is hard to review and hard to revert.
- When adding a dependency, check whether `kairos-sdk` already wraps it.
- When creating new tests, follow the ginkgo/gomega style as the rest of the tests in kairos projects do.
