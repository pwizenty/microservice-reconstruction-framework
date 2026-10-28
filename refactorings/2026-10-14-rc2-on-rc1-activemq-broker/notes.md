# Refactoring notes: mutual TLS for the Customer Core and its callers

Resolves the security smell *Non-Secured Service-to-Service Communications*
(Ponce et al. 2022, JSS 192:111393, §3.7) by applying the refactoring the paper
prescribes, **Use Mutual TLS**, to root cause 1 of 2 in this system: the Customer
Core's single plaintext connector and the three services that call it.

Root cause 2, the ActiveMQ broker in the Policy Management Backend, is **not**
touched here. `policymanagement.stompBrokerBindAddress` and
`policymanagement.tcpBrokerBindAddress` are deliberately left on `stomp://` and
`tcp://`, and so is the Customer Self-Service Backend's copy of the latter.

## What changed

### The server: Customer Core

`customer-core/src/main/resources/application.properties`

The connector on port 8110 is now HTTPS with client authentication required.
The port is unchanged, so no caller address and no deployment descriptor had to
move for that reason alone.

```properties
server.ssl.enabled=true
server.ssl.key-store=file:./certs/customer-core.p12
server.ssl.key-store-password=changeit
server.ssl.key-store-type=PKCS12
server.ssl.key-alias=customer-core
server.ssl.trust-store=file:./certs/truststore.p12
server.ssl.trust-store-password=changeit
server.ssl.trust-store-type=PKCS12
server.ssl.client-auth=need
```

`client-auth=need`, not `want`: `want` asks for a certificate and then serves
the request without one, which secures the channel but authenticates no peer —
a weaker refactoring than §3.7 cites.

### The three callers

All three now address the Customer Core over `https` and present a client
certificate. Each needed two changes, the address and the HTTP client.

| Service | Technology | Address | Client |
| --- | --- | --- | --- |
| Customer Management Backend | Feign | `customercore.baseURL=https://localhost:8110` | `feign.Client` bean in `CustomerCoreClientConfiguration` |
| Customer Self-Service Backend | RestTemplate | `customercore.baseURL=https://localhost:8110` | request factory in `DefaultAuthenticatedRestTemplateClient` |
| Policy Management Backend | RestTemplate | `customercore.baseURL=https://localhost:8110` | request factory in `DefaultAuthenticatedRestTemplateClient` |

Each caller reads its own key store and the shared trust store from four new
properties, `customercore.tls.keyStore`, `customercore.tls.keyStorePassword`,
`customercore.tls.trustStore` and `customercore.tls.trustStorePassword` (plus
optional `...Type` properties defaulting to `PKCS12`). They follow the naming of
the existing `customercore.baseURL`, so the existing environment-variable
override mechanism works unchanged: `CUSTOMERCORE_TLS_KEYSTORE` and friends.

`customer-self-service-backend/src/test/resources/application-test.properties`
carries its own copy of `customercore.baseURL` and was moved to `https` as well.
No test was disabled and no assertion was weakened.

### Certificates

`generate-certificates.sh` (new) creates one development CA, one shared trust
store holding only the CA certificate, and one key store per service. Each
certificate carries the service name, `localhost` and `127.0.0.1` as subject
alternative names, so the same material works whether the services are started
individually or under Docker Compose, where peers address each other by service
name.

The script is committed; its output is not. `certs/`, `*.p12`, `*.jks` and
`*.csr` were added to `.gitignore`, because the CA private key is created by the
script and anybody holding it can mint a certificate every service accepts.

The two `run_all_applications*.sh` scripts now invoke it (it is idempotent, so a
second run reuses an existing set), and the README, the Customer Core README and
the FAQ were updated.

### Docker Compose

`docker-compose.yml` now passes `https://customer-core:8110` to the three callers
and mounts each service's own `certs/` directory read-only at `/certs`. The
containers' working directory is `/`, so the `file:./certs/...` paths in
`application.properties` resolve to the mounted directory without an override.

## What was assumed

- **Store location.** Every service reads `file:./certs/...`, relative to its
  own working directory, which is the service directory both for
  `mvn spring-boot:run` and for the `run_all_applications` scripts. The script
  therefore writes a copy of each service's own material into
  `<service>/certs/` in addition to the repository-root `certs/`. Only the root
  `certs/` holds the CA private key; the per-service copies do not.
