# Fixture: unparsable-source

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. It is `minimal-spring` plus one file the Java
parser cannot read.

## What it exercises
That a source file the parser rejects does not end the reconstruction of the
whole system.

| File | Exercises |
|---|---|
| `CustomerCoreApplication.java` | Microservice and bounded-context detection |
| `domain/Customer.java` | Data structure reconstruction, unaffected by the rejected file |
| `interfaces/CustomerController.java` | Interface and operation reconstruction, likewise unaffected |
| `application/DataLoader.java` | **Cannot be parsed.** Skipped with a warning |

`load_classes` used to let the parser's exception escape, so a single
unreadable file aborted the run with a bare `javalang.parser.JavaSyntaxError`
and nothing was reconstructed at all. Lakeside Mutual's `customer-core` could
not be reconstructed for that reason: three of its files hit the defect below.
The file is now skipped, named in a warning, and counted in a summary.

## The parser defect this depends on
The parser is **ljavalang** (see ADR-0003, ADR-0006). It reserves the keywords
of a Java 9 module declaration globally:

```python
>>> 'module' in javalang.tokenizer.Keyword.VALUES
True
```

Java does not. Module directives are *restricted* keywords: inside a module
declaration they are directives, everywhere else they are ordinary identifiers.
`registry.module(schema)` is therefore legal Java that the parser rejects.

This fixture first used `.with(schema)`, the form that occurs in Lakeside
Mutual through Jackson's fluent reader and that made three of its files
unreadable. `with` was freed in the fork, so the file started parsing and this
fixture silently stopped testing anything - the reconstruction output is the
same either way, because `DataLoader` carries no annotation and contributes no
data structure. The trigger is now `module`, which stays reserved because the
parser needs it to recognise a module declaration at all.

`tests/test_java_utils.py::test_load_classes_skips_a_file_the_parser_cannot_read`
asserts the rejection directly, so a parser update that makes this construct
readable fails there rather than quietly hollowing out this fixture.

## Notes on the expected output
- `contexts` holds `CustomerCore` with the `Customer` structure, and
  `microservices` the `Customer` interface with `getCustomers`, exactly as in
  `minimal-spring`. That is the point: the rejected file costs nothing else.
- `DataLoader` is a plain class with no annotation, so even when it parses it
  contributes no data structure of its own.

Paths in `expected.json` and `expected_pipeline.json` are relative to this
fixture directory.
