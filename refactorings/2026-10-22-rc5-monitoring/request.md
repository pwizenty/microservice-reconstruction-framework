Use the skill lemma-smell-refactoring:resolve-non-secured-communication.

## What is to be repaired

This tree already resolves every finding the detection reports: the Customer
Core's connector, the ActiveMQ broker over both of its transports, and the
Risk Management server's gRPC endpoint are mutually authenticated.

One channel is broken by that work and is not a finding, because the
monitoring server is not reconstructed as a microservice and therefore has no
model the detection can judge. The repair of the Customer Core declared the
loss in its notes, and a runtime check confirms it:

    Spring Boot Admin, /instances, on this tree
        customer-core                    OFFLINE
        customer-management-backend      UP
        customer-self-service-backend    UP
        policy-management-backend        UP

The Customer Core still registers itself with the monitoring server, because
that direction is plaintext HTTP to port 9000 and was never changed. What
fails is the other direction: the monitoring server polls the Customer Core's
actuator endpoints over plaintext HTTP, and that connector now requires a
client certificate.

## Scope

The monitoring relationship only. Do NOT weaken or change the connector of the
Customer Core, the broker's connectors, or the gRPC endpoint: they are
correct, and every finding of this system is already resolved. The repair
belongs on the monitoring side of the channel.

The other three services register with the same monitoring server and are
reachable over plaintext, so whatever you do must keep them working.

## Done when

- the monitoring server reaches the Customer Core again, and
  `http://localhost:9000/instances` reports four services with status UP
- it reaches the Customer Core over TLS with a client certificate from the
  same development authority, not over plaintext and not by weakening the
  Customer Core
- the detection still reports zero findings for this tree
- every service still starts and the existing tests still pass