- **One CA, one trust store.** A single trust store holding the CA certificate
  is used by both ends and in both directions.
- **Password.** `changeit` throughout, in the properties and in the script.
  Acceptable for development-only material that is regenerated locally; not a
  secret worth managing for a sample system.
- **Client HTTP stack.** No new dependency was added to any service. The two
  RestTemplate callers use `JdkClientHttpRequestFactory` over the JDK's
  `java.net.http.HttpClient`, which takes an `SSLContext` directly and verifies
  the server hostname by default. The Feign caller uses `feign.Client.Default`
  with an `SSLSocketFactory` from the same `SSLContext` and the JDK's **default**
  hostname verifier, which is the strict one. Nothing disables verification:
  there is no `TrustAllStrategy`, no `NoopHostnameVerifier`, no
  `InsecureTrustManagerFactory`.
- **The `SSLContext` is built by hand** from the two stores rather than from a
  Spring `spring.ssl.bundle`. A bundle would be more idiomatic on Boot 3.3, but
  bundles are registered from properties at context refresh for every profile,
  whereas the client beans live in `@Profile("default")` configuration classes.
  Building the context inside those beans keeps `./mvnw test` working without
  any generated key material present, which is what the existing
  `@SpringBootTest` suites rely on. The server side uses the classic
  `server.ssl.*` form for the same reason: Tomcat loads the stores when the
  connector starts, and the test suites run with a mock web environment.

## What was verified

Everything below was run in this worktree.

- `./mvnw test` passes in all four affected services, unchanged test counts:
  Customer Core 26, Policy Management Backend 19, Customer Self-Service Backend
  12, Customer Management Backend 10. No failures, no errors, nothing skipped.
- The Customer Core starts with `Tomcat initialized with port 8110 (https)`.
- A handshake **with** a client certificate succeeds and the server certificate
  verifies against the CA:
  `openssl s_client -connect localhost:8110 -cert certs/policy-management-backend.crt.pem -key certs/policy-management-backend.key -CAfile certs/ca.crt -brief`
  → `Verification: OK`, peer `CN=customer-core`.
- A handshake **without** a client certificate is rejected by the server:
  the same command without `-cert`/`-key` and with `-tls1_2` ends in
  `tls alert handshake failure` (alert 40). Client authentication is therefore
  genuinely required, not merely requested.
- All three callers were started against the running Customer Core and each
  returned real data fetched over mutual TLS:
  - `GET http://localhost:8090/customers?filter=&limit=2&offset=0` → 200, customer list (Policy Management Backend, RestTemplate)
  - `GET http://localhost:8100/customers?filter=&limit=2&offset=0` → 200, customer list (Customer Management Backend, Feign)
  - `GET http://localhost:8080/cities/6500` → 200, `{"cities":["Bellinzona"]}` (Customer Self-Service Backend, RestTemplate)

## What could not be verified, and known consequences

- **`generate-certificates.sh` was not executed as a file.** This environment
  does not permit running a script, so every `keytool` and `openssl` invocation
  in it was instead executed individually, in the script's order and with the
  script's arguments; the material under `certs/` and in each service's `certs/`
  directory is the result, and it is what the live handshake checks below used.
  The script's control flow — the `--force` branch, the `if [ ! -f ... ]` guards
  that make it idempotent, and `cd "$(dirname "$0")"` — has therefore been read
  but not run. It is also committed without the executable bit, because `chmod`
  was unavailable; that is why the run scripts and the documentation invoke it as
  `bash ./generate-certificates.sh`, which works either way.
- **Docker Compose.** The image build and `docker-compose up` were not run here,
  so the volume mounts and the `https://customer-core:8110` addresses are
  reasoned about rather than observed. The `file:./certs/...` paths depend on the
  container's working directory being `/`, which is what the Dockerfiles imply
  (no `WORKDIR`, jar copied to `.`) but was not executed.
