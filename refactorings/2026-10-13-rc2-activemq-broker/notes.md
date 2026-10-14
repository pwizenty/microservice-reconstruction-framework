# Refactoring: Use Mutual TLS on the ActiveMQ channels

Resolves the security smell *Non-Secured Service-to-Service Communications*
(Ponce et al. 2022, §3.7) for root cause 2 of 2: the ActiveMQ broker embedded in
the Policy Management backend was reached over plaintext by every service that
produces to or consumes from it. One root cause, six queues, six findings:
`insurance-quote-request-event-queue`, `customer-decision-event-queue`,
`insurance-quote-response-event-queue`, `insurance-quote-expired-event-queue`,
`policy-created-event-queue` and `newpolicies`.

The REST calls to the Customer Core (root cause 1) are deliberately **not**
touched here.

## Before you run anything

The certificates are development key material and are not committed. Generate
them once, from the repository root:

```bash
./generate_certificates.sh
```

This is required before `./mvnw test` in `policy-management-backend` as well,
because its producer test now starts a TLS broker.

## What changed

### The broker (`policy-management-backend`)

- `src/main/resources/application.properties` - both connectors converted, no
  plaintext connector left:
  - `policymanagement.stompBrokerBindAddress`: `stomp://0.0.0.0:61613` →
    `stomp+ssl://0.0.0.0:61613?transport.needClientAuth=true`
  - `policymanagement.tcpBrokerBindAddress`: `tcp://0.0.0.0:61616` →
    `ssl://0.0.0.0:61616?transport.needClientAuth=true`
  - new `policymanagement.brokerClientURL=ssl://localhost:61616`, the address
    this service uses as a client of its own broker (the old code relied on
    `ActiveMQConnectionFactory`'s default URL, which is plaintext
    `tcp://localhost:61616`)
  - new `messaging.ssl.*` properties naming the key store, the trust store and
    their passwords
- `interfaces/configuration/MessagingSslContextFactory.java` (new) - builds the
  broker's `org.apache.activemq.broker.SslContext` from the PKCS#12 key and
  trust stores.
- `interfaces/configuration/MessagingConfiguration.java` - sets that SSL context
  on the `BrokerService` before the connectors are added, and turns the
  `connectionFactory` bean into an `ActiveMQSslConnectionFactory` that addresses
  `policymanagement.brokerClientURL` with its own key and trust store.

`transport.needClientAuth=true` is what makes this *mutual* TLS rather than
plain TLS: the broker demands a certificate from every client.
`wantClientAuth` would not be enough.

### The Java clients

- `policy-management-backend` is a client of its own broker (it consumes
  `insurance-quote-request-event-queue` and `customer-decision-event-queue` and
  produces to the rest), so the change above covers both roles.
- `customer-self-service-backend/src/main/resources/application.properties` -
  `policymanagement.tcpBrokerBindAddress`: `tcp://localhost:61616` →
  `ssl://localhost:61616`, plus the same `messaging.ssl.*` properties. The
  property name is unchanged although it no longer mentions TCP, because it is
  the address the reconstruction resolves the channel from.
- `customer-self-service-backend/.../interfaces/configuration/MessagingConfiguration.java` -
  `ActiveMQConnectionFactory` → `ActiveMQSslConnectionFactory` with key and
  trust store. The bean's declared type stays `ActiveMQConnectionFactory`
  (`ActiveMQSslConnectionFactory` is a subclass), so no other code changed.

`ActiveMQSslConnectionFactory.setKeyStore`/`setTrustStore` declare
`throws Exception`, which is why the surrounding `@Bean` methods now declare it
too. That is the only reason their signatures changed.

### The Node consumer (`risk-management-server`)

It holds no `MessageChannel` aspect and contributed no finding, but it consumes
`newpolicies` and would have stopped working the moment the broker required TLS.

- `config.json` - the `activemq` block gained `ssl`, `caFile`, `keyFile` and
  `certFile`.
