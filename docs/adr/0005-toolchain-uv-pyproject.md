# ADR-0005: Toolchain – uv, pyproject.toml, Python ≥ 3.12

- Status: Proposed
- Date: 2026-09-24
- Deciders: Philip Wizenty

## Context and problem statement
The project has three partially conflicting sources of metadata:
`setup.py` (packages `mrf`'s sub-packages as top-level packages and passes an
invalid `license_mrf` argument), `requirements.txt` (lists stdlib modules and
the unused `pandas`) and a `Pipfile` pinned to Python 3.10 (end of life
October 2026) that lists `javalang` instead of `ljavalang`. There is no linter,
type checker or test runner configured; CI runs `make run` without arguments.

## Decision drivers
- Single source of truth for dependencies
- Reproducible environments (lock file) for research results
- Fast feedback for humans and the coding agent
- Supported Python version

## Considered options
1. `pyproject.toml` (PEP 621, hatchling) + uv + uv.lock; ruff, mypy, pytest
2. `pyproject.toml` + Poetry
3. Keep setup.py + Pipenv

## Decision
Proposed: option 1. Remove `setup.py`, `requirements.txt`, `Pipfile(.lock)`.
Provide a `mrf` console script. CI: `uv sync --locked` → ruff → mypy →
pytest (unit) → pytest -m integration (MongoDB service) → Sphinx docs.
Enable `sphinx.ext.napoleon` (built into Sphinx) instead of the deprecated
`sphinxcontrib-napoleon` package, and `myst-parser` so ADRs render in the docs.

## Consequences
- Positive: one config file, locked environments, fast checks usable in
  Claude Code hooks, installable package with working imports.
- Negative: contributors need uv; existing ruff findings (~300, about half
  auto-fixable) must be cleaned up in a dedicated commit.