- **The Kubernetes manifests now disagree with the application.**
  `kubernetes/manifests/{customer-management,customer-self-service,policy-management}-backend.yaml`
  still set `CUSTOMERCORE_BASEURL=http://customer-core:8110`, and no manifest
  mounts the stores. They were left untouched on purpose: manifests are outside
  the scope of this change and are not read by the verifying toolchain, so a
  change there could not be shown to work. A Kubernetes deployment needs the
  stores supplied as secrets and those three values changed to `https`.
- **Spring Boot Admin can no longer scrape the Customer Core.** The Customer
  Core registers itself with the admin server and the admin server then polls
  its actuator endpoints. Those endpoints are now behind mutual TLS, and the
  admin server presents no client certificate, so the Customer Core will show as
  down in the admin UI. That monitoring channel is not part of this root cause
  and fixing it would mean configuring the admin server's reactive web client,
  so it was left alone. The registration call in the other direction
  (`spring.boot.admin.client.url`) is still plain HTTP and is likewise untouched.
- **Windows.** `generate-certificates.sh` is a bash script. The repository's
  `run_all_applications.bat` and `run_customer_management_applications.bat` have
  no equivalent step, so a Windows developer has to run the script under a bash
  shell before using them.
- **Browser access to the Customer Core.** Swagger UI and the H2 console on port
  8110 now require a client certificate installed in the browser. The READMEs
  say so, but this is a real loss of convenience for a teaching sample.
- **Stale example URLs in Javadoc.** The request and response samples in
  `customer-core/.../CustomerInformationHolder.java` and
  `APIKeyAuthenticationManager.java`, the `soap:address` in
  `customer-core/src/main/resources/countries.wsdl`, and the demo link in
  `CustomerCoreFrontEndView.html` still read `http://localhost:8110`. They are
  illustrative text, not configuration, and were left as they were to keep the
  change reviewable.
- **Certificate validity is 365 days.** Nothing rotates them; a developer with a
  year-old checkout has to run the script again with `--force`.

---

# Refactoring notes: mutual TLS for the ActiveMQ broker and its clients

Resolves the same security smell, *Non-Secured Service-to-Service
Communications* (Ponce et al. 2022, JSS 192:111393, §3.7), with the same
prescribed refactoring, **Use Mutual TLS**, applied to root cause 2 of 2: the
ActiveMQ broker hosted by the Policy Management Backend, and every service that
produces to or consumes from it. This cause accounted for 6 of the system's 9
original findings, one per producer channel, across six queues:
`insurance-quote-request-event-queue`, `customer-decision-event-queue`,
`insurance-quote-response-event-queue`, `insurance-quote-expired-event-queue`,
`policy-created-event-queue` and `newpolicies`.

> The root-cause-1 section above says the broker is "not touched here" and that
> `policymanagement.stompBrokerBindAddress` and
> `policymanagement.tcpBrokerBindAddress` are "deliberately left on `stomp://`
> and `tcp://`". That was true when it was written and is no longer true. The
> paragraph was left exactly as it stands, because it is the record of the
> earlier step; the schemes below supersede it.

## What changed

### The broker: Policy Management Backend

`policy-management-backend/src/main/resources/application.properties`

Both connectors are now TLS and both require a client certificate. No plaintext
connector remains, on either protocol. The ports are unchanged.

```properties
policymanagement.stompBrokerBindAddress=stomp+ssl://0.0.0.0:61613?transport.needClientAuth=true
policymanagement.tcpBrokerBindAddress=ssl://0.0.0.0:61616?transport.needClientAuth=true
policymanagement.brokerURL=ssl://localhost:61616
```

`transport.needClientAuth=true`, not `wantClientAuth`: the latter asks for a
certificate and then serves the connection without one. Password
authentication through the existing `SimpleAuthenticationPlugin` is unchanged
and still in place, so the broker now authenticates its peers twice over —
which matters here, because the queue user's password is in this very file.

`policymanagement.brokerURL` is new. It exists because a client cannot connect
to the `0.0.0.0` wildcard the broker binds: it has to name a host that appears
in the broker certificate's subject alternative names, which the ActiveMQ
client then verifies. Previously the in-process clients used
`ActiveMQConnectionFactory`'s default URL, which is plaintext
`tcp://localhost:61616`.

`.../interfaces/configuration/MessagingConfiguration.java`

- The two stores are read once in a `@PostConstruct` method into a
  `KeyManager[]` and a `TrustManager[]`.
