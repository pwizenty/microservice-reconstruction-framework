# Fixture: s2s-plaintext

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. The package layout imitates a Maven multi-module
system (`<service>/src/main/java`, `<service>/src/main/resources`), because the
plugin reads the module a file belongs to from exactly that layout.

Compared by `tests/test_communication_plugin.py` against
`expected_communication.json`. The name differs from `expected.json` on purpose:
the fixtures of `test_golden.py` are discovered by that name, and what is
compared here is the communication facts rather than the domain and service
models.

## What it exercises
A literal plaintext URL, and a service that calls nobody.

| Element | Exercises |
|---|---|
| `CalleeProxy` with `restTemplate.getForObject("http://callee:8081/greeting", …)` | a URL stated as a literal in a method, with no placeholder to resolve |
| the target `callee` | resolution by service name: `spring.application.name=callee` matches, so the call is `SERVICE` and reported under the name the reconstruction knows, `Callee` |
| `Callee` itself | a service that makes no call gets **no** transport entry, and therefore no aspect in the LEMMA model |

Without the plugin's class-level check the fixture would still pass; what it
guards is that a literal URL in a class that uses `RestTemplate` is found at
all, and that the aggregate is `plaintext`.
