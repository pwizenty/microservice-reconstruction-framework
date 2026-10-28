# Asynchronous service-to-service communication

Plan for reconstructing the messaging links between services, and for making
every link visible in a LEMMA service model. Decided with Philip Wizenty on
2026-10-13; the four choices his answers settled are marked **[decided]**.

Why: smell **3.7 Non-Secured Service-to-Service Communications** of Ponce et al.
(2022) covers "each communication channel between any two microservices", and a
queue is such a channel — see `security-smells.md`. Today only the three
synchronous REST links of Lakeside Mutual are reconstructed, so a detection rule
would miss every asynchronous interaction in the system it is meant to judge.

## 1. What the corpus holds, measured

```
policy-management     → newpolicies                          → RiskManagement
policy-management     → insurance-quote-response-event-queue → customer-self-service
customer-self-service → insurance-quote-request-event-queue  → policy-management

customer-decision-event-queue        listener in policy-management,      no producer in the repository
insurance-quote-expired-event-queue  listener in customer-self-service,  no producer in the repository
policy-created-event-queue           listener in customer-self-service,  no producer in the repository
```

| | |
|---|---|
| Producer | `@Autowired JmsTemplate` + `convertAndSend(queueName, event)`, the destination a `@Value("${…queueName}")` field |
| Consumer | `@JmsListener(destination = "${…queueName}")` |
| Broker | **embedded** in `policy-management-backend`: `BrokerService.addConnector(stompBrokerBindAddress)` and `addConnector(tcpBrokerBindAddress)` |
| Connectors | `stomp://0.0.0.0:61613`, `tcp://0.0.0.0:61616` — **plaintext**; ActiveMQ TLS would be `ssl://` |
| `spring.activemq.broker-url` | **not set anywhere**, so a client uses ActiveMQ's default `tcp://localhost:61616` |

Three of the six queues pair, three have a consumer only. The first pair is
**cross-technology**: a Java producer and a Node consumer, which the Node plugin
already reports as `MessageQueue{queue: newpolicies, scheme: stomp}`.

## 2. Decisions

**An asynchronous link is its own fact** **[decided]**, a `MessageChannel`
beside `ServiceCall`. The evidence differs — a queue and a broker rather than a
verb and a path — and so does the refactoring: mutual TLS secures a REST call,
a broker's `ssl://` secures a queue. Putting both in one flat map would leave
every `ServiceCall` carrying meaningless queue keys and every `MessageChannel`
carrying a meaningless verb.

**Both endpoints are reported, paired where possible** **[decided]**. A service
that consumes a queue is a fact whether or not the publisher is in this
repository: the message may come from outside it, or the publisher may be
unimplemented. An unpaired consumer gets an unresolved target; nothing is
invented and nothing is dropped.

**This step ends with facts in the model, not with a finding** **[decided]**.
The 3.7 validation is the step after. A rule written before its facts have been
seen in a model would be written against a guess.

**gRPC client calls stay out** **[decided]**. The gRPC server is already
reported (`GrpcServer`, `transportSecurity: UNRESOLVED`); the client side is a
later step.

## 3. What has to be read from the sources

| Fact | From |
|---|---|
| A service produces to a queue | a `JmsTemplate` field, and a `convertAndSend`/`send` whose destination resolves |
| A service consumes a queue | `@JmsListener(destination = …)` |
| The queue's name | the placeholder resolved against the service's own configuration |
| The broker | `spring.activemq.broker-url`, else the connectors an embedded `BrokerService` adds, else ActiveMQ's default |
| The transport | the broker URL's scheme: `tcp`/`stomp` plaintext, `ssl`/`stomp+ssl` TLS |

**The destination is a field, not an argument.** `convertAndSend(queueName, event)`
names a field annotated `@Value("${riskmanagement.queueName}")`, so the analysis
has to follow the field to its annotation and the annotation to the property.
A destination that is a literal is read directly; one that is a method
parameter, or built at run time, is unresolved rather than guessed.

**A defaulted broker says so**, as a defaulted `server.port` does in A1: where
nothing configures a broker URL, the fact carries ActiveMQ's default and a flag,
so a reader can tell a value the sources state from one the framework supplies.

## 4. The fact

