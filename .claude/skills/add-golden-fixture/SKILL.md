---
name: add-golden-fixture
description: Use when changing reconstruction logic of any plugin, when a bug in reconstruction output is reported, or when adding a new sample system to the regression suite.
---

# Golden-fixture regression tests

## Layout
```
tests/fixtures/<system-name>/
  src/            # minimal source files (only what the test needs)
  expected.json   # expected reconstruction output (model serialised via dataclasses.asdict)
  README.md       # origin + licence of the sample, what it exercises
tests/test_golden.py
```

## Rules
- Samples must be minimal and licence-compatible; record origin and licence
  in the fixture README (e.g. Lakeside Mutual excerpts – check the upstream licence).
- `expected.json` is written or reviewed by a human. When a change alters
  it, show the diff (`deepdiff`) and ask the user to confirm – never
  regenerate expected output just to make a test pass.
- Tests must not touch MongoDB: compare the in-memory model returned by the
  plugins/handler, not the database.
- Mark as `@pytest.mark.golden`.
- Paths in the output must be relative to the fixture root so results are
  machine-independent.

## Gotchas
- `ReconstructionHandler` is a singleton with class-level state – create a
  fresh handler per test (or reset `_instance`) until that is fixed.
- Order of lists depends on filesystem traversal order; sort before comparing
  or use `deepdiff(..., ignore_order=True)`.
