# Architecture Decision Records

Format: MADR-based, see `.claude/skills/write-adr/template.md`.
New ADRs start as *Proposed*; only the maintainer sets *Accepted*.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-plugin-discovery-via-entry-points.md) | Discover plugins via entry points | Proposed |
| [0003](0003-java-parsing-with-ljavalang.md) | Parse Java sources with ljavalang | Proposed |
| [0004](0004-mongodb-persistence.md) | Persist reconstruction results in MongoDB | Proposed |
| [0005](0005-toolchain-uv-pyproject.md) | Toolchain: uv, pyproject.toml, Python ≥ 3.12 | Proposed |
| [0006](0006-ljavalang-from-fork-pinned-by-commit.md) | Consume ljavalang from the pwizenty fork, pinned by commit | Proposed |
| [0007](0007-no-generated-api-documentation.md) | Keep hand-written records instead of generated API documentation | Proposed |
| [0008](0008-operation-phase-reconstructs-deployment.md) | Reconstruct deployment into operation nodes, in a third collection | Accepted |
| [0009](0009-security-plugin-reconstructs-communication-facts.md) | Reconstruct communication security as meta-data, in a plugin of its own | Proposed |
