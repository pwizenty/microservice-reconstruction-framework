# Fixture: infrastructure-service

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies.

## What it exercises
That a Spring Boot application which runs the system, rather than belonging to
its domain, becomes neither a bounded context nor a microservice.

| File | Exercises |
|---|---|
| `customercore/CustomerCoreApplication.java` | An ordinary service, reconstructed as context and microservice |
| `springbootadmin/MonitoringApplication.java` | `@SpringBootApplication` **and** `@EnableAdminServer`, reconstructed as neither |

The infrastructure class is deliberately called `MonitoringApplication`. Its
name matches nothing in `INFRASTRUCTURE_TECHNOLOGIES`, so the fixture fails
unless the annotation is what excludes it.

`INFRASTRUCTURE_TECHNOLOGIES` used to be the only signal, and it lists
`eureka` and `zuul` only. Lakeside Mutual's `spring-boot-admin` therefore
arrived as a microservice with no interfaces and a context with no data
structures - an empty shell in both models, while the operation phase already
reconstructed it as an infrastructure node. `INFRASTRUCTURE_ANNOTATIONS` names
the annotations that make a Spring Boot application infrastructure, and the
name list stays for infrastructure that carries no annotation of its own.

## Notes on the expected output
- `contexts` and `microservices` hold `CustomerCore` and nothing else. A
  change that reintroduces the infrastructure service into either is the
  defect returning.
- The operation phase is unaffected: an infrastructure node is reconstructed
  from the Compose specification, not from the Java sources, which is why this
  fixture has no `docker-compose.yml` and no operation nodes.

Paths in `expected_pipeline.json` are relative to this fixture directory.
