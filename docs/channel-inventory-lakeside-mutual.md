# Channel inventory: Lakeside Mutual at `622632f`

What this system's components say to each other, enumerated **by hand from the
sources and the deployment**, without consulting the reconstruction, and only
then compared against it.

It exists because the detection cannot answer the question a reviewer keeps
asking: *how much of the system does it see?* Counting services that carry no
communication fact catches a service that was read and left without one; it
cannot catch a client that has no service model at all. This table can.

**Method.** Read `docker-compose.yml`, every service's configuration, and the
code that opens a connection. Record source, target, protocol, port and the
file and line that evidences it. Classify each path, with a reason. Compare
against the generated models afterwards, not before.

**Scope.** The deployment the paper evaluates: the nine services of
`docker-compose.yml` at `622632f`, unpatched. Two further deployment
descriptions of the same system exist and are listed separately, because a path
that only exists in one of them is not a path of the evaluated system.

**What "in scope" means.** §3.7 of Ponce et al. (2022) is about two
microservices of one application interacting. A browser reaching a published
port is a client of the system, not a second microservice of it, so those paths
are recorded and excluded with that reason rather than quietly dropped.

**Methodological limit, and it has to be stated wherever this table is used.**
If the reconstruction is later improved against this table, the table stops
being an independent reference and becomes development data. It was built
before any such improvement and is unchanged since.

## In scope: service to service, in the evaluated deployment

| # | From | To | Protocol | Evidence | Reconstructed | Judged |
|---|---|---|---|---|---|---|
| 1 | customer-management-backend | customer-core :8110 | HTTP, Feign | `…/CustomerCoreClient.java:20`, `application.properties:26`, `docker-compose.yml:45` | yes | finding |
| 2 | policy-management-backend | customer-core :8110 | HTTP, RestTemplate | `…/CustomerCoreRemoteProxy.java:29`, `application.properties:40`, `docker-compose.yml:68` | yes | finding |
| 3 | customer-self-service-backend | customer-core :8110 | HTTP, RestTemplate | `…/CustomerCoreRemoteProxy.java:27`, `application.properties:45`, `docker-compose.yml:92` | yes | finding |
| 4 | customer-self-service-backend | policy-management-backend, queue `insurance-quote-request-event-queue` | JMS over OpenWire :61616 | `PolicyManagementMessageProducer.java:27`, `InsuranceQuoteRequestMessageConsumer.java:35` | yes | finding |
| 5 | customer-self-service-backend | policy-management-backend, queue `customer-decision-event-queue` | JMS over OpenWire :61616 | `PolicyManagementMessageProducer.java:30`, `CustomerDecisionMessageConsumer.java:62` | yes | finding |
| 6 | policy-management-backend | customer-self-service-backend, queue `insurance-quote-response-event-queue` | JMS over OpenWire :61616 | `CustomerSelfServiceMessageProducer.java:25`, `InsuranceQuoteResponseMessageConsumer.java:31` | yes | finding |
| 7 | policy-management-backend | customer-self-service-backend, queue `insurance-quote-expired-event-queue` | JMS over OpenWire :61616 | `CustomerSelfServiceMessageProducer.java:28`, `InsuranceQuoteExpiredMessageConsumer.java:28` | yes | finding |
| 8 | policy-management-backend | customer-self-service-backend, queue `policy-created-event-queue` | JMS over OpenWire :61616 | `CustomerSelfServiceMessageProducer.java:31`, `PolicyCreatedMessageConsumer.java:28` | yes | finding |
| 9 | policy-management-backend | risk-management-server, queue `newpolicies` | JMS in, STOMP out :61613 | `RiskManagementMessageProducer.java:20,40`; `risk-management-server/index.js:76`; `docker-compose.yml:118` | yes | **two** findings: the producer's channel and the consumer's leg, because the two ends use different connectors |
| 10 | risk-management-client | risk-management-server :50051 | gRPC | `risk-management-server/index.js:146,148`; `risk-management-client/index.js:31` | the endpoint, yes; the caller, no | finding, caller reported as unidentified |
| 11 | spring-boot-admin ↔ customer-core | :9000 and :8110 | HTTP, registration and actuator scrape | `docker-compose.yml:35`, `customer-core/…/application.properties:30` | **no** | **not judged** |
| 12 | spring-boot-admin ↔ customer-management-backend | the same | the same | `docker-compose.yml:46`, `…/application.properties:27` | **no** | **not judged** |
| 13 | spring-boot-admin ↔ policy-management-backend | the same | the same | `docker-compose.yml:69`, `…/application.properties:41` | **no** | **not judged** |
| 14 | spring-boot-admin ↔ customer-self-service-backend | the same | the same | `docker-compose.yml:94`, `…/application.properties:46` | **no** | **not judged** |

