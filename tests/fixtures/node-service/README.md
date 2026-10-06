# Fixture: node-service

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. The two projects have the shape of Lakeside
Mutual's `risk-management-server` and of one of its frontends: the same
dependencies, the same configuration sections, the same file names.

Compared by `tests/test_grpc_node_plugins.py` against `expected_model.json`.

## What it exercises
That a Node project is a service of the architecture only when something says
so, and what its configuration states when it is.

### `reporting` — a service

| Element | Exercises |
|---|---|
| `reporting.proto` | the microservice and the context, reconstructed by the Protobuf plugin; the Node plugin attaches to it rather than reconstructing one of its own |
| `package.json` with `@grpc/grpc-js` and `stompit` | the dependencies identify the technologies; a configured gRPC endpoint with no gRPC dependency is **not** reported |
| `config.json` section `grpc` | the endpoint it serves, `0.0.0.0:50052` |
| `config.json` section `activemq` | the broker, its address, and the queue `newreports` |
| `stompit` as the dependency | the scheme `stomp`. The configuration does not state it - the library decides the wire protocol |
| `username` and `password` in the configuration | reported as `credentialsConfigured: true` and **never** as values. That a broker is authenticated is architecture information; the secret is not, and a test asserts neither string reaches the model |
| no TLS section anywhere | `transportSecurity: UNRESOLVED`, not `plaintext`. Whether a channel is encrypted is decided in the code that opens it, which this step does not read, and absence is not evidence |

### `dashboard` — not a service

A React project with a `package.json` and a `config.json` that even names a gRPC
address. **Nothing** is reconstructed for it: no microservice, no context, no
facts. Every frontend of Lakeside Mutual has a manifest, and two configure an
address, so a plugin that treated a manifest as a service would put three user
interfaces into the service models.
