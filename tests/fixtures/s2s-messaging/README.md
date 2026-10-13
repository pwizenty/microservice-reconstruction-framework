# s2s-messaging

Origin: written for this test, not excerpted from a system.

Exercises the asynchronous links of `docs/async-communication-plan.md`:

| | |
|---|---|
| `orders-queue` | a producer and a consumer that **pair**, both through a `@Value` placeholder |
| `audit-queue` | a **literal** destination, read without resolution |
| `events-` + suffix | a destination **built at run time**, reported as unresolved |
| `reports-queue` | a consumer **nothing in this system publishes to** |
| `ConsumerTests` | a `@JmsListener` in test code, which must **not** become a fact |

The broker is `tcp://broker:61616`, configured by the subscriber. A TLS broker
appears in `tests/test_message_channels.py` instead: no sample system
configures one, so it is reachable only through a configuration written for a
test.

The publisher configures no broker URL of its own, so its channels take the
one the subscriber configures — which is how a client of an embedded broker is
resolved in Lakeside Mutual, where no service states a URL at all.
