Use the skill lemma-smell-refactoring:resolve-non-secured-communication.

## Finding

Security smell: Non-Secured Service-to-Service Communications
(Ponce et al. 2022, §3.7). Root cause 2 of 2 in this system.

An ActiveMQ broker is reached over a plaintext transport by every service that
produces to or consumes from it. This one root cause accounts for 6 of the
system's 9 findings, across 6 queues.

## The facts, as the reconstructed LEMMA models state them

Six producer channels, on CustomerSelfService and PolicyManagement, all of this
shape:

    @javaWithSpring::_aspects.MessageChannel(role = "producer",
        queue = "newpolicies", target = "RiskManagement", broker = "activemq",
        scheme = "tcp", transport = "plaintext")

The six queues are: insurance-quote-request-event-queue,
customer-decision-event-queue, insurance-quote-response-event-queue,
insurance-quote-expired-event-queue, policy-created-event-queue, newpolicies.

A seventh participant holds no channel aspect of its own because it is not a
Java service: the consumer of `newpolicies` is a Node service. It must be
refactored too, or the system will not run once the broker requires TLS.

The models carry no file paths by design. Locate the code yourself.

## Scope

This root cause only: the broker, every Java client of it, and the Node
consumer. Do NOT refactor the REST calls to CustomerCore - that is root
cause 1 and is handled separately.

## Done when

- the broker's connectors use a TLS scheme and NO plaintext connector remains
- every client addresses the broker over that TLS scheme and presents a
  client certificate
- every affected Java service still compiles with its own ./mvnw
