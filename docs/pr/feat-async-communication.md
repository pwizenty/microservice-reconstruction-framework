## Summary

A service that talks to another over a message queue was invisible to the
reconstruction. Only synchronous calls were reconstructed, so Lakeside Mutual's
six messaging interactions produced no facts at all — and a rule for security
smell §3.7 that cannot see them reports a system as quieter than it is.

```diff
 mrf/plugins/service/communication/
 ├── detectors/
 │   ├── detector.py          # Detector protocol, ServiceCall
+│   │                        #   + MessagingDetector protocol, MessageChannel
 │   ├── __init__.py          # DETECTORS
+│   │                        #   + MESSAGING_DETECTORS, a second registry
 │   ├── feign.py
 │   ├── rest_template.py
+│   └── jms.py               # @JmsListener, JmsTemplate.convertAndSend
 ├── server.py                # what a service answers on
+├── broker.py                # which broker, over which transport
 └── communication_plugin.py  # + channels, pairing, deduplication
```

A **channel** is one declared interaction with a queue by one service, in one
place in the sources: a role (`producer` or `consumer`), the queue, the broker
and the scheme it is reached over. Not one fact per queue — two services at the
ends of one queue are two independent findings for a rule that judges ordered
pairs, and each is evidenced in its own file and line.

The destination is followed rather than guessed:

```text
convertAndSend(queueName, event)
  queueName is an argument        -> find the field it names
    the field carries @Value      -> read the placeholder
      ${insurance-quote-request-event.queueName}
        resolve against the service's own configuration
          -> "insurance-quote-request-event-queue"
```

The broker is decided in three steps, each a fallback for the one before:
the service's own `spring.activemq.broker-url`; else the connectors an embedded
`BrokerService` adds, matched by property-name hint; else ActiveMQ's documented
default `tcp://localhost:61616`, marked `defaulted` so a reader can tell a
measured transport from an assumed one. Where a service runs several connectors
the **least protected one wins**, because a broker reachable over `tcp://` is
reachable over `tcp://` whatever else it also offers.

Pairing is symmetric. A producer and a consumer of the same queue name each
learn the other's service name, so a channel carries a `target`. The first
version pinned it on the producer only and consumers showed `<unpaired>`
although a producer existed — the queue is the join, not the direction.

This runs in the Communication phase, which `reconstruction_handler.py:117`
schedules after the Node plugin's `assign_to` at `:110`. That ordering is what
lets a Java producer pair with a Node consumer: the Node facts exist by then.

## Evidence

**Before:** no channel facts, on any system.

```console
$ git checkout origin/dev && uv run pytest tests/test_message_channels.py -q
no tests ran in 0.00s
```

**After:** 10 new checks, and the full suite unchanged elsewhere.

```console
$ uv run pytest tests/test_message_channels.py -q
..........                                    10 passed

$ uv run pytest -q
..........................................    150 passed

$ uv run ruff check && uv run ruff format --check && uv run mypy
All checks passed!
119 files already formatted
Success: no issues found in 57 source files
```

On Lakeside Mutual, reconstructed rather than asserted:

```console
$ # counted from the microservice collection after the run
channels=11  queues=6  services=2  unpaired=0  non-plaintext=0
roles: {'producer': 6, 'consumer': 5}
   customer-decision-event-queue
   insurance-quote-expired-event-queue
   insurance-quote-request-event-queue
   insurance-quote-response-event-queue
   newpolicies
   policy-created-event-queue
```

Two services carry all eleven, because only `policy-management-backend` and
`customer-self-service-backend` use JMS. The sixth consumer is
`risk-management-server`, which is Node: it declares no JMS, so it holds no
channel of its own, and the `newpolicies` producer still reaches it as a
`target`. That pairing is the ordering dependency above doing its work — and it
is the one case that proves the pairing is not Java-to-Java only.

All eleven are plaintext, which is the corpus's property and not the
detector's: `spring.activemq.broker-url` is set nowhere in the system, and the
embedded broker's two connectors are `stomp://` and `tcp://`.

The fixture `s2s-messaging` covers the paths the corpus cannot. Its expected
output was written by hand before the detector produced any, and includes the
three cases that are easy to get silently wrong — a destination that resolves
through a `@Value` placeholder, one given as a literal, and one that resolves to
nothing and is recorded as `unresolved` rather than dropped:

```json
{ "queue": "orders-queue", "role": "producer", "target": "Subscriber",
  "property": "orders.queueName", "broker": "activemq",
  "brokerAddress": "tcp://broker:61616", "scheme": "tcp",
  "transport": "plaintext", "technology": "JMS",
  "file": "…/EventProducer.java", "line": "19" }
```

The six existing fixtures gained an empty `channels` list rather than being
left without the key, so a fixture that should find no channel asserts that it
finds none.

**The reconstruction has to be re-run** for these facts to reach the database:

```console
! docker start mrf-mongo && uv run mrf -r -p Java Spring Communication Docker Protobuf Node -t ~/Entwicklung/MSA-Examples/LakesideMutual
```

`-r` matters: `__save` upserts on `qualified_name` and never clears its target,
so without it a stale document survives a run that no longer produces it. All
six plugins matter too — dropping `Node` leaves the Node consumer unpaired and
`RiskManagementServerContainer` deploying nothing.

## Merge Danger

**Door:** two-way. New files plus a second registry; no existing detector,
model class or repository changes shape.

**Blast Radius:** the meta-data of every microservice

`channels` is a new key in the communication plugin's `Data` values, so every
reconstructed microservice of a system that uses JMS gains facts it did not
have. Per ADR-0009 these are facts only — there is no field named `insecure`
and no severity anywhere in them. Whether a `tcp://` broker is a smell is
decided on the LEMMA side.

Three things to know before relying on it:

- **Only JMS/ActiveMQ.** Kafka and AMQP are not detected (backlog A8b), so a
  system using them still reports nothing and that absence does not mean safety.
- **An unresolvable destination becomes `unresolved`, not nothing.** A rule
  reading the facts must treat it as undecided rather than as safe; the LEMMA
  validator does.
- **The default broker URL is an assumption.** Where `defaulted` is set, the
  transport is ActiveMQ's documented default rather than something read from
  the system, and a deployment that overrides it by environment variable would
  not be seen — that is backlog A5.

A system reconstructed before this has no channel facts and should be
regenerated rather than compared.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
