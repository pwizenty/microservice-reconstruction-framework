# s2s-server-connectors

Origin: written for this test, not excerpted from a system.

Exercises what no system available here configures: a service with **two server
connectors** that differ in whether they use TLS.

```properties
server.port=8443
server.ssl.enabled=true
server.ssl.client-auth=need

management.server.port=9001
```

The expected facts are two `ServerEndpoint` records: the main connector with
`tlsEnabled=true` and `clientAuth=need`, the management connector with
`tlsEnabled=false`. That is the case the task document called
`additionalPlaintextPort`, expressed as a record per connector — each says which
connector it is and whether it uses TLS, so a third connector needs no new
field and the management connector's own TLS settings have somewhere to go.

Neither Lakeside Mutual nor park-and-charge configures TLS at all: eleven
services between them, every one a plaintext main connector and no management
port. So the TLS-positive and two-connector paths are reachable only through a
fixture like this one.

The service makes no outgoing call on purpose. A service that calls nothing
still answers on a port, and whether that port uses TLS is the other half of the
*Non-Secured Service-to-Service Communications* smell — `CustomerCore` of
Lakeside Mutual is exactly such a service.
