# Refactoring notes: mutual TLS for the ActiveMQ broker

Resolves the security smell *Non-Secured Service-to-Service Communications*
(Ponce et al. 2022, §3.7) for root cause 2 of 2: the ActiveMQ broker hosted by
the Policy Management backend was reached over plaintext transports by every
service that produces to or consumes from it. Six of the system's nine findings,
across the six queues `insurance-quote-request-event-queue`,
`customer-decision-event-queue`, `insurance-quote-response-event-queue`,
`insurance-quote-expired-event-queue`, `policy-created-event-queue` and
`newpolicies`, shared this one cause.

The refactoring the paper prescribes is **Use Mutual TLS**, so both ends of
every channel now authenticate each other with a certificate.

The REST calls to the Customer Core are root cause 1 and are deliberately
untouched here.

## What changed

### Development key material (new)

- `generate-certificates.sh` — creates a throwaway CA, one shared trust store
  holding only the CA certificate, and one PKCS#12 key store plus PEM key/cert
  pair per participating service, into `certs/`. Idempotent; re-running keeps
  existing material. Needs `openssl` and `keytool`.
- `.gitignore` — `certs/` is ignored. The script is source, its output is not.

Certificates carry `subjectAltName` entries for the docker-compose service
name, the short service name, `localhost` and `127.0.0.1`, because peers
address each other by service name under Docker and by `localhost` on a local
run. `extendedKeyUsage` carries both `serverAuth` and `clientAuth`, since under
mutual TLS every service is both.

### The broker — `policy-management-backend`

- `src/main/resources/application.properties`
  - `policymanagement.stompBrokerBindAddress`:
    `stomp://0.0.0.0:61613` → `stomp+ssl://0.0.0.0:61613?transport.needClientAuth=true`
  - `policymanagement.tcpBrokerBindAddress`:
    `tcp://0.0.0.0:61616` → `ssl://0.0.0.0:61616?transport.needClientAuth=true`
  - new `policymanagement.brokerURL=ssl://localhost:61616` — the address this
    service uses to reach *its own* broker as a client (see below).
  - new `policymanagement.ssl.{keyStore,keyStorePassword,trustStore,trustStorePassword}`.
- `.../interfaces/configuration/MessagingConfiguration.java`
  - the broker gets an `SslContext` built from the key and trust store before
    its connectors are added.
  - the connection factory is now an `ActiveMQSslConnectionFactory`, configured
    with the stores and with an explicit broker URL.

Both connectors were plaintext and both were converted. **No plaintext
connector remains**: there is no `tcp://` or `stomp://` address left anywhere in
the broker's configuration, so the least-protected connector the broker offers
is a TLS one.

`transport.needClientAuth=true` (not `wantClientAuth`) is what makes this mutual
rather than plain TLS: the broker refuses a client that presents no certificate.

### The Java clients

`policy-management-backend` is a client of its own broker as well as its host:
its `connectionFactory()` bean previously set no broker URL at all and so fell
back to ActiveMQ's default of `tcp://localhost:61616`. It now connects
explicitly over `ssl://localhost:61616` with its own key store.

`customer-self-service-backend`:

- `src/main/resources/application.properties`
  - `policymanagement.tcpBrokerBindAddress`:
    `tcp://localhost:61616` → `ssl://localhost:61616`
  - new `customerselfservice.ssl.{keyStore,keyStorePassword,trustStore,trustStorePassword}`.
- `.../interfaces/configuration/MessagingConfiguration.java` — the connection
  factory is now an `ActiveMQSslConnectionFactory` configured with the stores.
  Three bean methods gained a `throws Exception` clause, because
  `ActiveMQSslConnectionFactory`'s store setters declare one.

### The Node consumer — `risk-management-server`

This service holds no `MessageChannel` aspect and contributed no finding of its
own, but it consumes `newpolicies` over STOMP and would not have been able to
reach the broker after the conversion.

