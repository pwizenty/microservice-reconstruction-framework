# Backlog

Work identified but not done, across both repositories of the toolchain:
**MRF** (source code → MongoDB) and **LEMMA**
(`../lemma`, MongoDB → LEMMA models, diagrams).

Each item says what it needs and what it costs, so the list can be ordered by
something other than the order it was written in. Items marked **decision**
need an answer before they can be started; items marked **blocked** cannot be
tested against any system available here.

Last reviewed 2026-10-12.

## Done, for context

So the list below reads as the remainder rather than as the whole picture.

| | |
|---|---|
| Domain, service and operation models | reconstructed end to end, MRF → MongoDB → LEMMA |
| REST technology information | endpoints, verbs, parameter aspects, service aspects |
| Service-to-service dependencies | `required operations` at endpoint level, with a fallback chain |
| Communication transport as a fact | `ServiceCommunicationTransport` on the microservice, ADR-0009 |
| gRPC and Node components | hand-written proto3 parser; Node facts without a JavaScript parser |
| Headless model generation | byte-identical to the wizard |
| Data model diagrams | LEMMA, `de.fhdo.lemma.data.datadsl.diagram`, verified in Eclipse |
| Operation model diagrams | LEMMA, `de.fhdo.lemma.operationdsl.diagram`, verified in Eclipse |
| Server-side communication facts | **A1** below: ports, protocol, TLS, client auth, end to end into a LEMMA aspect |
| Service model diagrams | LEMMA, `de.fhdo.lemma.servicedsl.diagram`, verified in Eclipse |

## A. Security smell: the rest of the facts

The smell is **Non-Secured Service-to-Service Communications**, §3.7 of Ponce
et al. (2022) — see `security-smells.md` for the paper's ten smells, their
refactorings, and what each would need from the reconstruction. The fact list
below comes from Philip's task document rather than from the paper, which is why
some names do not appear there.

One fact is reconstructed today. `s2s-communication-plugin-plan.md` §6 lists the
others; this is them, ordered by what they cost rather than by the task
document's order.

| # | Fact | Needs | Size |
|---|---|---|---|
| ~~A1~~ | ~~Server `port`, `protocol`, `tlsEnabled`, `clientAuth`, `valueSource`~~ | **done.** One `ServerEndpoint` record per connector rather than an `additionalPlaintextPort` field, and a non-single-valued LEMMA aspect so a second connector is representable | — |
| A2 | `clientCertificateConfigured`, `verificationWeakened` | name-based detection of `TrustAllStrategy`, `NoopHostnameVerifier`, `InsecureTrustManagerFactory`; SSL bundle and `SSLContext` analysis | medium |
| A3 | Spring relaxed binding (`CUSTOMERCORE_BASEURL` → `customercore.baseURL`) | an explicit name mapping; only needed once the host matters | small |
| A4 | Mesh `meshType`, `sidecarInjected`, `peerAuthenticationMode`, `destinationRuleTlsMode` | reading `kubernetes/manifests/**`, which MRF does not do at all today | large |
| A5 | Resolved URL and target identity, via Compose `environment`/`env_file`, Kubernetes `env`, ConfigMaps | the operation phase's results — so a fourth phase, or a second method like `assign_deployed_services` | large |
| A6 | One link per profile, with the active one marked | profile-specific files plus `SPRING_PROFILES_ACTIVE` from the deployment | medium |
| A7 | Several evidence records per fact | a nested structure, which `Data.values` cannot hold — **this is where a fourth collection and an ADR become necessary** | large |
| A8a | **Asynchronous links** — JMS/ActiveMQ producers and consumers, the queue and the broker's transport | planned in `async-communication-plan.md`; six messaging interactions in Lakeside Mutual, none reconstructed today | medium |
| A8b | gRPC client calls, Kafka `security.protocol` | further detectors — **blocked**: absent from every sample system available here | medium |

**A1 is done.** It needed no new mechanism, and it completes the client/server
pair of which only the client half existed. **A2 is now the cheapest step**: the
client-certificate and weakened-verification facts, by name-based detection of
`TrustAllStrategy`, `NoopHostnameVerifier` and `InsecureTrustManagerFactory`.

**A8a is now the next step rather than A2**: a detection rule for smell 3.7 has
to see every interaction, and the six messaging links of Lakeside Mutual are
missing from the facts entirely — a false negative in the system the rule is
meant to judge. See `async-communication-plan.md`.

