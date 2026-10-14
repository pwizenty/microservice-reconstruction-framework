## Summary

Records the decision that lets an AI into this toolchain, and accepts every
remaining ADR.

```text
docs/adr/
├── 0010-resolve-smells-with-an-ai-authored-patch.md   NEW, Accepted
└── 0002 … 0007                                        Proposed → Accepted
```

ADR-0009 named refactoring as the pipeline's fourth step, and detection now
exists, so **what "resolve" means had to be decided before building it.** The
obvious reading — a quickfix that edits the model until the warning clears — is
rejected, on two grounds that are measured rather than argued:

```diff
  a quickfix that rewrites a reconstructed fact
- the warning disappears
- the vulnerability remains
- a true finding becomes a false negative inside our own reconstruction
```

and `ReconstructionModelWriter` uses plain `Files.write` —
`TRUNCATE_EXISTING`, no merge, no protected region — so the edit is silently
destroyed on the next run anyway. The Service DSL has no concept of transport
security to express the fix with either: `spring.technology` declares `rest`,
`soap` and `amqp`, none of which distinguishes TLS.

So resolution acts on the **sources**, the model stays descriptive, and a
proposal counts only when the toolchain measures it.

## Evidence

Five options are weighed, including "keep status quo", and the rejected ones
say why. The decision has four parts and the fourth is what makes the first
three admissible: **a proposal counts only when verified.**

Accepting the other six ADRs created real inconsistencies, which are fixed in
the same change rather than left to be discovered:

- **ADR-0002's own Decision section opened `Proposed: option 1.`**, contradicting
  its new header. The chosen option is untouched.
- **The plugin registration checklist branched on whether ADR-0002 was accepted.**
  It is — but entry-point discovery is *not implemented*, so a new plugin still
  has to be hand-wired. The checklist now says that instead of asking.
- **Backlog E2 said "Seven ADRs are still *Proposed*"**, already wrong by one, and
  gave the hand-wiring a pending question as its rationale. It is now a work
  item: the three-place wiring is a deviation from an Accepted ADR.
- **The same checklist asked for a Sphinx page** under `docs/source/`, which
  ADR-0005 removed — the directory and the dependencies are both gone, so it
  was sending a future author to write a file that cannot exist.

`ruff`, `mypy` and `pytest` unaffected: 150 passed. No module, test or fixture
is touched.

## Merge Danger

**Door:** two-way for the files. **One-way for the standing constraint.**

`CLAUDE.md` says not to contradict an Accepted ADR, so after this merge three
things stop being advisory: no quickfix may edit a reconstructed fact to clear
a finding; resolution is application-level only until backlog A4; and a
refactoring is not "resolved" without its before/after counts, a green build
and a running system. Changing any of them later needs a **superseding ADR**,
not an edit.

**Blast Radius:** the plugin registration becomes a known deviation

Accepting ADR-0002 means the current three-place wiring —`PluginType`, the CLI
`choices`, the handler's phase branch — now *contradicts* an Accepted ADR. **No
code is changed here**; that refactor was not in scope and is reframed as
backlog E2 instead. Nothing breaks, but the inconsistency is now on the record
rather than pending.

ADR-0009 and two plugin plan documents also mention ADR-0002 being Proposed and
are deliberately left alone: they record what was true when written, and
ADR-0009 is itself Accepted.

Merges cleanly with `docs/refactoring-proposals`, which also edits
`docs/backlog.md` — verified by merging both in order on a scratch branch.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
