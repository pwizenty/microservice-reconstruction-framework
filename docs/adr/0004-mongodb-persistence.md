# ADR-0004: Persist reconstruction results in MongoDB

- Status: Proposed (documents the current state, with open questions)
- Amended: 2026-09-29, upserts implemented (see *Amendments*)
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

## Amendments
### 2026-09-29: upserts are in place, the run ID is not
The decision above asked for upserts and for a run ID on every document. The
first half is implemented, the second is not, so this records what is true
rather than leaving the whole decision looking unimplemented.

`mongo_repository.__save` identifies a document by its `qualified_name` and
replaces it, so running the reconstruction again updates what it found before.
Until now every run used `insert_one`. The cost of that was not theoretical:
two runs of Lakeside Mutual left two `CustomerCore` contexts, one of them from
an earlier and narrower run, the LEMMA wizard offered both under the same name,
and the models generated from the stale one silently lost five data structures
and the type of a field.

A document of an earlier run that the current one did not produce is kept,
which is what lets several analysed systems share a database - the wizard
lists them together. `mrf --replace` drops the documents of a collection
first, for the case where a run is meant to be the entire content of the
database.

Two things this does not solve, both of which the run ID would:

- A narrower run leaves the elements of a broader one behind. Reconstructing
  the whole system and then a single service leaves the other services in the
  database, indistinguishable from what the current run found.
- Runs still cannot be told apart or compared, which is what the decision
  drivers above ask for.

The third collection `operation` is saved the same way, see ADR-0008. Note
that an operation node has no namespace of its own: its qualified name is its
name, so two systems with a container of the same name overwrite each other.
Contexts and microservices carry a package and do not have that problem.