Worth knowing before planning the rest: **neither sample system configures TLS
at all.** Eleven services between Lakeside Mutual and park-and-charge, every one
a plaintext main connector and no management port. So every TLS-positive path is
reachable only through a fixture, and A2's positive cases will be too.

A7 is the one that forces an architectural decision rather than an addition:
the flat `Data.values` is the reason a fact can carry only one piece of
evidence today.

## B. Node plugin, steps 3 and 4

Steps 1 and 2 are done. `node-plugin-plan.md` §8 holds the questions.

| # | Item | Note |
|---|---|---|
| B1 | The frontends | **decision**: reconstruct nothing, or their outgoing calls as `EXTERNAL` facts? Nothing is the honest default; the calls are architecture information no other plugin will see. Points at "nothing", given that frontend UI elements are already kept out of operation models |
| B2 | `risk-management-client` | **decision**: a command line tool, not a service. Nothing, or a `utility` microservice? Recommendation: reconstruct nothing and record why |
| B3 | A JavaScript parser for `createInsecure()` and the subscription | only if B1/A8 need it; behind an ADR |

## C. Operation model diagrams

The third diagram family, in LEMMA: containers, deployment, `default values`.
Unplanned, no questions outstanding, and it would complete the set. Smaller than
the service diagrams were — the operation models are simpler, and the
reader-plus-graph pattern is now proven twice.

Worth knowing before planning it: an operation model's references into service
models are cross-model references, so the same constraint applies — they do not
resolve outside a running Xtext and have to be read from the parse tree. See
`../lemma/docs/service-diagram-plan.md` §3.

## D. Diagram follow-ups

Noticed while building the two diagram bundles; none of them is a defect.

| # | Item | Note |
|---|---|---|
| D1 | Transport security on dependency edges, and `PreAuthorize` on operations | declined deliberately in the interview because the smell work comes later. One annotation each on top of the existing graph, so this is the first thing to pick up once **A** lands |
| D2 | `examples/parking-spaces` draws five microservices side by side at 14.6:1 | inherent to a model that declares five in one file; would need one diagram per microservice, which contradicts one diagram per model |
| D3 | Dependency diagrams are written beside the **first** selected model | arbitrary when selecting across folders; a folder picker or a fixed name would fix it |
| D4 | `PlantUmlRenderer` and `tools/check-bundle-requires.py` are shared by requiring the data diagram bundle | deliberate at two consumers; a third would justify `de.fhdo.lemma.diagram.common` |
| D5 | Parameter aspects (`RequestParam`, `PathVariable`, `RequestBody`, `Valid`) on the interface diagram | declined as the detail most likely to crowd the picture; the graph already carries them |
| D6 | Linking an operation's parameter type to its class in the data model diagram | would mean one picture spanning both model kinds |

## E. Debt and housekeeping

| # | Item | Note |
|---|---|---|
| E1 | MRF known issues | already listed in `CLAUDE.md` under *Known issues*, to be fixed when the area is touched rather than as a campaign. The `sping.py` → `spring.py` rename wants a dedicated commit |
| E2 | Seven ADRs are still *Proposed* | only the maintainer sets *Accepted*. ADR-0002 staying Proposed is why plugin registration is hand-wired in three places |
| E3 | `../lemma/de.fhdo.lemma.servicedsl.extractor` build config contradicts itself | `build.properties` says `output.. = bin/`, the committed `.classpath` says `target/classes`. The local working copy fixes it but also carries m2e entries, which is why it has been kept out of commits. Wants the output-folder change alone, in its own commit |
| E4 | `temp.txt` in the LEMMA working copy | pre-existing, untracked |
| ~~E5~~ | ~~**Lakeside Mutual cannot be built as a container system**~~ | **done, 2026-10-14.** Its Dockerfiles named `openjdk:21-slim-buster`, withdrawn from Docker Hub, so the system could not be built patched or unpatched. Fixed in the sample's own repository on `fix/container-base-images`: the five Java services build on `eclipse-temurin:21-jdk` and run on `:21-jre`, neither of which sets a `WORKDIR`, so the `file:./certs/...` paths of the mutual-TLS work still resolve. The *system starts* gate now runs, and a refactoring reached **VERIFIED** |

## What this list does not contain

Publication and evaluation work: which systems to reconstruct for the thesis,
what to measure, and what to compare against. That is not derivable from the
code and belongs with the author.
