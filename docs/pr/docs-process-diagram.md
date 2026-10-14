## Summary

The process as executed, drawn. Two pages in one `.drawio` file — a figure for
the write-up, and a reference behind it.

```text
docs/
├── smell-resolution-process.drawio
│   ├── page 1  "Process"                 22 boxes   ← use this one
│   └── page 2  "Detail (full pipeline)"  45 boxes
└── smell-resolution-process.md           what each page argues
```

Page 1 is three phases and a loop:

```text
RECONSTRUCTION  ──►  REFACTORING  ──►  VERIFICATION
 deterministic        an LLM, NOT        deterministic
 reproducible         reproducible
      ▲                                       │
      └───────────────────────────────────────┘
        gate ③ re-runs the WHOLE reconstruction
        over the patched sources
```

**The loop is the point.** The third gate does not inspect the patch — it
re-reconstructs the patched system and re-detects, which is why "9 → 0" is a
measurement rather than a claim. That is invisible in any linear drawing, and
it is the whole basis on which ADR-0010 admits a language model: the LLM sits
between two deterministic halves, with nothing it writes applied until a human
has read it.

Uncompressed XML, so it diffs in git and can be edited by hand.

## Evidence

Both pages parse, and every edge resolves to a real vertex:

```console
page 'Process':                22 vertices, 12 edges, dangling=none
page 'Detail (full pipeline)': 45 vertices, 32 edges, dangling=none
```

Each phase carries its epistemic status underneath it — *deterministic ·
reproducible* against *an LLM · not reproducible* — because that is the
distinction a reader most needs and the first one lost when a diagram is
tidied. The patch box says **APPLIED NOWHERE** in capitals for the same reason.

Four things are on the figure that a cleaner drawing would have dropped, and
each is there deliberately:

- the feedback loop, described above
- that only the **first** of the three instruction layers is enforced — a skill
  is instruction and can be ignored
- `fix/container-base-images` entering the fourth gate from the side as a
  **prerequisite**, not part of the refactoring: the strongest claim the method
  made depended on repairing the subject system's build, which is not the
  contribution
- on page 2: `is_error` deciding rather than `subtype`, a proposal not being
  atomic, every gate needing a control, and a **skipped gate not being a passed
  one**

`uv run pytest -q`: 151 passed; `ruff` and `mypy` clean. No code is touched.

## Merge Danger

**Door:** two-way. Two documentation files; nothing executes.

**Blast Radius:** none

No module, plugin, test or fixture changes. The only risk is the diagram
drifting from the implementation — which it will, as diagrams do. It is dated
by what it describes rather than maintained as a live artefact, and the
companion `.md` says which page to use for what.

One note for a reader: page 2 names tools that live in the LEMMA repository,
so the two pages span both halves of the toolchain. The paths are given in
`docs/paper-notes.md` §8 rather than repeated on the figure.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
