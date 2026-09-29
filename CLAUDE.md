# MRF – Microservice Reconstruction Framework

Reconstructs architecture information (microservices, interfaces, operations,
domain contexts, data structures) from source code via technology plugins and
persists the result in MongoDB. Research software (FH Dortmund) – results must
be reproducible.

## Commands
- Setup:        `uv sync --all-groups`
- Run:          `uv run mrf -p Java Spring -t <path-to-system>` (needs MongoDB, see `mrf/config.yaml`)
- Unit tests:   `uv run pytest -q`
- Integration:  `uv run pytest -m integration` (Docker/testcontainers)
- Lint+format:  `uv run ruff check --fix && uv run ruff format`
- Types:        `uv run mypy`

Before claiming a task is done: ruff, mypy and pytest must pass. Show the output.

## Architecture
- `mrf/main.py` – CLI entry point (`mrf` script)
- `mrf/utilities/command_line.py` – argument parsing, file loading, `SourceFile`
- `mrf/modules/` – technology-independent architecture model
  (`service.py`: Microservice/Interface/Operation; `domain_data.py`: Context/DataStructure/…)
- `mrf/modules/reconstruction_handler.py` – orchestrates phases: domain data → services → (operation, planned)
- `mrf/plugins/` – technology plugins implementing `Plugin` ABC (`reconstruction_plugin.py`)
  - `data/java/` – domain data from JPA entities; `service/spring/` – services/REST interfaces
  - `common/common_plugin.py` – shared `Data` (meta-data) and `JavaClassArtifact`
- `mrf/utilities/java_utils.py`, `mrf/utilities/sping.py` – Java/Spring parsing helpers & constants
- `mrf/repositories/` – mapping model → `R*` persistence classes → MongoDB

Dependency direction: plugins → modules/utilities; repositories → modules.
`modules/` must never import from plugins or repositories.

## Architecture decisions
Index: @docs/adr/README.md
- Do not contradict an **Accepted** ADR. If a change requires it, stop and
  draft a superseding ADR (skill: `write-adr`) instead of silently deviating.
- Changes to dependencies, persistence, plugin API or the model need an ADR.

## Conventions
- Python ≥ 3.12, full type hints, Google-style docstrings
- Absolute imports only: `from mrf.utilities…` – never `from utilities…`
- `logging` instead of `print` (new code); log via `logging.getLogger(__name__)`
- No mutable class-level defaults; use `dataclasses.field(default_factory=list)`
- Model classes in `mrf/modules` stay technology-agnostic (no javalang types)
- Commit messages: `<Area>: <imperative summary>` – areas used so far:
  `General`, `Spring Plugin`, `Java Plugin`, `Microservice`, `Docs`
- Branching: feature branches from `dev`, PRs into `dev`; never commit to `main`
- Every change to a plugin's reconstruction logic needs a golden-fixture test
  (skill: `add-golden-fixture`)

## Known issues (fix when touching the area, don't copy the pattern)
- `java_plugin.py` / `spring_plugin.py` import `from utilities.java_utils …`
  → breaks when installed (`ModuleNotFoundError`); must be `mrf.utilities`
- `main()` doesn't exit when `-p`/`-t` are missing → `TypeError` in `args_to_plugins`
- `ReconstructionHandler` is a singleton with class-level mutable lists
  → state leaks between runs/tests
- `RData.values = {}` is a shared class attribute; `SourceFile` is a `@dataclass`
  with a hand-written `__init__`
- `mongo_repository.__setup_database` opens `mrf/config.yaml` relative to CWD
- Saving uses `insert_one` → re-running duplicates documents
- `SpringPlugin.__reconstruct_interface` uses `next()` without default
  → `StopIteration` if a controller matches no service
- `utilities/sping.py` is a typo of `spring.py` (rename in a dedicated commit)

## Gotchas
- Parser is **ljavalang** (fork, Java 9–22 incl. records), not `javalang`.
  The import name is still `javalang`.
- Qualified-name heuristics (`adjust_qualified_name`, `HIERARCHY_LEVEL`) were
  tuned on Lakeside Mutual – check golden fixtures of other systems before changing.
- Spring infrastructure services (Eureka, Zuul) are deliberately skipped
  (`INFRASTRUCTURE_TECHNOLOGIES`).
