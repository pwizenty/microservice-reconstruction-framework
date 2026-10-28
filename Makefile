# Build and check targets for MRF.
#
# The same commands CI runs, so a green pipeline and a green working copy mean
# the same thing. Dependencies come from pyproject.toml + uv.lock (ADR-0005);
# there is no requirements.txt or Pipfile, and no Sphinx: ADR-0005 removed the
# generated documentation, so the Sphinx scaffolding that used to live here
# went with it.

UV = uv
SRC_DIR = mrf
TEST_DIR = tests

.PHONY: help init install check lint format types test integration run clean

help:
	@echo "init         install dependencies from uv.lock"
	@echo "check        lint, format, types and tests - what CI runs"
	@echo "lint         ruff check"
	@echo "format       ruff format --check"
	@echo "types        mypy"
	@echo "test         pytest"
	@echo "integration  pytest -m integration (needs Docker)"
	@echo "run          reconstruct a system: make run ARGS='-p Java Spring -t <path>'"

init:
	$(UV) sync --locked --all-groups

install: init

# What "done" means, per CLAUDE.md: ruff, mypy and pytest must pass.
check: lint format types test

lint:
	$(UV) run ruff check

format:
	$(UV) run ruff format --check

types:
	$(UV) run mypy

test:
	$(UV) run pytest -q

integration:
	$(UV) run pytest -m integration

# ARGS is required: mrf needs -p and -t, and without them main() raises
# rather than printing usage. Needs MongoDB, so it is not a CI target.
run:
	$(UV) run mrf $(ARGS)

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
