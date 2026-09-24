## Go

- Build and test through the repository's `Makefile` target where there is one.
  `go build ./...` on its own can fail on a fresh clone in repositories whose
  packages embed generated files. If a module proxy is unreachable in your
  environment, say so rather than claiming the tests passed.
- Do not bump the Go version or dependencies as a side effect of an unrelated
  change. Renovate handles routine bumps.
- Check whether `kairos/sdk` already wraps a dependency before adding it.
- Write tests in the ginkgo/gomega style the rest of the tree uses.