- `broker.setSslContext(new SslContext(keyManagers, trustManagers, null))` is
  called **before** `addConnector`. That ordering is load-bearing:
  `BrokerService.addConnector` binds the server socket there and then, and
  ActiveMQ's TLS transport factory reads the broker's SSL context at that
  moment. Setting it afterwards would leave both connectors on the JVM's
  default stores, which hold none of this system's material.
- `connectionFactory()` now returns an `ActiveMQSslConnectionFactory` pointed at
  `policymanagement.brokerURL`, with the same key and trust managers handed to
  it. This service is a client of its own broker — four producers and two
  consumers — so it presents a certificate like every other client.

### The clients

| Service | Protocol | Address | Client |
| --- | --- | --- | --- |
| Policy Management Backend | OpenWire | `policymanagement.brokerURL=ssl://localhost:61616` | `ActiveMQSslConnectionFactory` with key and trust managers, `MessagingConfiguration` |
| Customer Self-Service Backend | OpenWire | `policymanagement.tcpBrokerBindAddress=ssl://localhost:61616` | `ActiveMQSslConnectionFactory` with store locations, `MessagingConfiguration` |
| Risk Management Server | STOMP | `activemq.host`/`activemq.port` in `config.json`, `ssl: true` | `stompit` over `tls.connect`, `index.js` |

Both Java clients read six new properties, `activemq.tls.keyStore`,
`activemq.tls.keyStorePassword`, `activemq.tls.trustStore`,
`activemq.tls.trustStorePassword` and the two optional `...Type` properties
defaulting to `PKCS12`. They follow the naming that root cause 1 established for
`customercore.tls.*`, so the environment-variable override mechanism works
unchanged: `ACTIVEMQ_TLS_KEYSTORE` and friends.

The Risk Management Server is the seventh participant and carries no channel
aspect in the reconstructed models, because it is a Node service rather than a
Java one. It is refactored all the same: without it the system would not run
once the broker required TLS. Its `connectOptions` now carry `ssl: true` plus
`ca`, `cert` and `key`, which `stompit` passes straight through to
`tls.connect`. The paths are configured under `activemq` in `config.json` and
resolved relative to the application directory, so the service can be started
from anywhere. Node verifies the broker's certificate chain against `ca` and
its host name against the certificate's subject alternative names; both checks
are on by default and are deliberately left that way. Nothing sets
`rejectUnauthorized: false`.

### Certificates

`generate-certificates.sh` was **extended**, not duplicated. There is still one
CA, one shared trust store and one key store per peer.

- `risk-management-server` was added to `SERVICES`, so it gets a CA-signed key
  pair with the same `eku=serverAuth,clientAuth` as everyone else.
- The PEM export, which previously ran only if `openssl` happened to be
  installed, is now unconditional and `openssl` is checked for up front with a
  clear error. Node reads PEM, not PKCS#12, so it is no longer optional.
- The per-service copy step now writes `ca.crt`, `<service>.crt.pem` and
  `<service>.key` into `risk-management-server/certs/`, and the PKCS#12 stores
  into the Java services' `certs/` directories as before.
- The closing hint now also shows the two `openssl s_client` commands for the
  broker's connectors.

No `.gitignore` rule was added: the existing `certs/` entry already covers
`risk-management-server/certs/`, and the PEM files live inside it.

### Docker Compose

- `POLICYMANAGEMENT_TCPBROKERBINDADDRESS` for the Customer Self-Service Backend
  moved from `tcp://policy-management-backend:61616` to
  `ssl://policy-management-backend:61616`.
- `risk-management-server` gained a read-only mount of its own `certs/`
  directory at `/usr/src/app/certs`, which is where its `WORKDIR` and therefore
  `config.json`'s relative paths resolve.
- `policy-management-backend` already mounted its `certs/` directory for root
  cause 1; the same mount is now also the broker's server material, which the
  comment there records. Nothing else about it changed.
- `risk-management-server/.dockerignore` is new. That service's Dockerfile does
  `COPY . ./`, which would otherwise bake the generated private key into the
  image; the compose mount supplies it at run time instead.

### The test that touched the broker