- `config.json` — new `cafile`, `keyfile`, `certfile` entries.
- `index.js` — the `stompit` connect options gained `ssl: true` (which makes
  `stompit` connect through Node's `tls` module instead of `net`), plus `ca`,
  `key` and `cert`. `rejectUnauthorized` is left at its secure default.
  Relative paths are resolved against the service's own directory, so the
  behaviour does not depend on the working directory.

### `docker-compose.yml`

- `POLICYMANAGEMENT_TCPBROKERBINDADDRESS` for the Customer Self-Service backend:
  `tcp://policy-management-backend:61616` → `ssl://policy-management-backend:61616`.
- The three participating services mount `./certs` read-only at `/certs` and get
  environment overrides pointing at that path, because the certificates are
  generated on the host and the images are built without them.

### Documentation

`README.md`, `policy-management-backend/README.md`,
`customer-self-service-backend/README.md` and
`risk-management-server/README.md` gained a sentence each pointing at
`generate-certificates.sh`, because the messaging no longer works on a fresh
clone until it has been run once.

### Tests

`policy-management-backend`'s `RiskManagementMessageProducerTests` started a
fixture broker on `tcp://localhost:61616`. That fixture now uses the **in-VM
transport** (`vm://...?create=false`) instead: the broker is named, kept
non-persistent, and reached without opening a network socket at all.

No test is disabled and no assertion was weakened — both tests still send
events through a real broker and assert on what comes back. The reason for
`vm://` rather than `ssl://` is the clean-checkout requirement below: a fixture
on `ssl://` would need key material that the repository does not and must not
carry. An in-VM transport is not a network channel, so it is not an instance of
the smell either.

## Verification

- `policy-management-backend`: `./mvnw test` → 19 tests, BUILD SUCCESS.
- `customer-self-service-backend`: `./mvnw test` → 12 tests, BUILD SUCCESS.
- Both suites were re-run with `certs/` moved out of the way, to reproduce a
  clean checkout of this patch with no generated key material present. Both
  still pass. This works because every client hands its stores to ActiveMQ as
  *paths*, which are only opened when a connection is actually established, so
  a context that starts without a reachable broker never touches a store.
- The broker was started with `./mvnw spring-boot:run` and logged both
  connectors as `stomp+ssl://...:61613?transport.needClientAuth=true` and
  `ssl://...:61616?transport.needClientAuth=true`.
- `openssl s_client` against both ports, presenting a client certificate,
  completes the handshake with `Verify return code: 0` and shows the broker
  asking for a certificate (`Acceptable client certificate CA names`).
- The same connection *without* a client certificate is rejected: the broker
  logs `Empty client certificate chain` and sends a `certificate_required`
  alert. Client authentication is therefore required, not merely requested —
  this is mutual TLS and not plain TLS.
- With the broker running, `customer-self-service-backend` and the broker's own
  host were started and neither logged a single `Could not refresh JMS
  Connection`, so both Java clients established their mutually authenticated
  connections.
- `risk-management-server` was started with `npm start` and subscribed without a
  connection error. A frame sent to `/queue/newpolicies` over STOMP+TLS with a
  client certificate was logged by it as `An event has been consumed`, so the
  Node consumer's end of the channel works in both directions.

## Assumptions

- **A throwaway CA is the right answer for a sample system.** The script says so
  in its header. One CA, one trust store, one key store per service.
- **Store password `changeit`** for all development material, in the properties
  files next to the already-present development credentials (`spring.activemq.password=secret`,
  the hardcoded API keys). This is consistent with how the sample system already
  handles development secrets; it is not a pattern for production.
- **`policymanagement.tcpBrokerBindAddress` kept its name** in both services even
  though it now holds an `ssl://` address. Renaming it would have broken the
  existing `POLICYMANAGEMENT_TCPBROKERBINDADDRESS` environment override and the
  Kubernetes manifest that sets it, for no functional gain.
- **Certificate paths default to `../certs/...`**, which is correct for the
  documented way of running the services (each from its own subdirectory, as
  `run_all_applications.sh` does). Docker overrides them by environment.
- **The Policy Management backend reaches its own broker over the network**
  (`ssl://localhost:61616`) rather than in-VM. Keeping it on a real TLS
  connection means its own six producer and consumer channels are protected by
  the same mechanism as everybody else's, which is what the smell is about.

## Not verified / out of scope

- **The Kubernetes manifests under `kubernetes/` were not changed.** They still
  set `POLICYMANAGEMENT_TCPBROKERBINDADDRESS=tcp://...` and
  `ACTIVEMQ_PORT=61613` without TLS material, so a Kubernetes deployment needs a
  matching change (a secret holding the stores, mounted into the pods, and the
  `ssl://` address). This was left out deliberately: the refactoring had to be
  expressed in application configuration and code to be verifiable here.
- **`docker-compose up` was not run.** The three services were verified running
  locally against `localhost`, which exercises the same configuration, but the
  containerised path — the `./certs` bind mounts and the environment overrides
  that go with them, and the certificates' `policy-management-backend`
  `subjectAltName` — was not executed.
- **No business event was pushed through the whole chain.** The queue was
  exercised with a synthetic frame rather than by creating a policy through the
  Policy Management REST API, which would also have needed the Customer Core
  and so the still-plaintext root cause 1.
- **The frontends and the Risk Management client are unaffected** — they do not
  talk to the broker.
