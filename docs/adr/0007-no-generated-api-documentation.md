# ADR-0007: Keep hand-written records instead of generated API documentation

- Status: Proposed
- Date: 2026-09-29
- Deciders: Philip Wizenty
- Supersedes: – (narrows the documentation part of ADR-0005)

## Context and problem statement
ADR-0005 settled the toolchain and included a Sphinx build: `sphinx.ext.napoleon`
for the Google-style docstrings and `myst-parser` so that the ADRs render into
the same site. What actually existed under `docs/source/` was the output of
`sphinx-apidoc`: `mrf.rst`, `mrf.modules.rst`, `mrf.plugins.*.rst`,
`mrf.repositories*.rst`, `mrf.utilities.rst` plus `conf.py`, `index.rst` and a
`Makefile`. Those files carry no prose of their own. They enumerate the packages
so that Sphinx can pull the docstrings out of the modules, and they have to be
regenerated whenever a module is added or renamed - `mrf/plugins/operation/` is
already listed although the package is an empty stub.

Meanwhile the documentation that is read while working on this project lives
elsewhere and is hand-written: `CLAUDE.md` for the architecture, the dependency
direction and the conventions, and `docs/adr/` for the decisions. Both are
Markdown, both render on GitHub, and neither needs a build.

The Sphinx scaffolding was removed in a preceding commit, which leaves ADR-0005
describing a build that no longer exists.

## Decision drivers
- Reproducibility: every dependency in `uv.lock` is one more thing to pin and to
  reinstall for a result to be reproduced
- The documentation that is actually consulted should be the documentation that
  is maintained
- Generated files that must be kept in sync by hand go stale silently
- TODO(author): whether the dissertation or a tool paper has to ship a browsable
  API reference. If so, this decision has to be revisited before submission.

## Considered options
1. Drop the generated API documentation, keep `CLAUDE.md` and the ADRs
2. Repair the Sphinx setup: regenerate the `sphinx-apidoc` output, wire up
   `napoleon` and `myst-parser` as ADR-0005 planned
3. Replace Sphinx with MkDocs and `mkdocstrings`, which reads the docstrings
   without checked-in stub files
4. Keep status quo: leave the Sphinx configuration in the repository unbuilt

## Decision
Chosen option: "Drop the generated API documentation", because the removed pages
duplicated docstrings the reader can see in the source, while the documentation
that carries judgement - why a plugin is structured the way it is, why the
parser is a fork - is hand-written and unaffected. Dropping the `docs`
dependency group removed 24 packages from the lock file, which serves
reproducibility directly.

Docstrings stay Google-style. Nothing about that depended on Sphinx: `ruff`
selects the `D` rules with `convention = "google"` (`pyproject.toml`), so the
convention is enforced on every commit whether or not anything renders it.

## Consequences
- Positive: 24 fewer locked packages; no generated `.rst` files to regenerate
  when a module moves; the ADRs and `CLAUDE.md` render on GitHub with no build
  step; `uv sync --all-groups` is faster.
- Negative: no browsable API reference. Anyone who wants an overview of the
  model classes reads `mrf/modules/` directly. ADR-0005's plan to render the
  ADRs through `myst-parser` is void, so the ADRs are read as files.
- Follow-up tasks:
  - ADR-0005 amended to point here instead of describing the Sphinx build.
  - TODO(author): if documentation returns, prefer option 3. `mkdocstrings`
    reads the docstrings without stub files, which removes the failure mode
    that made the `sphinx-apidoc` output go stale.

## Pros and cons of the options
### Drop the generated API documentation
- Good, because it removes 24 dependencies that served files nobody read.
- Good, because the remaining documentation needs no build to be readable.
- Bad, because there is no rendered reference to link to from a paper.

### Repair the Sphinx setup
- Good, because ADR-0005 already described it, and `myst-parser` would put the
  ADRs and the API reference on one site.
- Bad, because the `sphinx-apidoc` stubs stay a hand-maintained duplicate of the
  package layout, which is what let them drift in the first place.

### Replace Sphinx with MkDocs and mkdocstrings
- Good, because it renders docstrings without checked-in stub files.
- Bad, because it is a new toolchain to learn and pin for documentation that has
  no reader yet.

### Keep status quo
- Bad, because a configuration that is never built is indistinguishable from one
  that is broken, and it still has to be installed.
