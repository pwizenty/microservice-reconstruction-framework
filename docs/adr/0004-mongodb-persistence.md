# ADR-0004: Persist reconstruction results in MongoDB

- Status: Proposed (documents the current state, with open questions)
- Date: 2026-09-24
- Deciders: Philip Wizenty

## Context and problem statement
Reconstructed model elements are mapped to persistence classes (`R*` in
`mrf/repositories/`) and inserted into MongoDB collections `context` and
`microservice` (`mongo_repository.py`). Connection settings come from
`mrf/config.yaml`, opened relative to the current working directory.
Every run uses `insert_one`, so repeated runs duplicate documents and runs
cannot be distinguished.

## Decision drivers
- Downstream consumers of the results (TODO(author): which tools/analyses?)
- Reproducibility and comparison of runs
- Testability without a running database
- Deployment simplicity for other researchers

## Considered options
1. MongoDB with a repository abstraction, run IDs and upserts
2. File-based export (JSON per run) as primary output, MongoDB optional
3. Keep status quo

## Decision
Proposed: option 1 plus a JSON export. Introduce a `Repository` protocol
(in-memory + Mongo implementations), tag every document with a run ID
(timestamp, commit hash, analysed system, plugin versions) and use upserts.
Configuration via CLI flag / environment variable (`MRF_MONGO_URI`) with the
YAML file as fallback, resolved relative to the package, not CWD.

## Consequences
- Positive: idempotent runs, traceable results, tests without MongoDB.
- Negative: small refactoring of `mongo_repository.py` and the handler.
