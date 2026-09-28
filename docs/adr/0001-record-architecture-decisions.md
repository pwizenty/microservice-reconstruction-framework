# ADR-0001: Record architecture decisions

- Status: Accepted
- Date: 2026-09-24
- Deciders: Philip Wizenty

## Context and problem statement
MRF is research software developed over several years, increasingly with an
AI coding agent (Claude Code). Design rationale currently lives only in commit
messages and the author's head. Both humans and the agent need a durable,
reviewable record of why the architecture looks the way it does, and a rule
for when deviating is allowed.

## Decision
We record significant decisions as ADRs in `docs/adr/` using a MADR-based
template. An ADR is required for changes to the plugin API, the architecture
model (`mrf/modules`), persistence, runtime dependencies and the toolchain.
Accepted ADRs are immutable; changes happen through superseding ADRs.
CLAUDE.md references the ADR index so the agent loads it in every session.

## Consequences
- Positive: rationale is versioned with the code; decisions can be cited in
  publications and the dissertation; the agent has explicit guard rails.
- Negative: small overhead per decision.
