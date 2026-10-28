# Fixture: ambiguous-type

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. It reproduces in miniature what Lakeside Mutual
does: several microservices of one system define a class of the same name.

## What it exercises
That a type is resolved to the source in its own microservice, not to the
first file of that name in the system.

| File | Exercises |
|---|---|
| `customer-core/…/domain/CustomerId.java` | One of two classes named `CustomerId`, with the field `customerCoreId` |
| `policy-management/…/domain/CustomerId.java` | The other, with the field `policyManagementId` |
| `…/domain/Customer.java`, `…/domain/Policy.java` | An `@Entity` in each service with a field of type `CustomerId` |

The two `CustomerId` classes differ only in their field, which is what makes
the expected output say *which* of them a context received.

`JavaPlugin.__handle_project_dependency` used to look a type up by file name
alone. With two candidates it took whichever the file system yielded first, so
both services resolved to the same class: `CustomerCore` received a
`CustomerId` and `PolicyManagement` received none, while its `Policy.id`
referred to a structure its context did not hold. Lakeside Mutual defines
`CustomerId` four times, one per service, and lost five of the ten data
structures of `CustomerCore` that way - but only in a whole-system run, which
is why per-service runs looked correct.

`__find_class` now prefers the candidate sharing the most path segments with
the qualified name being resolved.

## Notes on the expected output
- Each context holds its own `CustomerId`: `CustomerCore` the one with
  `customerCoreId`, `PolicyManagement` the one with `policyManagementId`. That
  is the whole point of the fixture; a change that makes both contexts hold the
  same one is the defect returning.
- There is no `expected.json`. The plugins in isolation do not resolve
  dependencies, so the ambiguity only arises in the full pipeline.
- The fields carry no type in the serialised output because the reconstruction
  records a complex field type rather than a primitive one, as in the other
  fixtures.

Paths in `expected_pipeline.json` are relative to this fixture directory.
