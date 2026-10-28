# Fixture: s2s-mixed

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
A service that reaches one peer in plaintext and another over TLS.

| Element | Exercises |
|---|---|
| two `@Value` fields on one class, `alpha.baseURL=http://alpha:8081` and `beta.baseURL=https://beta:8443` | several addresses injected into one class, each becoming a call of its own |
| the transport of `Hub` | `mixed`, which is why the vocabulary has the value: neither `plaintext` nor `tls` would be true |
| `Clients` holding a `RestTemplate` field but calling nothing with it | the unit of detection is the class, not the call site. The parser resolves no symbols, so a class that uses an HTTP client is reported as calling the addresses it injects. The evidence names the line of each address so the fact can be checked |
