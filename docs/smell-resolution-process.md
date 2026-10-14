# The process, as a diagram

`smell-resolution-process.drawio` — open with <https://app.diagrams.net> or the
VS Code Draw.io extension. Uncompressed XML, so it diffs and can be edited by
hand.

Four lanes, and the lanes are the argument:

| Lane | |
|---|---|
| 1 Reconstruction | deterministic, reproducible — MRF, Python |
| 2 Detection | deterministic, reproducible — LEMMA, Xtend |
| 3 Proposal | **an LLM, not reproducible**, strictly downstream of detection |
| 4 Verification | deterministic — what makes a proposal admissible |

The LLM is sandwiched. Everything above it is reproducible, everything below it
measures what it produced, and nothing it writes is applied. That arrangement is
the whole of ADR-0010; the diagram exists mainly to make it visible at a glance.

Three details in the diagram that are easy to lose in prose:

- **The dashed green edge from the `smell` gate back up to the MRF plugins.** The
  gate does not inspect the patch; it re-runs the entire reconstruction over the
  patched sources and re-detects. That loop is why "9 → 0" is a measurement
  rather than a claim.
- **The three instruction layers feeding the CLI**, of which only the first is
  enforced. A skill is instruction and can be ignored, so nothing load-bearing
  rests on it.
- **`fix/container-base-images` entering the `starts` gate from the side**, marked
  as a prerequisite rather than part of the refactoring. Until the sample's
  withdrawn base image was replaced, that gate could only skip — so the
  strongest claim the method can make depended on repairing the subject system's
  build, which is not part of the contribution.
