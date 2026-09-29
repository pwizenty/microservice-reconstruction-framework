---
name: new-reconstruction-plugin
description: Use when adding support for a new technology or framework to MRF (e.g. Docker, Kubernetes, Quarkus, Micronaut, messaging via Kafka/RabbitMQ) or when splitting an existing plugin. Not for bug fixes inside an existing plugin.
---

# New reconstruction plugin

## Goal
A plugin that implements `mrf.plugins.reconstruction_plugin.Plugin`, maps
technology-specific artifacts onto the technology-agnostic model in
`mrf/modules/`, is selectable from the CLI, and is covered by at least one
golden-fixture test.

## Constraints
- The model in `mrf/modules/` is the contract. If the technology needs a
  concept the model lacks, stop and draft an ADR (skill `write-adr`) before
  extending the model.
- Put technology constants (annotation names, file names) in a dedicated
  `mrf/utilities/<technology>.py`, like `sping.py` does for Spring.
- Pick the phase: domain data → `plugins/data/`, services/interfaces →
  `plugins/service/`, deployment/operation → `plugins/operation/`.
- Plugins must be stateless across runs: initialise all lists in `__init__`.
- Use `logging`, not `print`.

## Steps
1. Read `mrf/plugins/reconstruction_plugin.py` and the closest existing plugin
   (`plugins/service/spring/spring_plugin.py` for services,
   `plugins/data/java/java_plugin.py` for data).
2. Scaffold from `templates/plugin.py`.
3. Register the plugin: follow `references/checklist.md` – registration
   differs depending on whether ADR-0002 (entry points) is accepted.
4. Create a minimal sample system under `tests/fixtures/<technology>-minimal/`
   and a golden test (skill `add-golden-fixture`). Write the expected output
   by hand from the sample – do not generate it from the new plugin.
5. Run `uv run pytest -q && uv run mypy && uv run ruff check`.
6. Add the plugin to the docs (`docs/source/`) and to the plugin list in CLAUDE.md.

## Gotchas
- `SourceFile.file` is `None` when a file couldn't be decoded – guard against it.
- The CLI `choices` in `command_line.py` are hardcoded and must match the
  `PluginType` values exactly (case-sensitive: "Spring", not "spring").
- `ReconstructionHandler` only runs plugins it explicitly checks for; a
  registered but unwired plugin is silently ignored.
