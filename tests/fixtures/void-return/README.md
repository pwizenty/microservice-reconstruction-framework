# Fixture: void-return

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies.

## What it exercises
That an operation which returns nothing has no outgoing parameter.

| Method | Returns | Expected |
|---|---|---|
| `deleteCustomer` | `ResponseEntity<Void>` | only the incoming `id` |
| `createCustomer` | `void` | only the incoming `name` |
| `getCustomers` | `String` | the incoming `filter` and an outgoing `String` |

A return type is reconstructed as a parameter with the exchange pattern `Out`
whose name is the type. For a method returning nothing that produced an
outgoing parameter named after the absence of a value:

```text
deletePolicy( … , sync out void : PolicyManagement::PolicyManagement.Void);
```

Three things were wrong with it. `Void` means the operation returns nothing, so
there should be no outgoing parameter at all. `Void` needs no import, so the
reconstruction resolved it in the package of the controller and referred to a
data structure no context holds. And `void` is a keyword, which a parameter of
a service model may not be called.

`ResponseEntity` is unwrapped before the check, since Spring writes a response
without a body as `ResponseEntity<Void>`, and the primitive `void` is caught
as well.

## Notes on the expected output
- `getCustomers` is in the fixture to show that an ordinary return is
  untouched: it keeps its outgoing parameter.
- The parser reports the primitive `void` as the plain string `"void"` and
  every other return type as a node carrying a name. Both reach the check, so
  `createCustomer` covers a shape that a node-only check would crash on.

Paths in `expected_pipeline.json` are relative to this fixture directory.
