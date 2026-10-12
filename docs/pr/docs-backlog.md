## Summary

A backlog of what is identified but not done, across both repositories of the
toolchain, plus a pointer to it from `CLAUDE.md`.

```text
docs/backlog.md
├── Done, for context          # so the list reads as the remainder
├── A. Security smell          # the 8 remaining facts, by what they cost
├── B. Node plugin 3 and 4     # with the two decisions they wait on
├── C. Operation diagrams      # the third diagram family, unplanned
├── D. Diagram follow-ups      # declined deliberately, not forgotten
└── E. Debt and housekeeping
```

Items are ordered by cost rather than by the task document's order, and carry
two markers: **decision** for what needs an answer before it can start,
**blocked** for what cannot be tested against any system available here.

## Evidence

The ordering is the point of the document, so the three judgements in it are
stated rather than left implicit:

```text
A1  server port/protocol/tlsEnabled/clientAuth     the obvious next step
    needs nothing new - Data holds one flat entry per port - and completes
    the client/server pair of which only the client half exists

A7  several evidence records per fact               forces a decision
    Data.values is flat, so a fact can carry one piece of evidence; this is
    where a fourth collection and an ADR become necessary

A8  gRPC usePlaintext(), messaging detectors        blocked
    absent from every sample system available here, so untestable
```

Nothing in the list is new information: it is drawn from
`s2s-communication-plugin-plan.md` §6, `node-plugin-plan.md` §8–9,
`../lemma/docs/service-diagram-plan.md` §7, `CLAUDE.md`'s known issues, and the
follow-ups noticed while building the two diagram bundles. The value is that it
is in one place and ordered.

Both diagram bundles are recorded as verified in Eclipse, which closes the one
thing their own checks could not cover.

## Merge Danger

**Door:** two-way. Two files, one of them new, no code.

**Blast Radius:** documentation

`CLAUDE.md` gains a *Planned work* section pointing at the backlog, so the list
is found from the file that is read first rather than only by someone who goes
looking in `docs/`. The backlog describes LEMMA work as well as MRF work and
lives only here, because most of the remaining work is MRF-side and this is
where the plans and ADRs already are — a reader of the LEMMA repository alone
will not find it.

It carries a *Last reviewed* date, which is a thing that can go stale. It says
so by carrying the date rather than by pretending otherwise.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
