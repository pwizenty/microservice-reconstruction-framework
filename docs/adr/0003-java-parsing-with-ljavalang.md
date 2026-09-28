# ADR-0003: Parse Java sources with ljavalang

- Status: Proposed (documents the current state)
- Date: 2026-09-24
- Deciders: Philip Wizenty

## Context and problem statement
The Java and Spring plugins analyse Java ASTs (annotations, fields, method
signatures, imports) via `mrf/utilities/java_utils.py`. The code imports
`javalang` but uses `RecordDeclaration`, which only exists in **ljavalang**, a
fork of the unmaintained `javalang` with Java 9–22 support. `requirements.txt`
lists `ljavalang`, while the `Pipfile` lists `javalang`, which would fail at import.

## Decision drivers
- Coverage of modern Java syntax in analysed systems (records, `var`, text blocks)
- Stability and maintenance of the parser
- Effort to migrate existing AST-handling code
- Reproducibility of published results

## Considered options
1. ljavalang (API-compatible fork of javalang)
2. tree-sitter-java via `tree-sitter` Python bindings
3. A JVM-based parser (JavaParser) via subprocess/JPype

## Decision
Proposed: keep ljavalang (option 1) and pin it in `uv.lock`. Encapsulate all
parser-specific types in `mrf/utilities/java_utils.py` so plugins depend on
helpers rather than on `javalang.tree` directly, keeping option 2 open.

TODO(author): acceptable risk of depending on a single-maintainer fork?

## Consequences
- Positive: no migration; modern Java syntax supported.
- Negative: fork maintenance risk; `javalang.tree` types currently leak into
  both plugins (`spring_plugin.py`, `java_plugin.py`).
- Follow-up: remove the `javalang` entry from `Pipfile` (or drop the Pipfile,
  see ADR-0005); add golden fixtures containing records.
