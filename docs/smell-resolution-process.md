# The process, as a diagram

`smell-resolution-process.drawio` — open with <https://app.diagrams.net> or the
VS Code Draw.io extension. Uncompressed XML, so it diffs and can be edited by
hand.

**Two pages.** Use the first one in the write-up; the second is reference.

| Page | | |
|---|---|---|
| **Process** | 22 boxes | three phases: reconstruct, refactor, verify |
| **Detail (full pipeline)** | 45 boxes | every tool, artefact and gate, in four lanes |

## What the first page is arguing

Three phases, left to right, and a loop:

```text
RECONSTRUCTION  ──►  REFACTORING  ──►  VERIFICATION
 deterministic        an LLM, not        deterministic
 reproducible         reproducible
      ▲                                       │
      └───────────────────────────────────────┘
        gate ③ re-runs the WHOLE reconstruction
        over the patched sources
```

The loop is the point. **The third gate does not inspect the patch** — it
re-reconstructs the patched system and re-detects, so "9 → 0" is a measurement
rather than a claim. And the LLM sits between two deterministic halves with
nothing it writes applied until a human has read it, which is the whole of
ADR-0010.

Each phase carries its epistemic status underneath it, because that is the
distinction a reader most needs and the one most easily lost: *deterministic ·
reproducible* for the outer two, *an LLM · not reproducible* for the middle.

One footnote is kept on the figure rather than dropped: the sample's container
images had to be repaired before the fourth gate could run at all. That is a
prerequisite, not part of the refactoring, and it means the strongest claim the
method made depended on fixing the subject system's build.

## What the second page adds

Every tool by name, the three instruction layers (and which of them is
*enforced* — only the first, since a skill can be ignored), `PatchGuard`,
the proposal record, the controls each gate needs, and the operational facts
worth not rediscovering: `is_error` deciding rather than `subtype`, a proposal
not being atomic, and a skipped gate not being a passed one.
