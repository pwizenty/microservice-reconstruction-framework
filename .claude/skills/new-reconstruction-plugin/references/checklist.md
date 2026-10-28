# Plugin registration checklist

## How it works today (hand-wired)
ADR-0002 is **Accepted**, but entry-point discovery is not implemented yet,
so a new plugin still has to be wired in by hand. Removing this duplication
is backlog item E2.

- [ ] Add a member to `PluginType` in `mrf/plugins/reconstruction_plugin.py`
- [ ] Add the value to `choices=[...]` in `mrf/utilities/command_line.py`
      (better: `choices=[p.value for p in PluginType]`)
- [ ] Wire the plugin into the matching phase method of
      `mrf/modules/reconstruction_handler.py`
- [ ] If the plugin produces new model types: add `R*` mapping classes in
      `mrf/repositories/` and a save function in `mongo_repository.py`

## The decided mechanism (ADR-0002, entry points)
What replaces the above once E2 is done:
- [ ] Add `[project.entry-points."mrf.plugins"] <name> = "<module>:<Class>"` in `pyproject.toml`
- [ ] Run `uv sync` so the entry point is registered
- [ ] No core file needs to change

## Always
- [ ] Golden fixture + test in `tests/fixtures/<name>-minimal/`
- [ ] Unit tests for non-trivial helpers
- [ ] Docstrings (Google style) on the class and public methods
- [ ] Commit: `<Technology> Plugin: Add initial reconstruction`
