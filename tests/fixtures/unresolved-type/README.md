# Fixture: unresolved-type

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. It reuses the package layout of `minimal-spring`
(`com.example.customercore` with an `interfaces` sub-package) so that the
qualified-name heuristics in `mrf/utilities/java_utils.py` behave the same way.

## What it exercises
A REST operation with a parameter whose type belongs to **no** reconstructed
microservice: `org.springframework.http.ResponseEntity`.

| File | Annotation | Exercises |
|---|---|---|
| `CustomerCoreApplication.java` | `@SpringBootApplication` | Microservice and bounded-context detection |
| `interfaces/CustomerController.java` | `@RestController`, `@GetMapping` | An `In` parameter of a framework type that no microservice owns |

`SpringPlugin.__find_microservice` finds no owning microservice for such a
type. It used to return `None`, which `adjust_qualified_name` interpolated into
the qualified name as the literal string `"None"`:

    "qualified_name": "None.ResponseEntity"

Downstream that reached LEMMA as a data type of a context named `None`, so the
generated service model imported a `None.data` that does not exist. Worse, the
dependency phase then searched the sources for a `ResponseEntity.java`, found
none and aborted the entire reconstruction with a `StopIteration`.

The expected output now records both halves of the fix:

    "qualified_name": "UnknownContext.ResponseEntity",
    "class_type": "UNSPECIFIED"

`UNKNOWN_CONTEXT` is the marker the Java plugin already uses, and the
unspecified class type keeps a type that belongs to no reconstructed
microservice out of the domain models. LEMMA turns an unspecified type into its
`unspecified` primitive, so no data model is imported for it.

## Notes on the expected output
- The fixture defines no entity, so `contexts` holds the bounded context
  without any data structures. The interesting part is under `microservices`.
- The parameter keeps the qualified name `UnknownContext.ResponseEntity`. The
  name records where the type could not be placed; the `UNSPECIFIED` class type
  is what stops it from being treated as a data structure.
- The return type is modelled as a parameter whose `name` is the *type*
  (`String`) with `exchange_pattern: Out`, as in `minimal-spring`.

Paths in `expected.json` are relative to this fixture directory.
