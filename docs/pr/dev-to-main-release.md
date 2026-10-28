## Summary

**`dev` into `main`, after nineteen months.** `main` last moved on
2025-03-12; `dev` carries 122 commits and 20 merges since, and nothing on
`main` is absent from `dev`, so this is a clean fast-forward rather than a
reconciliation.

```text
347 files changed, 35 314 insertions, 434 deletions
```

What `main` gains, in the order it was built:

| Merged | What it added |
|---|---|
| #2, #3 | **Operation models** — a third reconstruction phase, deployment into operation nodes (ADR-0008), and `ljavalang` re-pinned by commit (ADR-0006) |
| #4 | Reconstruction quality fixes found by comparing output against the sources |
| #5, #6, #7 | **The communication plugin** — the interaction surface of a service as meta-data (ADR-0009): outgoing calls and their transport, deployment configuration, and service dependencies as `required operations` with a fallback chain |
| #8, #9 | **gRPC and Node** — a hand-written proto3 parser, and Node facts without a JavaScript parser; plus the plans and ADRs behind them |
| #10 | A backlog of what is identified and not done, across both repositories |
| #11 | **Server-side facts** — the ports a service answers on, per connector: `port`, `protocol`, `tlsEnabled`, `clientAuth`, `valueSource` |
| #12, #13 | **Asynchronous links** — JMS/ActiveMQ producers and consumers, the queue and the broker's transport; and the ten security smells of Ponce et al. (2022) as reference |
| #14, #15, #16 | **ADR-0010** — resolving a smell with an AI-authored patch, outside the reproducible path; the recorded proposals; and the process drawn |
| #17, #18 | CI actually runs the checks it claims to, and a container's operation environment is read from what it *runs* on, not what it builds from |
| #19 | **A Node channel's transport, read from the sources by name**, and the record of the experiment it made possible |

The through-line: **MRF collects facts, LEMMA decides the smell** (ADR-0009).
Nothing here reports a severity or a field named `insecure`; the judgement lives
in the other repository, and this release is what gives it something to judge.

**Ten ADRs, all Accepted.** `docs/adr/README.md` is the index. Two of them bound
what any later change may do: ADR-0009 puts the smell decision in LEMMA, and
ADR-0010 admits an AI-authored patch only on the condition that what it produces
is measured rather than trusted.

## Evidence

Run at this tip:

```text
ruff          All checks passed!
ruff format   142 files already formatted
mypy          Success: no issues found in 58 source files
pytest        168 passed in 0.46s
```

`168` against `main`'s suite is the measure of the release: every plugin's
reconstruction logic is covered by a golden fixture whose expected output was
written or reviewed by hand, never regenerated to make a test pass.

The reconstruction was also run end to end against a live MongoDB and the
generated models fed to LEMMA, which is where the numbers in `docs/` come from —
eleven findings over four root causes on Lakeside Mutual, and the fourteen
channels of that system enumerated by hand from the sources, without consulting
the reconstruction, to say which ten the models carry.

### What this release does not claim

- **Neither sample system configures TLS at all.** Eleven services across
  Lakeside Mutual and park-and-charge, every one a plaintext main connector and
  no management port, so every TLS-positive path is reachable only through a
  fixture.
- **`refactorings/` is excluded from ruff and the formatter.** Those files are
  recorded verbatim, including a patch's own whitespace; formatting them would
  misreport the run.
- **The known issues in `CLAUDE.md` are still open** — the two
  `from utilities…` imports, the `ReconstructionHandler` singleton's class-level
  state, `insert_one` duplicating documents on a re-run. They are listed to be
  fixed when the area is touched, not as a campaign, and they are on `main` now
  too.
- **Plugin registration is still hand-wired**, against Accepted ADR-0002.
  Backlog E2.

## Merge Danger

**Door:** one-way in the sense that matters — this is the branch other people
and other checkouts take as the published state, and `main` has been still for
nineteen months. Reverting is a revert commit, not an undo of what people
already pulled.

**Blast Radius:** everything downstream of `main`

- **The CLI gained a third phase and four plugin families.** A caller passing
  only `-p Java Spring` behaves as before; `operation/docker` additionally needs
  the **system root** as `-t`, not a service directory.
- **`mrf/config.yaml` is read relative to the working directory**, so a run
  started elsewhere finds no database configuration. Pre-existing, and listed
  under known issues.
- **Saving uses `insert_one`**, so re-running a reconstruction duplicates
  documents rather than replacing them. Anyone automating repeated runs against
  one database needs to know this before upgrading.
- **`uv`, `pyproject.toml` and Python ≥ 3.12** are the toolchain (ADR-0005).
  `main`'s previous setup is replaced, not kept beside it.
- Dependencies now include the `ljavalang` fork, pinned by commit from the
  `pwizenty` repository rather than PyPI (ADR-0006). Whether to release it to
  PyPI before the results are published is an open `TODO(author)` in that ADR.

Worth stating rather than implying: **CI runs lint, format, types and tests**
since #18, and that is the whole of it — there is no integration run on CI, so
the `pytest -m integration` suite that needs Docker and testcontainers has only
ever been run locally.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
