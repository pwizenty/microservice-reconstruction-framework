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
The parser is **ljavalang** (see ADR-0003, ADR-0006), which reserves `with` as
a keyword:

```python
>>> 'with' in javalang.tokenizer.Keyword.VALUES
True
```

Java does not. `with` is a *contextual* keyword of derived record creation
(JEP 468, preview), so ordinary uses of it as an identifier are legal and
common - Jackson's fluent API being the case here:

```java
reader.readerFor(Map.class).with(schema).readValues(file)
```

Any `a.with(b)`, `int with = 1;` or `void with() {}` fails the same way. The
reported position is misleading: the parser blames a token earlier in the
statement, which is why this looks like a generics problem at first sight.

Should ljavalang stop reserving `with`, this fixture's `DataLoader.java` starts
parsing and the expected output changes: `Customer` gains nothing, but the
skip warning disappears and the file count in it changes. Replace the file with
another construct the parser rejects rather than deleting the fixture - the
behaviour under test is the skipping, not this particular defect.

## Notes on the expected output
- `contexts` holds `CustomerCore` with the `Customer` structure, and
  `microservices` the `Customer` interface with `getCustomers`, exactly as in
  `minimal-spring`. That is the point: the rejected file costs nothing else.
- `DataLoader` is a plain class with no annotation, so even when it parses it
  contributes no data structure of its own.

Paths in `expected.json` and `expected_pipeline.json` are relative to this
fixture directory.
