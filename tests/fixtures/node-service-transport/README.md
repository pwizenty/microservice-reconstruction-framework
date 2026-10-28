# Fixture: node-service-transport

## Origin and licence
Hand-written for this test suite, not taken from any external system. No
third-party licence applies. Both projects have the shape of Lakeside Mutual's
`risk-management-server`: the same dependencies, the same configuration
sections, the same two channels — one gRPC endpoint it serves, one queue it
consumes — and `index.js` opens them the way that service opens them.

Compared by `tests/test_grpc_node_plugins.py` against `expected_model.json`.

## What it exercises
That the transport of a Node service's channels is read from the code that opens
them. The sibling fixture `node-service` covers the third outcome: a service
whose sources were not read at all keeps `transportSecurity: unresolved`,
because absence of a TLS setting is not evidence of plaintext.

### `plaintext` — both channels unprotected

| Element | Exercises |
|---|---|
| `grpc.ServerCredentials.createInsecure()` | `GrpcServer.transportSecurity: plaintext`, with `index.js` as the `valueSource` |
| `stompit.ConnectFailover` with no `ssl` option | `MessageQueue.transportSecurity: plaintext`. The library's default is a plain TCP connection, and here the call that opens the channel is in the sources, so plaintext is read rather than assumed |
| no `clientAuth` on either fact | nothing requires a client certificate, so nothing is stated |

### `secured` — both channels mutually authenticated

| Element | Exercises |
|---|---|
| `createSsl(ca, [pair], true)` | `transportSecurity: tls` **and** `clientAuth: need`. The third argument is what makes the server require and verify a client certificate, which is the half of the refactoring that mutual TLS adds over plain TLS |
| `ssl: true` in the connection options | `MessageQueue.transportSecurity: tls` |
| `key`, `cert` and `ca` paths in `config.json` | read as addresses of key material and never as values; the facts carry no path to a certificate and no secret |
| the broker's own `clientAuth` | **not** reported. What a broker requires of its clients is the broker's configuration, and the broker is no service of this model |

### What it does not exercise
A connection whose options are assembled further away than
`MESSAGING_WINDOW` lines from the call that opens it. That is reported as
unresolved, by design: the window is a heuristic, and a guess in either
direction would be worse than a gap.
