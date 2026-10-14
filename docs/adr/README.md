# Architecture Decision Records

Format: MADR-based, see `.claude/skills/write-adr/template.md`.
New ADRs start as *Proposed*; only the maintainer sets *Accepted*.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-plugin-discovery-via-entry-points.md) | Discover plugins via entry points | Accepted |
| [0003](0003-java-parsing-with-ljavalang.md) | Parse Java sources with ljavalang | Accepted |
| [0004](0004-mongodb-persistence.md) | Persist reconstruction results in MongoDB | Accepted |
| [0005](0005-toolchain-uv-pyproject.md) | Toolchain: uv, pyproject.toml, Python ≥ 3.12 | Accepted |
| [0006](0006-ljavalang-from-fork-pinned-by-commit.md) | Consume ljavalang from the pwizenty fork, pinned by commit | Accepted |
| [0007](0007-no-generated-api-documentation.md) | Keep hand-written records instead of generated API documentation | Accepted |
| [0008](0008-operation-phase-reconstructs-deployment.md) | Reconstruct deployment into operation nodes, in a third collection | Accepted |
| [0009](0009-security-plugin-reconstructs-communication-facts.md) | Reconstruct communication security as meta-data, in a plugin of its own | Accepted |
| [0010](0010-resolve-smells-with-an-ai-authored-patch.md) | Resolve security smells with an AI-authored patch, outside the reproducible path | Accepted |
