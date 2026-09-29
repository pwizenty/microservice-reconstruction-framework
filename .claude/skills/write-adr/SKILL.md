---
name: write-adr
description: Use when a change alters MRF's architecture, plugin API, architecture model, persistence, dependencies or toolchain, when a change would contradict an accepted ADR, or when the user asks to document a decision.
---

# Write an Architecture Decision Record

## Rules
- Location: `docs/adr/NNNN-kebab-case-title.md`, next free 4-digit number.
- Format: `template.md` in this folder (MADR-based). Keep it to 1–2 pages.
- New ADRs start as **Proposed**. Only the user sets **Accepted**.
- Never edit the decision of an Accepted ADR. Supersede it: new ADR with
  `Supersedes: ADR-XXXX`, and set the old one to `Superseded by ADR-YYYY`.
- List at least two real options, including "keep status quo".
- Ground the context in the code: cite modules/classes, not generalities.
- Mark anything that needs the author's judgement (research rationale,
  publication constraints) as `TODO(author): …` rather than inventing it.
- Update the table in `docs/adr/README.md` in the same change.
- Commit: `Docs: Add ADR-NNNN <title>`.

## Gotchas
- Decision drivers for MRF are often research-driven (reproducibility,
  comparability with published results, analysed systems). Ask if unclear.