```
MessageChannel
    role          producer | consumer
    queue         resolved queue name
    target        the microservice at the other end, or absent when unpaired
    broker        activemq | …
    scheme        tcp | stomp | ssl | …
    transport     plaintext | tls | unresolved
    brokerAddress host and port
    defaulted     true when the broker URL is the framework's default
    file, line    where the producer or consumer is
```

Flat, as the Mongo seam requires (ADR-0009). One entry per channel per service,
so a service that produces to two queues carries two entries.

### Pairing

By **resolved queue name**: a producer of queue `Q` pairs with every consumer of
`Q`. The Node plugin's `MessageQueue` facts take part, which is what joins the
Java producer of `newpolicies` to its Node consumer — and the handler already
runs Node's `assign_to` before the Communication plugin's, so those facts are on
the microservices by the time pairing happens.

A queue name that resolves for neither side, or that two unrelated services use
by coincidence, leaves the target absent. Reporting the wrong peer would be
worse than reporting none.

## 5. The LEMMA side: per-link facts in the model

Today only two communication facts are declared as aspects:

```
aspect ServiceCommunicationTransport<singleval> for microservices   ← one value for ALL outgoing calls
aspect ServerEndpoint for microservices                             ← per connector
```

`ServiceCall` and `ServiceCallEndpoint` exist in the database and **never reach
the model**. So a rule can see *that* A requires B, and separately that A's
calls are "plaintext" or "mixed", but not that **this** link is plaintext —
and `mixed` says a problem exists somewhere without saying where.

This step declares `ServiceCall`, `ServiceCallEndpoint` and `MessageChannel` as
aspects, **none of them `<singleval>`**, so each may appear once per link.
`ServiceDslValidator.checkUniqueAspects` rejects a repeated single-valued aspect
and returns early for one that is not — the constraint A1 had to discover.

There is **no aspect join point for a `required` dependency**: the Technology
DSL offers `types, fields, domainOperations, domainParameters, microservices,
interfaces, operations, parameters`. A per-link fact can therefore only be a
repeatable aspect on the microservice that names its target. That is a
constraint, not a preference, and the detection rule has to join the aspect's
`target` to the `required` entry itself.

## 6. Risks, each measured

- **Test code.** `RiskManagementMessageProducerTests` is a producer too. The
  plugin's existing `__without_test_code` and `__is_test_class` exclude it;
  a fixture asserts that it stays excluded.
- **Three unpaired consumers.** Expected, not a defect. The golden fixture
  records them as consumer-only facts with an absent target.
- **The embedded broker.** `policy-management-backend` *is* the broker as well as
  a client. Its connectors decide the transport for everything on that broker,
  so the fact for a *client* service has to be read from the broker's
  configuration and not only from its own — or every client's transport comes
  out unresolved.
- **`setTrustAllPackages(true)`** appears in `MessagingConfiguration`. Not 3.7 —
  it is a deserialisation risk — but worth recording where it is seen rather
  than discarding it silently.

## 7. Steps

1. **`MessageChannel` and the detectors** — a `jms.py` detector for the producer
   and the consumer, placeholder and field resolution reusing
   `configuration.py`. Fixtures: a paired producer and consumer, a
   consumer-only queue, a literal destination, an unresolvable destination, a
   producer in test code.
2. **Broker resolution** — `spring.activemq.broker-url`, an embedded
   `BrokerService`'s connectors, and the framework default with its flag.
   Fixtures: each of the three, plus an `ssl://` broker, which **no sample
   system has**, so TLS is fixture-only exactly as in A1.
3. **Pairing** — by resolved queue name, including the Node `MessageQueue`
   facts. Golden fixture over the real shape: three pairs, three consumer-only.
4. **The LEMMA aspects** — `ServiceCall`, `ServiceCallEndpoint` and
   `MessageChannel` declared non-single-valued, and the expected models updated.
5. **Verification** — ruff, mypy, pytest, the golden fixtures, and the LEMMA
   regression test; then a run against Lakeside Mutual showing six messaging
   facts beside the three REST links.

## 8. Not in this plan

- The 3.7 validation rule itself — the next step.
- gRPC client calls.
- Kafka, and messaging technologies other than JMS/ActiveMQ: nothing here uses
  them, so a detector for them would be untestable (backlog A8).
- Mesh facts, resolved target identity, profiles, several evidence records per
  fact — backlog A4, A5, A6, A7.
