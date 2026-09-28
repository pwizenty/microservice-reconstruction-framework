# Fixture: minimal-spring

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. It imitates the package layout of Lakeside Mutual
(`<group>.<service>` with `domain` and `interfaces` sub-packages), because the
qualified-name heuristics in `mrf/utilities/java_utils.py` were tuned on that
system.

## What it exercises
Three source files, the smallest set that drives both plugins end to end:

| File | Annotation | Exercises |
|---|---|---|
| `CustomerCoreApplication.java` | `@SpringBootApplication` | Microservice detection (`SpringPlugin`) and bounded-context detection (`JavaPlugin`); `Application` suffix stripping |
| `domain/Customer.java` | `@Entity`, `@Id` | Data structure reconstruction, primitive fields, DDD `Entity` and `Identifier` meta-data |
| `interfaces/CustomerController.java` | `@RestController`, `@GetMapping` | Interface detection, `Controller` suffix stripping, operation with an `In` parameter and the `Out` return type |

The package names are deliberately three levels deep
(`com.example.customercore`) so that `match_microservice_interface` reaches
`HIERARCHY_LEVEL` (3) matching parts and links the controller to the service.

All three annotations sit on the **first top-level type** of their file, the
position ljavalang 2.1.0 drops (ADR-0003). This fixture therefore also guards
the recovery in `parse_java_file`: without it, `expected.json` collapses to two
empty lists.

## Notes on the expected output
Two properties are worth knowing before treating a diff as a regression:

- The return type is modelled as a parameter whose `name` is the *type*
  (`String`) with `exchange_pattern: Out`. That is what
  `SpringPlugin.__handle_return_type` does today.
- The interface and the data structure end up with the same
  `qualified_name` (`com.example.customercore.CustomerCore.Customer`), because
  `adjust_qualified_name` re-roots both onto the service name.

Paths in `expected.json` are relative to this fixture directory.
