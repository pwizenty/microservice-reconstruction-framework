# Fixture: docker-minimal

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. The Compose specification imitates the shape of
Lakeside Mutual's: a service built from a directory, an infrastructure service
taken from an image, and a dependency between them.

## What it exercises
The operation phase (ADR-0008), end to end through `ReconstructionHandler`.

| File | Exercises |
|---|---|
| `docker-compose.yml` | Both node kinds, `build:` and `image:`, and `depends_on` |
| `customer-core/Dockerfile` | The operation environment, read from `FROM` |
| `customer-core/src/…/CustomerCoreApplication.java` | The microservice a container deploys |

Reconstructed from it:

- `Eureka`, an **infrastructure node**, because its Compose service name
  matches `INFRASTRUCTURE_NODE_NAMES`. It has no `build:`, so no operation
  environment, and deploys nothing.
- `CustomerCoreContainer`, a **container**, which deploys `CustomerCore`,
  depends on `Eureka` and runs on `openjdk:11-jre-slim`.

The container is matched to its microservice through the build directory: the
artifact `CustomerCoreApplication.java` was reconstructed from lies below
`customer-core/`, which is what `build: customer-core` names. Matching by
directory rather than by name keeps the two independent of each other's naming.

## Notes on the expected output
- `expected_pipeline.json` is written by hand, not generated from the plugin,
  and is the only expectation this fixture has. There is no `expected.json`,
  because the operation phase only exists in the full pipeline: a container
  cannot know which microservice it deploys before the service phase has run.
- `qualified_name` equals `name` for both nodes. A Compose specification names
  no namespace, and inventing one would be a claim the sources do not make.
- `operation_environment` is `null` for `Eureka`. That is the documented shape
  for a node without a Dockerfile, not a missing value.
- The dependency is recorded as `Eureka`, the *node* name, not `eureka`, the
  Compose service name. The Compose name is kept as meta-data under
  `ComposeService`, so nothing is lost.

Paths in `expected_pipeline.json` are relative to this fixture directory.
