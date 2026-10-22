# Microservices security smells

Reference for the security work of the toolchain, taken from

> Francisco Ponce, Jacopo Soldani, Hernán Astudillo, Antonio Brogi:
> **Smells and refactorings for microservices security: A multivocal
> literature review.** *The Journal of Systems & Software* 192 (2022) 111393.
> <https://doi.org/10.1016/j.jss.2022.111393>
> Replication package: <https://github.com/ms-security/smells-replication-package>

A multivocal literature review over **58 primary studies**, white and grey.
Section 3 of the paper defines ten smells; this file records them, the
refactorings the paper suggests, and what each would need from the
reconstruction.

**This file is reference, not a plan.** What the toolchain reconstructs today is
in `backlog.md` section A, and the fact set there came from Philip's own task
document rather than from this paper — which is why some of its names, such as
`additionalPlaintextPort`, do not appear here.

## Where a smell is decided

ADR-0009 puts the split between the two steps:

| | |
|---|---|
| **MRF** collects facts | a port, a scheme, a `clientAuth` value, an aspect in the sources |
| **LEMMA** decides the smell | a validation over the generated models |

So nothing in this file is something MRF should report as a finding. A
reconstructed field named `insecure`, or a severity, would move the decision
into the wrong step.

## The taxonomy

The paper groups the smells by the security properties of **ISO/IEC 25010**.
Only three of that standard's five properties correspond to any identified
smell:

- **Confidentiality** — data are accessible only to those authorized
- **Integrity** — unauthorized modification of programs or data is prevented
- **Authenticity** — the identity of a subject or resource can be proved to be
  the one claimed

| § | Smell | C | I | A | Suggested refactoring | Refactoring type | Studies |
|---|---|---|---|---|---|---|---|
| 3.1 | Insufficient access control | ● | | | Use OAuth 2.0 | Design pattern implementation | 25 |
| 3.2 | Publicly accessible microservices | ● | | | Add an API Gateway | Design pattern implementation | 25 |
| 3.3 | Unnecessary privileges to microservices | ● | ● | | Follow the Least Privilege Principle | Use of established security protocols | 12 |
| 3.4 | Own crypto code | ● | ● | ● | Use Established Encryption Technologies | Use of established security libraries | 9 |
| 3.5 | Non-encrypted data exposure | ● | ● | ● | Encrypt all Sensitive Data at Rest | Data encryption | 12 |
| 3.6 | Hardcoded secrets | ● | ● | ● | Encrypt Secrets at Rest | Use of established security libraries | 8 |
| 3.7 | **Non-secured service-to-service communications** | ● | ● | ● | **Use Mutual TLS** | Data encryption | **32** |
| 3.8 | Unauthenticated traffic | | | ● | Use Mutual TLS **and** Use OpenID Connect | Use of established security protocols | 14 |
| 3.9 | Multiple user authentication | | | ● | Use a Single Sign-On | Design pattern implementation | 21 |
| 3.10 | Centralized authorization | | | ● | Use Decentralized Authorization | Design pattern implementation | 19 |

"Studies" is how many of the 58 discuss the smell, as the section text states it.

Two structural points of the taxonomy, both from §3:

- **A refactoring can serve several smells.** `Add an API Gateway` serves 3.2
  and 3.9; `Use OpenID Connect` serves 3.8 and 3.9; `Use Mutual TLS` serves 3.7
  and 3.8. The paper prefers mutual TLS for 3.7 *because* it also mitigates 3.8.
- **Where a smell lists several refactorings, all of them apply.** The paper is
  explicit: "the refactorings associated to a smell should all be applied to
  mitigate its effects". So 3.8 needs mutual TLS *and* OpenID Connect, and 3.9's
  single sign-on is itself `Add an API Gateway` plus `Use OpenID Connect`.

**Interaction-related smells dominate the literature.** The paper observes that
"the more a security smell is related to service interactions, the higher is its
coverage", and 3.7 has the broadest support of all ten.

## 3.7 Non-secured service-to-service communications

The smell the toolchain addresses first. Quoted, because one clause of it
decides whether the reconstructed facts are evidence or false positives:

> This smell occurs whenever two microservices in an application interact
> without enacting a secure communication channel, **even if they are within the
> same network**.

Lakeside Mutual's services talk over plaintext inside a Docker network. By this
definition that still counts, so the facts the reconstruction reports for it are
evidence rather than noise.

Why the paper's refactoring is *mutual* TLS rather than TLS:

> when Mutual TLS is used to secure communications between two microservices,
> each microservice can legitimately identify the microservice it is talking to,
> which means that microservices can authenticate each other

