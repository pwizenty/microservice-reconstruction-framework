## Summary

CI has failed on every run, for a long time, and checked nothing while doing
it.

```diff
  - uses: actions/checkout@v4
+ - uses: astral-sh/setup-uv@v10.3.0     # uv was never installed
  - run: make init
- - run: make install                     # alias for init
- - run: make html                        # Sphinx — removed by ADR-0005
- - run: make run                          # mrf with no -p/-t; needs a database
+ - run: make check                        # lint · format · types · tests
```

Three things were wrong, and the missing `uv` was only the most visible:

```text
uv sync --locked --all-groups
make: uv: No such file or directory
make: *** [Makefile:32: init] Error 127
```

**`make html` could never have worked.** The Makefile was a Sphinx makefile
whose catch-all routed unknown targets to `sphinx-build`, and **ADR-0005
removed Sphinx** along with `docs/source`.

**`make run` could never have worked either.** `mrf` without `-p` and `-t`
raises rather than printing usage — it is in `CLAUDE.md` under *Known issues* —
and it would need MongoDB.

So the workflow reported failure while verifying nothing, which is worse than
having no workflow at all: **a red mark that is always red carries no
information.** GitHub marked every pull request `UNSTABLE`, and six merged PRs
went in under it.

The Makefile now carries the targets `CLAUDE.md` already defines as "done" —
`ruff check`, `ruff format --check`, `mypy`, `pytest` — behind `make check`,
and CI runs exactly that. A green pipeline and a green working copy now mean
the same thing.

## Evidence

**Before**, on every branch and every push to `dev`:

```console
$ gh run list --limit 8
  failure  fix/runtime-operation-environment  (pull_request)
  failure  dev                                (push)
  failure  docs/process-diagram               (pull_request)
  failure  dev                                (push)
  failure  docs/refactoring-proposals         (pull_request)
  …
```

**After**, locally, which is now the same command CI runs:

```console
$ make check
uv run ruff check          All checks passed!
uv run ruff format --check 143 files already formatted
uv run mypy                Success: no issues found in 57 source files
uv run pytest -q           150 passed
```

The workflow parses and its four steps resolve:

```text
(checkout)           -> actions/checkout@v4
Install uv           -> astral-sh/setup-uv@v10.3.0
Install dependencies -> make init
Check                -> make check
```

**The action is pinned to an exact release, not a moving major tag.** This is
research software whose results have to be reproducible, and a tag that moves
underneath us is the opposite of that. Checked against the upstream API rather
than assumed: the latest release is `v10.3.0`, and there is **no `v10` major
tag** — only `v4` … `v7`, which would have been silently years out of date.

`make help` lists every target, so the file documents itself.

## Merge Danger

**Door:** two-way. A workflow, a Makefile and one line of `CLAUDE.md`.

**Blast Radius:** pull requests start being blocked

This is the point, and it is still a change in behaviour worth stating:

- **A red check will now mean something.** Until now every PR was `UNSTABLE`
  and mergeable anyway. After this, a PR that breaks lint, formatting, types or
  tests will be *correctly* blocked — including, possibly, work in flight that
  has been relying on nobody reading the check.
- **Integration tests are deliberately excluded.** `make integration` needs
  Docker and a database; running it here would reintroduce a permanently-red
  check, which is the problem being fixed.
- **`make install` is kept as an alias for `init`** so anything calling it
  still works, even though the workflow no longer does.
- **The Sphinx scaffolding is removed from the Makefile.** `make html` and the
  catch-all that routed unknown target names to `sphinx-build` are gone, which
  is what ADR-0005 implies. Anyone with that in muscle memory will now get
  `No rule to make target` instead of a confusing `sphinx-build` failure.

One thing this does **not** fix: the LEMMA repository has no CI at all, so
everything there is still verified by hand with the Xtend batch compiler.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
