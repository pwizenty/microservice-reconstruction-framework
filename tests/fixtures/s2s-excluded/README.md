# Fixture: s2s-excluded

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
Everything that looks like a call and is not one.

| Element | Expected |
|---|---|
| `SCHEMA = "http://www.w3.org/2001/XMLSchema"` | **no call**: an XML namespace is an identifier that happens to look like an address |
| `ExternalProxyTest` under `src/test`, with `http://localhost:9999/stub` | **no call**: test code is excluded by its path, and by the class name suffix |
| `@Value("\${exchange.rates.url}")` resolving to `https://api.exchangerate.host` | one call, `targetKind=EXTERNAL`, excluded from the aggregate - this smell is about traffic inside the application |
| `@Value("\${missing.service.url}")`, defined nowhere | **no call**, deliberately. Unlike a Feign `url`, a `@Value` field is not known to hold an address, so an unresolvable one is not reported as a call of unknown transport. `s2s-unresolved` covers the case where the source does say it is an address |
| the transport of `Service` | **none**: its only call leaves the application, so the service gets no aspect |
