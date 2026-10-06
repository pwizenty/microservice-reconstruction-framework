# Fixture: protobuf-types

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. The shapes are the ones Lakeside Mutual's
`risk-management-server/riskmanagement.proto` uses, plus the proto3 constructs it
does not, so the fixture covers the language rather than one file.

Compared by `tests/test_protobuf_plugin.py` against `expected_protobuf.json`.
The name differs from `expected.json` on purpose: the fixtures of
`test_golden.py` are found by that name and run the Java and Spring plugins,
which have nothing to reconstruct here.

## What it exercises
Every type proto3 offers, and everything in a file that is not a declaration.

| Element | Exercises |
|---|---|
| all fifteen scalars | each maps onto a primitive. A scalar with no mapping would silently become a complex type, so the mapping is asserted for all of them |
| `repeated string many_strings` | a collection of a primitive, named `StringList` with the first letter raised, as the LEMMA side writes it |
| `map<string, Nested> by_name` | read as a sequence of the value type; the model has no map, and the value is what a consumer needs |
| `google.protobuf.Timestamp created_at` | a type of an **imported** file, which this reconstruction has no structure for. Reported as `UNSPECIFIED` rather than qualified under this context, which would claim a structure that does not exist |
| `oneof either` | its fields are optional by construction and name the group they belong to |
| a commented-out service and message, in both comment forms | **not** reconstructed |
| `import`, `option`, `reserved`, a field option, an rpc's option block | read and skipped, so a file that uses them parses rather than failing |