**Fourteen in-scope channels. Ten are reconstructed and carry eleven findings**
— row 9 contributes two, because a queue reached over two connectors needs two
patches. **Four are not reconstructed, and all four are the monitoring
channels**: MRF skips `spring-boot-admin` as infrastructure
(`INFRASTRUCTURE_TECHNOLOGIES`), so it has no service model, and a service with
no model cannot be the end of a judged channel.

Every one of the fourteen is plaintext at `622632f`.

## Recorded and excluded, with the reason

| Path | Why it is not a §3.7 channel |
|---|---|
| browser → customer-self-service-backend :8080, policy-management-backend :8090, customer-management-backend :8100 | the frontends serve static files only (`*/nginx.vh.default.conf`) and the browser addresses published ports; the client is a user agent, not a second microservice |
| browser → the three frontends :3000, :3010, :3020, and → spring-boot-admin :9000 | the same |
| each Spring service → its own H2 database | `jdbc:h2:file:` in each `application.properties`: a file, in process, not a network channel |

## In other deployment descriptions of the same system

Not part of the evaluated deployment, and this is why the reconstruction does
not carry them. They are listed because a patch may still have to change them,
and because one of them is where a proposal found work the models never named.

| Path | Where | Note |
|---|---|---|
| nginx proxy :80 → four customer-core replicas :8110, plaintext `proxy_pass` | `customer-core/nginx-loadbalancing/docker-compose.yml`, `…/nginx/*.conf` | a load-balancing demonstration with its own compose file. `abl-f`, given the sources rather than the models, found and secured it |
| the Kubernetes variant | `kubernetes/docker-compose.yml`, `kubernetes/manifests/*.yaml` | plaintext endpoints; MRF reads no manifests at all (backlog A4), and no proposal was allowed to change them |

## What this answers

- **Which relevant paths are missing?** The four monitoring channels, entirely.
  Within the ten that are carried, no end is missing.
- **Which omissions therefore reach the repair request?** All four. A request
  for `endpoint:CustomerCore` names three callers; the Customer Core's
  connector has a fourth client, the monitoring server, and nothing in the
  models says so. That is why `rc1` broke the scrape and had to declare it,
  and why `abl-f`, reading the sources, secured it instead.
- **Which changes can the detector not see?** Any change to rows 11-14 and to
  the other deployment descriptions. Both the breakage under `rc1` and the
  repair under `abl-f` are invisible to the finding count: both runs measure
  11 → 8.
- **Do the same paths survive a patch, or only the same number of facts?** The
  paper's "20 facts before and after" shows that nothing stopped being
  reconstructed. It does not show that the fourteen channels still work. Rows
  1-3 and 9 are exercised by the runtime probes; rows 4-8 are covered at
  connector level; rows 11-14 are exercised only by the start gate, which is
  how `rc1`'s loss was found; row 10's caller is not deployed and is exercised
  by nothing.

## Coverage, stated as the paper should state it

> Of fourteen service-to-service channels in the evaluated deployment, the
> reconstruction carries ten, and those ten produce the eleven findings. The
> four it does not carry are the monitoring channels, which share the Customer
> Core's connector; a repair of that connector therefore affects a client the
> models do not name.