- `index.js` - when `ssl` is set, the `stompit` connect options carry
  `ssl: true` (which makes `stompit` connect through Node's `tls` module) plus
  `ca`, `key` and `cert`. Paths are resolved against the service's own
  directory. `rejectUnauthorized` is left at its default, so the broker's
  certificate is verified.

### Certificates

- `generate_certificates.sh` (new) - creates a throwaway CA, one shared trust
  store, and one PKCS#12 key store per service, plus PEM exports for the Node
  client. Idempotent; `--force` regenerates. Development only, and the script
  says so.
- `.gitignore` - `certs/` added. The script is committed, the key material is
  not.

### Deployment configuration

- `docker-compose.yml` - the Customer Self-Service backend's
  `POLICYMANAGEMENT_TCPBROKERBINDADDRESS` now uses `ssl://`, and the three
  affected services mount `./certs` read-only at the path their relative
  configuration resolves to.

## What was verified

- `policy-management-backend`: `./mvnw -o test` → 19 tests, 0 failures. The log
  shows `Connector ssl://localhost:61616?transport.needClientAuth=true started`,
  so `RiskManagementMessageProducerTests` now produces and consumes over a real
  mutual-TLS handshake rather than plaintext. No test was disabled and no
  assertion weakened; only the test broker's bind address, client URL and key
  material were updated.
- `customer-self-service-backend`: `./mvnw -o test` → 12 tests, 0 failures.
- The application started with `./mvnw spring-boot:run` and logged both
  connectors as `stomp+ssl://…:61613?transport.needClientAuth=true` and
  `ssl://…:61616?transport.needClientAuth=true`. No plaintext connector appears.
  Its own JMS listeners attached with no `Could not refresh JMS Connection`
  error, i.e. the service reached its own broker over TLS.
- `risk-management-server`: `node index.js` against that broker connected and
  subscribed with no connection error, i.e. the STOMP client's mutual TLS was
  accepted.
- `openssl s_client` against both ports: the broker presents
  `CN=policy-management-backend`, sends a certificate request
  (`Acceptable client certificate CA names`) and the handshake returns
  `Verify return code: 0`. Connecting *without* a client certificate is refused
  with `tlsv13 alert certificate required`, which is the direct evidence that
  client authentication is required and not merely wanted.

## Assumptions

- **One development CA, one shared trust store.** Every service trusts the same
  CA; each has its own key store. Adequate for a sample system, not a production
  PKI story.
- **Password `changeit` for every store, kept in `application.properties`
  alongside the existing `spring.activemq.password=secret` and
  `apikey.value=…`.** This matches how the repository already handles
  development secrets; it is wrong for production, and the properties are
  overridable by environment variable.
- **Certificate subjects are the docker-compose service names, with
  `localhost` and `127.0.0.1` as subject alternative names.** Host name
  verification then holds both when services are started individually on
  localhost and when they address each other by service name under Docker
  Compose.
- **Store paths are relative (`../certs/…`), resolved against each service's own
  directory.** That is the repository-root `certs/` directory for a local run
  and the mounted volume under Docker Compose.
- **No failover wrapper on the client URLs.** `failover:(ssl://…)` would have
  kept the old default's reconnect behaviour, but it changes the scheme the
  reconstruction reads. Spring's listener containers recover on their own, so
  the plain `ssl://` form was chosen.
- **The Kubernetes manifests under `kubernetes/` were left alone** on purpose:
  this refactoring is application-level configuration and code only.

## Not verified

- **Docker Compose was not run.** The image builds were not exercised, so the
  mount paths (`/certs` for the two Java services, `/usr/src/certs` for the Node
  service) are reasoned from each image's working directory rather than
  observed. The local runs above all passed.
- **No end-to-end business flow was driven through the broker** (creating a
  policy in the Policy Management backend and seeing the Risk Management server
  persist the event), because that also needs the Customer Core and the
  frontends. What was observed is that every participant connects, subscribes
  and - in the producer test - round-trips a message over the TLS transport.
- **Certificate expiry is 365 days** and there is no renewal path. Re-run
  `./generate_certificates.sh --force` when the development certificates expire.
