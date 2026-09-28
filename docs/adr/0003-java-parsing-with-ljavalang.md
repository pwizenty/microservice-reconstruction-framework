# ADR-0003: Parse Java sources with ljavalang

- Status: Proposed (documents the current state)
- Date: 2026-09-24
- Updated: 2026-09-28 (class-annotation defect in ljavalang 2.1.0)
- Deciders: Philip Wizenty

## Context and problem statement
The Java and Spring plugins analyse Java ASTs (annotations, fields, method
signatures, imports) via `mrf/utilities/java_utils.py`. The code imports
`javalang` but uses `RecordDeclaration`, which only exists in **ljavalang**, a
fork of the unmaintained `javalang` with Java 9–22 support. `requirements.txt`
lists `ljavalang`, while the `Pipfile` lists `javalang`, which would fail at import.

### Class-annotation defect (found 2026-09-28)
The pinned **ljavalang 2.1.0** drops class-level annotations written in the
conventional position, before the modifiers:

| Source form | `ClassDeclaration.annotations` |
|---|---|
| `@Entity`<br>`public class C {}` (first top-level type) | `[]` |
| `public @Entity class C {}` | `[Annotation(name=Entity)]` |
| `@Entity` on the *second* top-level type | `[Annotation(name=Entity)]` |

Only the first top-level type of a compilation unit is affected. Fields,
methods, nested types and further top-level types are unaffected. Because a
Java file conventionally holds exactly one top-level type, this strips the
annotations of precisely the class both plugins key on.

Upstream `javalang` attaches both forms but cannot parse records
(`JavaSyntaxError`). Reproduced identically on Python 3.12, 3.13 and 3.14, so
this is a parser defect and not an environment effect.

This is not cosmetic. `has_annotation(clazz, …)` in `mrf/utilities/java_utils.py`
is how `JavaPlugin.__reconstruct_context` / `__reconstruct_entity` detect
`@SpringBootApplication` (`CONTEXT_ANNOTATION`) and `@Entity`, and how
`SpringPlugin.__reconstruct_microservice` / `__reconstruct_interface` detect
`@SpringBootApplication` and `@RestController`.
With ljavalang 2.1.0 these never match on normally formatted Java, so a run
reconstructs no microservices, contexts or entities at all.

`>=2.1` currently resolves to 2.1.0 as the only matching release, so relaxing
the constraint does not yield a fixed version.

TODO(author): were the published Lakeside Mutual results produced with upstream
`javalang` (the `Pipfile` listed it)? If so, reproducing them may require that
parser, which is a reproducibility constraint on this decision.

## Decision drivers
- Coverage of modern Java syntax in analysed systems (records, `var`, text blocks)
- Fidelity of annotation extraction — the primary reconstruction signal
- Stability and maintenance of the parser
- Effort to migrate existing AST-handling code
- Reproducibility of published results

## Considered options
1. Keep ljavalang 2.1.0 and repair the tree in `java_utils.parse_java_file`
2. Switch back to upstream `javalang` (loses record support)
3. Downgrade to an earlier ljavalang that may predate the defect
4. tree-sitter-java via `tree-sitter` Python bindings
5. A JVM-based parser (JavaParser) via subprocess/JPype

## Decision
Keep ljavalang and pin it in `uv.lock`. **The version stays at 2.1.0**
(decision 2026-09-28): record support is required, and neither switching
parsers nor downgrading is acceptable on the basis of this defect alone.

The annotation defect is therefore handled inside MRF rather than by changing
the dependency. It is repaired in `parse_java_file()`, not in
`has_annotation()` as first assumed: the parser discards the annotations
outright rather than storing them elsewhere in the tree, so nothing can be
recovered from a `Declaration` node alone. `parse_java_file()` is the single
parse choke point (`load_classes` is its only caller) and still has the source
text, so it re-reads the names from the token stream and attaches them to
`unit.types[0]`. Every consumer of the tree then sees correct annotations, not
just `has_annotation()`.

The defect is narrower than first recorded: only the **first** top-level type
of a compilation unit is affected. Fields, methods, nested types and any
further top-level type keep their annotations. Recovery is therefore limited to
`unit.types[0]` and is skipped when the parser already supplied annotations, so
a fixed ljavalang takes precedence. Annotation *arguments* are not restored,
since MRF matches on names only.

Continue to encapsulate all parser-specific types in
`mrf/utilities/java_utils.py` so plugins depend on helpers rather than on
`javalang.tree` directly, keeping options 4 and 5 open.

TODO(author): acceptable risk of depending on a single-maintainer fork?

## Consequences
- Positive: no migration; modern Java syntax supported; the parser choice stays
  behind one module.
- Negative: MRF carries a workaround for a third-party defect, and the token
  scan is a second, simplified reader of Java syntax next to the parser. It is
  bounded: it stops at the first type declaration and gives up unless the
  identifier after the type keyword matches `unit.types[0].name`.
- Positive: reconstruction works again. `tests/test_annotation_recovery.py`
  covers the recovery, and the `minimal-spring` golden fixture fails outright
  if it is removed.
- Negative: fork maintenance risk; `javalang.tree` types currently leak into
  both plugins (`spring_plugin.py`, `java_plugin.py`).
- Follow-up: report the defect upstream to the ljavalang maintainer, and drop
  the workaround once a fixed release exists.
- Follow-up: the golden fixture covers `@SpringBootApplication`, `@Entity` and
  `@RestController`; a record-valued fixture is still missing.

## Pros and cons of the options
### 1. Keep ljavalang 2.1.0 + workaround
- Good, because records and modern syntax keep working.
- Good, because the repair sits at the single parse choke point, so the whole
  tree is correct rather than one predicate.
- Bad, because MRF carries a workaround for a third-party defect.

### 2. Upstream javalang
- Good, because class annotations work without a workaround.
- Bad, because records fail to parse, which ADR-0003 originally set out to fix.

### 3. Earlier ljavalang
- Good, because it may restore annotations with no code change.
- Bad, because it is unverified, and older forks may lack Java 22 coverage.