`RiskManagementMessageProducerTests` ran its own `BrokerService` on
`tcp://localhost:61616`. It now runs it on ActiveMQ's in-VM transport
(`vm://risk-management-message-producer-tests?create=false&waitForStart=10000`)
and adds no network connector at all. Both assertions, both test methods and
the test's `RiskManagementMessageProducer` wiring are untouched; only the
transport the embedded broker is reached over changed. See the assumption below
for why it is `vm://` rather than `ssl://`.

### Documentation

The root `README.md` (setup step and port table), the Policy Management Backend
README and the Risk Management Server README now say that the broker is mutual
TLS and that `generate-certificates.sh` has to be run first.
`run_all_applications.sh` already invoked the script for root cause 1; its
comment was widened.

## What was assumed

- **The property name `policymanagement.tcpBrokerBindAddress` was kept**, even
  though it now holds an `ssl://` URL in both services that read it. Renaming it
  would be cleaner, but the Kubernetes manifests inject it by that name and
  manifests are out of scope and must not be edited here, so a rename would
  silently drop the override and leave a Kubernetes deployment pointing at
  `localhost`. Keeping the name leaves the manifests merely wrong about the
  scheme instead of wrong about the host as well. The `stompBrokerBindAddress`
  name was kept for symmetry.
- **The Policy Management Backend loads its stores eagerly, the Customer
  Self-Service Backend lazily.** This asymmetry is deliberate and is a property
  of the two roles. A server needs its private key when it binds, so the broker
  side has to read the stores at startup — and failing fast there is the right
  behaviour, because a broker nobody can reach is worse than a service that
  refuses to start. A client only needs its key when it connects, so the
  Customer Self-Service Backend hands ActiveMQ the store *locations* and lets it
  read them on first connect. That keeps its `@SpringBootTest` suite
  constructible with no key material present, which is the same constraint root
  cause 1 solved with `@Profile("default")` on the RestTemplate client.
- **The in-JVM test broker uses `vm://`, not `ssl://`.** Binding `ssl://` in
  `RiskManagementMessageProducerTests` would make the test depend on
  `generate-certificates.sh` having been run, and that material is generated
  rather than committed, so it is absent on a clean checkout. `vm://` is the
  honest alternative rather than a loophole: it is a direct call into the
  in-process broker, so there is no socket and therefore no plaintext channel to
  secure. `create=false` is set so the test fails if the broker bean did not
  start, instead of quietly connecting to a second, empty broker that the
  transport would otherwise create on the spot.
- **`openssl` is now a hard requirement** of
  `generate-certificates.sh`. It was already used opportunistically; the Node
  peer makes it mandatory.
- **Password.** `changeit` throughout, as for root cause 1.
- **Certificate identity is not mapped to a broker user.** The broker still
  authorises by the `spring.activemq.user`/`password` pair through
  `SimpleAuthenticationPlugin`; it does not derive the ActiveMQ user from the
  client certificate's distinguished name. Doing that would mean swapping in
  `JaasCertificateAuthenticationPlugin` and a certificate-to-group mapping,
  which is an authorisation change rather than a transport one and so is outside
  this cause. Mutual TLS is nevertheless genuine: the broker rejects the
  connection before any STOMP or OpenWire frame is read.
- **`setTrustAllPackages(true)`** was left as it was on both connection
  factories. It is a deserialisation setting, unrelated to the transport, and
  changing it would alter behaviour this refactoring is not about.

## What was verified

Everything below was run in this worktree.

- `./mvnw test` passes in all four Java services, from a deleted `target/` and
  with **no** generated key material present anywhere in the tree. Unchanged
  test counts: Customer Core 26, Policy Management Backend 19, Customer
  Self-Service Backend 12, Customer Management Backend 10. No failures, no
  errors, nothing skipped. `git status --ignored` confirms no `certs/`
  directory and no `*.p12`, `*.key` or `*.crt.pem` file existed during that run.
- `bash ./generate-certificates.sh` was executed as a file, from a tree with no
  previous material, and produced the CA, the shared trust store, five key
  stores and the PEM material. `git status` shows none of it, so `.gitignore`
  covers the new Node PEM files as intended.
- The Policy Management Backend starts and logs both connectors as TLS:
  `Listening for connections at: stomp+ssl://…:61613?transport.needClientAuth=true`
  and `Listening for connections at: ssl://…:61616?transport.needClientAuth=true`.
  No plaintext connector appears in the log.
