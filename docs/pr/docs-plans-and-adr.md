## Summary

Two documents about work that is already merged.

```diff
 docs/adr/0009-security-plugin-reconstructs-communication-facts.md
-- Status: Proposed
+- Status: Accepted

 docs/service-dependencies-plan.md
-Status: **proposed, awaiting review**
+Status: **implemented**, MRF PR #7 and LEMMA PR #5, merged 2026-10-01.
```

**ADR-0009 is accepted** on your word: the decision it records is in use, and the
service models of Lakeside Mutual carry the facts it describes.

**The dependency plan is kept rather than dropped.** It was written before the
work and said it awaited review; the work is merged. What it holds is worth
keeping — what was read from the Service DSL before anything was written (that
the three `required` levels are alternatives rather than layers, that a `noimpl`
operation cannot be required at all, how an operation is named across models),
and what the implementation deliberately does not reach.

## Evidence

Documents only; no code. The claims each one makes were verified when the
corresponding work was done — MRF PR #7 and LEMMA PR #5, both merged.

## Merge Danger

**Door:** two-way. Two files, one of them a status line.

**Blast Radius:** none

Accepting an ADR changes what `CLAUDE.md` forbids contradicting: a later change
that needs to deviate from ADR-0009 now has to supersede it rather than simply
differ.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
