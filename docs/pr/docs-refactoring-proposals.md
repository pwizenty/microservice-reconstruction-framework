## Summary

The research record of the resolution work: three AI-authored proposals, their
verification, and the write-up. **No code — MRF's reconstruction is untouched.**

```text
refactorings/
├── 2026-10-13-rc1-customercore/           9 → 6   PARTIAL
├── 2026-10-13-rc2-activemq-broker/        —       NOT VERIFIED
└── 2026-10-14-rc2-on-rc1-activemq-broker/ 9 → 0   VERIFIED
      request.md  constraints.md  skill.md  patch.diff
      notes.md    model.txt       result.json  verification.md
docs/paper-notes.md                        the write-up
docs/backlog.md                            E5 struck
```

ADR-0010 admits a language model only on the condition that its output is
**measured rather than trusted**, so the record of each proposal is the basis
on which the method is allowed at all. Each folder carries the prompt, the
constraints, a **verbatim copy of the skill that produced it**, the patch, the
model and cost, both repositories' commit SHAs, and the verdict. The skill is
copied rather than referenced so a record can be read without checking out two
repositories at the right revisions.

## Evidence

**The headline: findings fall from 9 to 0**, re-reconstructed from the patched
sources and re-detected — and the intermediate number is the predicted one, not
merely movement:

| | rc1 | rc2 | rc2-on-rc1 |
|---|---|---|---|
| Turns / cost | 144 / $10.62 | 100 / $6.55 | 135+28 / $29.04 |
| `clean` | PASS | **FAIL** | PASS |
| `inplace` | PASS | PASS | PASS |
| `smell` | **9 → 6** | — | **9 → 0** |
| `starts` | SKIP | — | **PASS** |
| Verdict | PARTIAL | NOT VERIFIED | **VERIFIED** |

rc1 resolves the three synchronous findings and leaves rc2's six, which is
exactly 9 → 6. rc2 and rc1 were produced independently against the same commit
and **do not compose** — five overlapping files, two CAs — so rc2-on-rc1 was
produced against a tree where rc1 was already applied, and the overlaps
vanished.

`compose up --wait` proves health checks passed, not that the TLS path is
exercised, so the record carries direct probes: plaintext gets Tomcat's 400,
`https` with a client certificate completes the handshake, **`https` without one
is refused** — the thing that distinguishes mutual TLS from TLS — and the
broker logs both connectors with `needClientAuth=true` and no plaintext
connector.

**Four things are recorded as findings rather than omitted:**

- **The validator produced a confident wrong attribution.** It blamed rc1 for a
  system that does not start unpatched either, because `openjdk:21-slim-buster`
  has been withdrawn from Docker Hub. Framed as an instance of a general hazard,
  with the mitigation that every gate needs a control.
- **`PatchGuard` rejected a correct patch for being honest**, reading
  `rejectUnauthorized: false` out of the proposal's own prose. A second instance
  of the same hazard.
- **Two tests in this work could not fail** — one comparing `0 == 0`, one
  crashing instead of failing and hiding every later check.
- **rc2-on-rc1 ran without the skill** and took two sessions, the first
  truncated by a usage limit. So it is **not evidence about the skill**, and a
  proposal is not an atomic operation.

`uv run pytest -q`: 150 passed. `ruff` and `mypy` clean.

## Merge Danger

**Door:** two-way. Documentation and records only; nothing executes.

**Blast Radius:** none at runtime

No module, plugin, repository, test or fixture is touched. The only risk is the
record being wrong, which is why every figure names what produced it.

Two things to know:

- **`refactorings/` is new and will grow.** One folder per proposal, each a few
  hundred KB of text and diff. If that is the wrong home, moving it later is a
  rename.
- **`docs/paper-notes.md` carries `TODO(author)` markers** at the two places
  needing your judgement: the framing, and which limitations are future work
  versus threats to validity.

Merges cleanly with `docs/adr-smell-resolution`, which also edits
`docs/backlog.md` — verified by merging both in order on a scratch branch. That
branch should go **first**: this one's records cite ADR-0010 by number.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
