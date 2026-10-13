## Summary

Two documents, no code. The first records the literature the smell detection is
built on; the second plans the one fact the detection still lacked.

```text
docs/
├── security-smells.md            # the ten smells of Ponce et al. (2022)
│   ├── Where a smell is decided  # MRF collects facts, LEMMA decides (ADR-0009)
│   ├── The taxonomy              # all ten, by ISO/IEC 25010 property
│   ├── 3.7 in full               # the one being implemented
│   └── What the other nine need  # reconstructable / partly / no
└── async-communication-plan.md   # JMS producers, consumers, broker transport
```

`security-smells.md` carries the taxonomy as a table — section, smell, which of
confidentiality / integrity / authenticity it forfeits, the suggested
refactoring, the refactoring's type and how many of the paper's studies report
it. It then takes **§3.7 Non-secured service-to-service communications** apart,
because that is the one with 32 studies behind it and the only one both halves
of which the toolchain already reconstructs.

The decisive clause is quoted rather than paraphrased: the smell holds whenever
two microservices interact without a secure channel, *even if they are within
the same network*. That sentence is what makes a plaintext call between two
containers on one Compose network a finding rather than an acceptable shortcut,
so the rule that implements it should be traceable to it.

`async-communication-plan.md` answers a gap the taxonomy made visible. A rule
for §3.7 has to see **every** interaction, and the six messaging links of
Lakeside Mutual were missing from the facts entirely — a false negative in the
very system the rule is meant to judge. The plan settles four decisions (what a
channel is, how a producer and a consumer are paired, what counts as the
broker, what to do when nothing resolves) before any of it was written.

`docs/backlog.md` splits the old A8 accordingly: **A8a** asynchronous links,
promoted ahead of A2, and **A8b** gRPC and Kafka, which stay blocked for want of
a sample system that uses them.

## Evidence

Documentation, so the evidence is that the claims are the paper's and the
corpus's rather than mine.

**Before:** the backlog named "messaging `amqp://` and Kafka
`security.protocol`" as one blocked item, and no document said which smell was
being detected or on whose authority.

**After:** every row of the taxonomy is traceable to the paper —
Ponce et al. (2022), *Smells and refactorings for microservices security: A
multivocal literature review*, JSS 192:111393,
[10.1016/j.jss.2022.111393](https://doi.org/10.1016/j.jss.2022.111393). Study
counts, refactoring names and refactoring types are the paper's own.

The corpus figures in the plan were measured, not estimated:

```console
$ grep -rln "JmsTemplate" --include="*.java" .        # producers
policy-management-backend/.../RiskManagementMessageProducer.java
policy-management-backend/.../CustomerSelfServiceMessageProducer.java
customer-self-service-backend/.../PolicyManagementMessageProducer.java
(+ 2 MessagingConfiguration, 1 test)

$ grep -rln "@JmsListener" --include="*.java" .       # consumers
policy-management-backend/.../InsuranceQuoteRequestMessageConsumer.java
policy-management-backend/.../CustomerDecisionMessageConsumer.java
customer-self-service-backend/.../InsuranceQuoteExpiredMessageConsumer.java
customer-self-service-backend/.../PolicyCreatedMessageConsumer.java
customer-self-service-backend/.../InsuranceQuoteResponseMessageConsumer.java

$ grep -rn "addConnector" --include="*.java" .        # the broker is embedded
policy-management-backend/.../MessagingConfiguration.java:43: broker.addConnector(stompBrokerBindAddress)
policy-management-backend/.../MessagingConfiguration.java:44: broker.addConnector(tcpBrokerBindAddress)

$ grep -rn "activemq.broker-url" .                    # nothing: clients take the default
```

`stompBrokerBindAddress` and `tcpBrokerBindAddress` resolve to
`stomp://0.0.0.0:61613` and `tcp://0.0.0.0:61616` — both plaintext, where
ActiveMQ TLS would be `ssl://`. A sixth consumer, `risk-management-server`, is
Node and so matches neither Java grep; the plan accounts for it separately.

One correction is recorded in the plan rather than quietly fixed: it first
predicted **3** paired queues and the implementation found **6**. The estimate
came from a grep that matched only the first `@Value` per file. The number in
the document is the measured one.

## Merge Danger

**Door:** two-way. Two new files, plus a table row split and three lines of
`CLAUDE.md`.

**Blast Radius:** none at runtime

No module, test or fixture is touched; `uv run pytest -q` passes unchanged at
150. The only thing that can go wrong is the documentation being wrong, which is
why the taxonomy cites section numbers and the plan cites commands.

One dependency worth stating: `feat/async-communication` implements the plan
this branch contains. Either order merges cleanly — the two touch no common
line of `docs/backlog.md` — but reading this one first is what makes the other
one's design decisions legible.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