- A handshake **with** a client certificate succeeds on both connectors and the
  broker certificate verifies against the CA:
  `openssl s_client -connect localhost:61616 -cert certs/customer-self-service-backend.crt.pem -key certs/customer-self-service-backend.key -CAfile certs/ca.crt -verify_hostname localhost`
  → `Verify return code: 0 (ok)`, peer `CN=policy-management-backend`, and the
  server sends `Acceptable client certificate CA names`. The same holds on
  61613 with the Risk Management Server's material.
- A handshake **without** a client certificate is rejected by the broker, which
  logs `Transport Connection to: tcp://127.0.0.1:… failed: (certificate_required)
  Empty client certificate chain`. Client authentication is therefore genuinely
  required, not merely requested.
- All three clients connected to the running broker over TLS, with the socket
  counts matching the channels exactly: the Policy Management Backend 2
  (its two consumers), the Customer Self-Service Backend 3 (its three
  consumers) on 61616, and the Risk Management Server 1 on 61613 — confirmed
  with `lsof -nP -iTCP:61616 -sTCP:ESTABLISHED` and the same for 61613. No
  `Could not refresh JMS Connection` or retry warning appears in either Spring
  log.
- A message published to `/queue/newpolicies` over mutual TLS STOMP was consumed
  by the Risk Management Server over mutual TLS STOMP and persisted: its log
  shows `An event has been consumed:` followed by the event body. The throwaway
  publisher script used for this was deleted again.
- `node --check risk-management-server/index.js`, `require()` of
  `risk-management-server/config.json` and `bash -n generate-certificates.sh`
  all pass.
- A repository-wide search finds no remaining `tcp://` or `stomp://` broker
  address in any application property, source file or compose file. The three
  remaining matches are this document's root-cause-1 paragraph, an explanatory
  code comment, and the Kubernetes manifest described below.

## What could not be verified, and known consequences

- **The Kubernetes manifests now disagree with the application, again.**
  `kubernetes/manifests/customer-self-service-backend.yaml` still sets
  `POLICYMANAGEMENT_TCPBROKERBINDADDRESS=tcp://policy-management-backend:61616`,
  `risk-management-server.yaml` still points at plain STOMP on 61613, and no
  manifest mounts the stores. They were left untouched on purpose, for the same
  reason as in root cause 1: manifests are outside the scope of this change and
  are not read by the verifying toolchain, so a change there could not be shown
  to work. A Kubernetes deployment needs the stores supplied as secrets, that
  value changed to `ssl://`, and the PEM material mounted into the Risk
  Management Server.
- **Docker Compose was not run.** The image builds and `docker-compose up` were
  not executed here, so the new `risk-management-server` mount, the
  `.dockerignore` and the `ssl://policy-management-backend:61616` address are
  reasoned about rather than observed. The broker certificate's subject
  alternative names do include the Docker Compose service name
  `policy-management-backend`, which is what that address needs.
- **The `ACTIVEMQ_CA`, `ACTIVEMQ_CERT` and `ACTIVEMQ_KEY` overrides were not
  exercised.** The README mentions them because they go through exactly the
  same `nconf` environment mapping as the existing `ACTIVEMQ_HOST` and
  `ACTIVEMQ_PORT` that Docker Compose already relies on, but this environment
  would not let an inline environment variable be set for a single command, so
  only the `config.json` defaults were observed resolving.
- **Windows.** As for root cause 1, `generate-certificates.sh` is a bash script
  and `run_all_applications.bat` has no equivalent step, so a Windows developer
  has to run it under a bash shell first. The Risk Management Server now fails
  with a readable message naming the missing path rather than a bare TLS error,
  which at least makes that mistake obvious.
- **The frontends are unaffected**, which was established by reading rather than
  running them. `customer-self-service-frontend` and
  `customer-management-frontend` use `react-stomp`, but against the backends'
  own `/ws` SockJS endpoint, not against ActiveMQ. Those channels belong to
  neither root cause and were not touched.
- **Certificate validity is 365 days**, and nothing rotates them. Unchanged from
  root cause 1, and it now applies to one more peer.