Hence the distinction matters to the reconstruction: a TLS connector mitigates
the confidentiality and integrity half, and only `clientAuth = need` evidences
the authentication half. `ServerEndpoint.clientAuth` carries exactly that.

### What the toolchain already has for it

| Half of the smell | Fact | Where from |
|---|---|---|
| What a client calls, and with which scheme | `ServiceCall`, `ServiceCallEndpoint`, `ServiceCommunicationTransport` | `service/communication/detectors/` |
| What the callee accepts | `ServerEndpoint` — `port`, `protocol`, `tlsEnabled`, `clientAuth`, per connector | `service/communication/server.py` |
| What a Node service serves, and how it binds it | `GrpcServer` — `host`, `port`, `transportSecurity`, `clientAuth` | `service/node/`, the transport by name from the sources (`javascript.py`) |
| The leg a Node service holds to a broker | `MessageQueue` — `broker`, `queue`, `scheme`, `credentialsConfigured`, `transportSecurity` | the same |

All of them appear on the microservice in a generated service model. **An aspect
the technology model does not declare is dropped**, silently and by design: a
reference that does not resolve is worse than a visible gap. The two Node facts
were reconstructed and dropped exactly that way until 2026-10-21, and Lakeside
Mutual's Risk Management server stood in the models with no communication fact
at all — so the detection reported nine findings and said nothing about the two
channels it had not looked at. A fact is only evidence once both steps carry it.

### What it does not have

- **Mesh facts.** The paper's smell is not present where a service mesh secures
  the channel. Backlog A4; needs reading `kubernetes/manifests/**`, which MRF
  does not do at all.
- **Resolved target identity.** Which concrete service a call reaches, through
  the deployment's environment. Backlog A5.
- **Client certificates and weakened verification** on the Java side. Backlog
  A2. A Node service's are read: `createSsl` against a CA, and the third
  argument that makes a client certificate required.
- **The client half of a gRPC channel.** Backlog A8b. The server half is read;
  the only caller in this sample is a command line tool that the deployment does
  not contain, and B2 reconstructs nothing for it.
- **Several pieces of evidence per fact.** Backlog A7, and the one that needs an
  ADR: `Data.values` is flat, so a fact carries one piece of evidence.

### Where its view ends

Counting services with no communication fact catches a service that was
reconstructed and left without one. It does not catch a client with no service
model at all, and Lakeside Mutual has two: the monitoring server, skipped as
infrastructure, and an NGINX load-balancing demonstration, which MRF does not
read. Both are real clients of the Customer Core's connector. The detection
therefore also compares the operation model against the service models and
reports every deployment node that deploys no reconstructed microservice as a
*potential unmodelled client* - not as a finding, because nothing there says
such a node communicates at all.

A channel with only one reconstructed end is the harder case, because nothing
reports it in either direction: the monitoring server has no service model, so
breaking its relationship produces no finding and repairing it produces none
either. `monitoring-regression.md` records that case end to end.

**Measured, and it bounds what any detection can be tested against:** neither
sample system configures TLS anywhere. Eleven services across Lakeside Mutual
and park-and-charge, every one a plaintext main connector, no management port.
So a detection rule's *positive* case — a system that does not smell — is
reachable only through a fixture.

## What the other nine would need

Judgements about this toolchain, not claims from the paper.

| § | Reconstructable from today's facts? |
|---|---|
| 3.7 | **Yes.** Both halves are there |
| 3.8 Unauthenticated traffic | Partly. Mutual TLS evidence exists via `clientAuth`; OpenID Connect is not reconstructed |
| 3.6 Hardcoded secrets | Plausibly. The configuration reader already sees property values, and the paper's smell includes credentials in source and repositories |
| 3.2 Publicly accessible microservices | Plausibly. Operation nodes, ports and the API gateway are reconstructed; "publicly accessible" needs the deployment's exposure, which is A5's territory |
| 3.1 Insufficient access control | A start exists: `PreAuthorize` is detected as an operation aspect |
| 3.10 Centralized authorization | A start exists, same aspect; "centralized" needs where authorization is enforced, not only that it is |
| 3.3 Unnecessary privileges | No. Needs the privileges a service is granted — IAM, Kubernetes RBAC, database grants |
| 3.4 Own crypto code | No. Needs recognising cryptographic implementations in source |
| 3.5 Non-encrypted data exposure | No. Needs storage configuration and what is deemed sensitive |
| 3.9 Multiple user authentication | No. Needs where user authentication happens across services |
