# Tests

Unit tests run without any external service:

    uv run pytest -q

Integration tests need Docker/MongoDB via testcontainers and are excluded by
default (see `addopts` in `pyproject.toml`):

    uv run pytest -m integration

Golden-fixture tests compare a plugin's reconstruction output against
`tests/fixtures/<system>/expected.json` and carry the `golden` marker. They
need a checked-in sample system; see the `add-golden-fixture` skill. None exist
yet - every change to a plugin's reconstruction logic should add one.
