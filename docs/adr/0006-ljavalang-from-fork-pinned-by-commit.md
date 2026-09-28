# ADR-0006: Consume ljavalang from the pwizenty fork, pinned by commit

- Status: Proposed
- Date: 2026-09-28
- Deciders: Philip Wizenty
- Supersedes: –

## Context and problem statement
ADR-0003 kept `ljavalang` as the Java parser and ADR-0005 pinned it through
`uv.lock`. The released **ljavalang 2.1.0** on PyPI drops the annotations of
the first top-level type of a compilation unit, the conventional
`@Entity public class C` form. Since `has_annotation()` on that class is how
`JavaPlugin` finds bounded contexts and entities and how `SpringPlugin` finds
`@SpringBootApplication` and `@RestController`, MRF reconstructed nothing from
normally formatted Java. Commit `5f3ec0f` worked around this in
`java_utils.parse_java_file()` by re-reading the names from the token stream.

The workaround is no longer necessary. `github.com/pwizenty/Ljavalang` is the
project's own fork of ljavalang, and its `dev` branch carries commit
`330d58b` *"Add support for top-level annotations, e.g., @Entity for classes"*,
which repairs the parser itself. Verified against that commit: the annotation
is attached **and** records still parse, so the trade-off recorded in ADR-0003
disappears. The fix has never been released to PyPI, so a version constraint
cannot reach it.

MRF and the fork are therefore two repositories that have to move together, and
`ljavalang>=2.1` gave no way to express which revision of the parser a
reconstruction result depends on.

## Decision drivers
- Reproducibility: a published result must name the exact parser that produced it
- Reaching a fix that exists in the fork but not on PyPI
- CI and co-authors must resolve the dependency without extra credentials
- Keeping a local edit loop across both repositories while developing

## Considered options
1. Pin `ljavalang` to a fork commit via `[tool.uv.sources]` with `rev`
2. Keep status quo: released 2.1.0 plus the `parse_java_file()` workaround
3. Commit a relative path source to the sibling checkout (`../Ljavalang`)
4. Release the fork to PyPI under a distinct name and depend on that version
5. Vendor the parser into `mrf/`

## Decision
Chosen option: **1**. `pyproject.toml` declares

```toml
[tool.uv.sources]
ljavalang = { git = "https://github.com/pwizenty/Ljavalang.git", rev = "330d58b…" }
```

and `uv.lock` records the resolved commit, so `uv sync --locked` reproduces the
exact parser everywhere. HTTPS is used rather than SSH because the fork is
public, which keeps CI free of deploy keys.

The commit is pinned rather than the `dev` branch: a branch would silently
change the parser under a `uv.lock` refresh, which is precisely the failure
that produced this ADR.

Option 3 is rejected for the committed configuration because a relative path
breaks for anyone without the sibling checkout, but it stays the local
development loop: `uv add --editable ../Ljavalang` while changing both
repositories, reverted before committing. Option 4 remains the exit path if the
fork stabilises; option 5 was rejected because vendoring hides the provenance
that reproducibility depends on.

The `parse_java_file()` workaround is removed in the same change. Its tests are
kept and repurposed as contract tests against the pinned parser
(`tests/test_class_annotations.py`), so moving the pin to a revision that
regresses fails the suite.

TODO(author): should the fork be released to PyPI before the results are
published, so the artefact is citable without a GitHub reference?

## Consequences
- Positive: reconstruction works against the parser itself; MRF carries no
  workaround, and the token-scan duplicate of Java syntax is gone.
- Positive: the lock file now names the exact parser revision behind a result.
- Negative: MRF depends on a Git revision rather than a released artefact.
  Installing needs network access to GitHub, and the dependency cannot be
  resolved from a PyPI mirror alone.
- Negative: the fork must stay reachable for results to be reproducible.
  Publishing should not rely on a single GitHub account remaining available.
- Follow-up: raise the fix upstream, or release the fork, and return to a
  version constraint (ADR-0003 follow-up).
- Follow-up: the pin must be bumped deliberately; `uv lock --upgrade` will not
  move it.

## Pros and cons of the options
### 1. Git source pinned by commit
- Good, because it reaches the fix and names it exactly.
- Good, because CI and co-authors need no extra setup for a public repository.
- Bad, because installation needs GitHub rather than only a package index.

### 2. Keep status quo
- Good, because the dependency stays a released artefact.
- Bad, because MRF keeps a workaround for a defect already fixed upstream of it,
  and a second, simplified reader of Java syntax next to the parser.

### 3. Committed path source
- Good, because the edit loop is immediate.
- Bad, because it breaks every checkout without a sibling directory, and records
  no revision at all.
