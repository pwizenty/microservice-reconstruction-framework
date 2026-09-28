# ADR-0002: Discover plugins via entry points

- Status: Proposed
- Date: 2026-09-24
- Deciders: Philip Wizenty

## Context and problem statement
Adding a plugin currently requires changes in three core places:
the `PluginType` enum (`mrf/plugins/reconstruction_plugin.py`), the hardcoded
CLI `choices` (`mrf/utilities/command_line.py`) and explicit `if PluginType.X
in self.plugins` branches in `ReconstructionHandler`. The enum already lists
`DOCKER`, which has no implementation. The core therefore knows every
technology, contradicting the goal of a technology-independent framework, and
third parties cannot add plugins without forking.

## Decision drivers
- Extensibility without modifying core (open/closed)
- Plugins declare their own phase (data, service, operation)
- Low complexity; no extra dependencies

## Considered options
1. Entry points (`importlib.metadata`, group `mrf.plugins`)
2. Decorator-based in-process registry
3. Keep status quo (enum + explicit wiring)

## Decision
Proposed: option 1. The `Plugin` ABC gains `name` and `phase` attributes; the
handler loads all entry points in group `mrf.plugins`, filters by the names
chosen on the CLI and runs them grouped by phase. CLI choices are derived from
the discovered plugins.

TODO(author): Should cross-plugin steps (e.g. `SpringPlugin` results feeding
`JavaPlugin.reconstruct_dependencies`) become an explicit phase contract, or
may plugins declare dependencies on other plugins?

## Consequences
- Positive: new plugins (incl. external packages) need no core change;
  `PluginType` and the handler's `if` chains disappear.
- Negative: plugin interaction must be made explicit; entry points only
  update after `uv sync`.
- Follow-up: extend the ABC, migrate Java and Spring plugins, update the
  `new-reconstruction-plugin` skill checklist.
