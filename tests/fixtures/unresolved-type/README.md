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
generated service model imported a `None.data` that does not exist. The method
now falls back to `UNKNOWN_CONTEXT`, the same marker the Java plugin already
uses, and the expected output records

    "qualified_name": "UnknownContext.ResponseEntity"

## Notes on the expected output
- The fixture defines no entity, so `contexts` holds the bounded context
  without any data structures. The interesting part is under `microservices`.
- `UnknownContext` is a marker, not a reconstructed context: no context of that
  name is created here, so a LEMMA service model generated from this output
  still imports a data model that does not exist. Representing types from
  outside the reconstructed system is an open question, this fixture only pins
  down that the marker is used instead of a stringified `None`.
- The return type is modelled as a parameter whose `name` is the *type*
  (`String`) with `exchange_pattern: Out`, as in `minimal-spring`.

Paths in `expected.json` are relative to this fixture directory.
