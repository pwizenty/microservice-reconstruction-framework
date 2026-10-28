# What is new against the predecessor work, measured

The paper extends Wizenty et al. (2024), and a reviewer is entitled to ask what
exactly is new. This file holds the measured answer, so the paper can state it
in three sentences and point here.

## The one-sentence delta

**The reconstruction was reimplemented from scratch as the Microservice
Reconstruction Framework (MRF), so that communication security becomes a
reconstructed fact rather than an assumption — and so that the technologies a
real system actually uses are covered rather than one of them.**

Everything below is evidence for that sentence.

## Why a reimplementation was necessary, not a preference

The predecessor workflow reconstructs architecture, validates models, refactors
*models*, and reflects the result into implementation artifacts. For security
smell §3.7 that is not enough in a specific, checkable way: the smell is decided
by **how two services talk**, and that information was not in the models. A
model that records services, interfaces and operations but not the scheme of a
call, the connectors a callee offers, or the transport of a queue cannot decide
this smell at all — not badly, but not at all.

The Node service of Lakeside Mutual is the proof, and it happened inside this
work: its two communication facts were reconstructed but not declared in the
technology model, so the generator dropped them. The models looked complete, the
detection reported nine findings, and **two channels went unjudged without
anything saying so**. Declaring the two aspects raised the baseline to eleven
and made the residue of the guided sequence visible. A fact that is not
reconstructed and declared is not a weak signal; it is silence.

## What MRF is, in numbers

| | |
|---|---|
| Implementation | 58 Python modules, 7 512 lines, under `mrf/` |
| Tests | 12 files, 1 778 lines, golden fixtures per plugin |
| Phases | domain data → services → operation, orchestrated by `ReconstructionHandler` |
| Plugins | Java, Spring, Protobuf (data and service), Node, Docker, Communication |
| Persistence | MongoDB, three collections (ADR-0004, ADR-0008) |
| Architecture decisions | ten ADRs, all Accepted |

The communication layer alone — the part that exists for this smell — is
**2 048 lines**: `server.py` for the connectors a service offers, `urls.py` for
address resolution, and four detectors (`feign.py`, `rest_template.py`,
`jms.py`, and the registry in `detector.py`).

## The technologies, and why each was needed

Not a list of features: each one is a channel of the sample system that would
otherwise be invisible.

| Technology | What it contributes | How it is read |
|---|---|---|
| Java | domain data from JPA entities | ljavalang, a fork for Java 9-22 including records (ADR-0003, ADR-0006) |
| Spring | services, REST interfaces, operations, endpoints | the same parser plus `application.properties` |
| Communication | the smell's evidence: outgoing calls, their scheme and client library, the connectors a service offers, the queues it produces to and consumes from | Feign and `RestTemplate` call sites, JMS producers and listeners, connector properties |
| Protobuf | a gRPC contract: messages into the domain phase, service and rpcs into the service phase | a hand-written proto3 parser, `proto_utils.py` |
| Node | what a Node service serves and the transport of its channels | `package.json`, `config.json`, and the sources read **by API name** — no JavaScript parser, so ADR-0003 stays intact |
| Docker | the deployment: containers, `depends_on`, operation nodes | `docker-compose.yml` and Dockerfiles (ADR-0008) |

Seven kinds of artifact in three languages produce the facts the rule reads:
Java annotations and client code, `application.properties`, Compose files and
Dockerfiles, `.proto`, `package.json`, `config.json`, `index.js`.

## The facts, and the design decision behind them

Seven technology aspects carry the smell's evidence. The technology model
declares 65 aspects in total; these are the ones the validation reads:

| Aspect | What it states |
|---|---|
| `ServiceCall` | target, target kind, scheme, client library |
| `ServiceCallEndpoint` | the operation called, its verb and path |
| `ServiceCommunicationTransport` | the transport of a service's outgoing calls |
| `ServerEndpoint` | one record per connector: port, protocol, `tlsEnabled`, `clientAuth` |
| `MessageChannel` | queue, role, broker, scheme, transport |
| `GrpcServer` | host, port, `transportSecurity`, `clientAuth` |
| `MessageQueue` | broker, queue, scheme, credentials, `transportSecurity` |

`clientAuth` is the one that earns its place: §3.7's refactoring is *mutual*
TLS, so a TLS connector without required client authentication is a weaker
result than the paper prescribes, and only a reconstructed `clientAuth` lets a
rule tell the two apart.

**ADR-0009 is the decision that makes this clean**: MRF reconstructs facts and
never a verdict. There is no field called `insecure` and no severity anywhere in
the reconstruction. The smell is decided on the LEMMA side, by a rule over the
generated models. That separation is what allows the same facts to serve a
second smell without touching the reconstruction, and it is also why the
detector could be extended to the Node channels without regenerating anything.

## The LEMMA side

| Bundle | Size | What it adds |
|---|---|---|
| `de.fhdo.lemma.reconstruction` | 37 files, 4 141 lines | reading the database into LEMMA models, headless and byte-identical to the wizard |
| `de.fhdo.lemma.servicedsl.smells.validation` | 4 files, 740 lines | `ChannelVerdict`, the rule; `RootCause`, the grouping key |
| `de.fhdo.lemma.servicedsl.smells` | 20 files, 3 593 lines | detection, report, request assembly, patch guard, proposal records, the four gates |

## Resolution: the second half of the delta

The predecessor refactored **models** and generated new code from them. It could
not change code that already exists, and mutual TLS is exactly that kind of
change: it means editing connectors and clients that are already implemented.

Here the implementation artifacts change and the models are never edited — the
architecture is reconstructed **again** from the modified implementation, which
is what makes the result measurable rather than asserted. ADR-0010 states the
condition under which an AI is admitted into the toolchain at all: what it
produces is measured, not trusted.

## Ready to paste

For §I, as the third contribution:

> We reimplement architecture reconstruction as the Microservice Reconstruction
> Framework, so that the information this smell is decided from — outgoing calls
> and their scheme, the connectors a service offers with their TLS and
> client-authentication settings, and the queues it produces to and consumes
> from — is reconstructed rather than assumed, across Java, Spring, Protobuf,
> Node and Docker artifacts. The reconstruction reports facts only; the smell is
> decided by a rule over the generated models.

For §V, replacing the delta sentence:

> We extend that workflow on both sides. Its reconstruction did not carry
> communication information, so §3.7 could not be decided from its models at
> all; ours recovers caller, endpoint and messaging facts from seven kinds of
> artifact in three languages, and declares them as technology aspects a
> validation rule reads. Its resolution generated new source code and left
> existing code untouched, which places mutual TLS out of reach, since securing
> a channel means changing connectors and clients that already exist. Here the
> implementation changes and the models do not: the architecture is
> reconstructed again from the modified system, so the effect of a change is
> measured rather than assumed.

*AI-drafted (Claude Opus 5) from measurements in this repository; cover it in
the AI-use acknowledgment.*
