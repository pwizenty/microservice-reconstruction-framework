# Fixture: s2s-placeholder

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
A placeholder resolved against the calling service's own configuration, over TLS.

| Element | Exercises |
|---|---|
| `@FeignClient(name = "backend", url = "\${backend.baseURL}")` | the address on an annotation of an **interface**, which is where Feign states it |
| `backend.baseURL=https://backend:8443` in `application.properties` | resolving a placeholder through the service's own configuration |
| the resulting scheme | `https`, so the transport of the gateway is `tls` |
| `server.ssl.enabled=true` on the backend | present on purpose and **not** read: what the callee accepts is a later step, and the fixture records that it is not part of this one |

Against a revision that does not resolve placeholders the scheme would be
`UNRESOLVED` and the transport `unresolved`, so the fixture fails without the
resolution it is about.
