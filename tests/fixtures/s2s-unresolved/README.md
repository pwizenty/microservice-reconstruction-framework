# Fixture: s2s-unresolved

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
That a call of unknown transport is never reported as encrypted.

Extends `s2s-placeholder` with a third service and a second client:

| Element | Exercises |
|---|---|
| `@FeignClient(name = "reporting", url = "\${reporting.baseURL}")` with the property defined **nowhere** | the `url` element of a Feign client is an address by definition, so the call is reported with `scheme=UNRESOLVED` rather than dropped |
| `reporting` as a service of the system | the unresolved call targets a **known** service, so it counts towards the aggregate; a target matching nothing would be `EXTERNAL` and excluded |
| the transport of `Gateway` | `unresolved`, not `tls`, although its other call is `https`: one call of unknown transport makes the transport of the service unknown |

This is the case the aggregation is easiest to get wrong in, which is why it has
a fixture of its own rather than a branch of `s2s-placeholder`.
