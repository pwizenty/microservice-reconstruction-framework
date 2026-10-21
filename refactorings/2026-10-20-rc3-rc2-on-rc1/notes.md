# Refactoring notes: mutual TLS for the Customer Core and its callers

Resolves the security smell *Non-Secured Service-to-Service Communications*
(Ponce et al. 2022, JSS 192:111393, §3.7) by applying the refactoring the paper
prescribes, **Use Mutual TLS**, to root cause 1 of 2 in this system: the Customer
Core's single plaintext connector and the three services that call it.

Root cause 2, the ActiveMQ broker in the Policy Management Backend, is **not**
touched by the change described in this first section. It is resolved
separately, in [the second section below](#refactoring-notes-mutual-tls-for-the-activemq-broker-and-its-clients).

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
refactoring, **Use Mutual TLS**, for root cause 2 of 2: the ActiveMQ broker
embedded in the Policy Management Backend, which every producer and consumer
reached over a plaintext transport. This cause accounted for 6 of the system's
9 findings, across the six queues `insurance-quote-request-event-queue`,
`customer-decision-event-queue`, `insurance-quote-response-event-queue`,
`insurance-quote-expired-event-queue`, `policy-created-event-queue` and
`newpolicies`.

Nothing belonging to root cause 1 was changed. The Customer Core's connector,
its callers' addresses and their HTTP clients are as the first section
describes them.

## What changed

### The broker: Policy Management Backend

The broker offers two connectors and **both were plaintext**; both are now TLS
with client authentication required. Adding a TLS connector beside a plaintext
one would have changed nothing, because a broker is only as protected as the
least protected transport it accepts.

`policy-management-backend/src/main/resources/application.properties`

```properties
policymanagement.stompBrokerBindAddress=stomp+ssl://0.0.0.0:61613?transport.needClientAuth=true
policymanagement.tcpBrokerBindAddress=ssl://0.0.0.0:61616?transport.needClientAuth=true
```

`needClientAuth=true`, not `wantClientAuth`: for the same reason
`client-auth=need` rather than `want` was chosen for the Customer Core, `want`
serves a client that presents no certificate and so authenticates no peer.

`MessagingConfiguration` builds the broker's `SslContext` from the two stores
and sets it on the `BrokerService` **before** the connectors are added.
`BrokerService.addConnector()` binds the server socket immediately, and the
`ssl://` and `stomp+ssl://` transports take their key and trust material from
the broker's `SslContext` at that moment; setting it afterwards is silently too
late.

### The clients

| Client | Technology | Address | Material |
| --- | --- | --- | --- |
| Customer Self-Service Backend | `ActiveMQSslConnectionFactory` | `policymanagement.tcpBrokerBindAddress=ssl://localhost:61616` | `policymanagement.broker.tls.*` |
| Policy Management Backend | `ActiveMQSslConnectionFactory` | `policymanagement.brokerURL=ssl://localhost:61616` | `policymanagement.broker.tls.*` |
| Risk Management Server | `stompit` over Node's `tls` | `activemq.host`/`activemq.port`, `activemq.ssl=true` | `activemq.caFile`/`keyFile`/`certFile` |

Three points worth noting:

- **The Policy Management Backend is a client of its own broker**, through
  `@JmsListener` on two queues and `JmsTemplate` on the others. It had **no
  broker address at all**: `new ActiveMQConnectionFactory()` fell back to the
  library's plaintext default. A new property, `policymanagement.brokerURL`,
  now addresses the broker explicitly over `ssl://`. The bind address could not
  be reused for this: `0.0.0.0` is not a destination and `needClientAuth` is a
  server-side transport option.
- **The Customer Self-Service Backend reaches the broker through a property
  that reads like server configuration**, `policymanagement.tcpBrokerBindAddress`.
  That is the property whose scheme changed; `spring.activemq.broker-url` is
  not set anywhere in this system.
- **The Risk Management Server holds no `MessageChannel` aspect**, because it is
  a Node service, so no finding pointed at it. It still had to be refactored:
  without `ssl: true` and a client certificate it cannot consume `newpolicies`
  once the broker requires TLS, and the system would clear six findings while
  no longer running.

`risk-management-server/index.js` gained a `brokerConnectOptions()` function
that adds `ssl: true` plus `ca`, `key` and `cert` to the connect options
`stompit` passes through to `tls.connect`. The three paths come from
`config.json` and are resolved against the application directory, so a relative
path works regardless of where `npm start` was run from. `rejectUnauthorized`
is left at its default of `true`; nothing here disables verification.

### Certificates

`generate-certificates.sh` was **extended, not duplicated**. The same
development CA and the same shared trust store now also issue a key store for
`risk-management-server`, and the PEM export that previously ran as a separate
pass after the main loop was moved into it, so each service's own `.key` and
`.crt.pem` land in its `certs/` directory alongside the PKCS#12 stores. Node's
TLS stack cannot read a PKCS#12 store, which is why the Risk Management Server
needs the PEM form; for the Java services the same files are what lets
`openssl s_client` check a handshake.

No new `.gitignore` rule was needed: `certs/` already matches every service's
`certs/` directory at any depth, so the PEM files are excluded along with the
stores.

### Docker Compose

`docker-compose.yml` now passes
`POLICYMANAGEMENT_TCPBROKERBINDADDRESS=ssl://policy-management-backend:61616`
to the Customer Self-Service Backend and mounts
`./risk-management-server/certs` read-only at `/usr/src/app/certs`, which is
that image's `WORKDIR`. The Policy Management Backend's existing `/certs` mount
already covers the broker, because the container's working directory is `/` and
the broker reads `./certs/...`.

### Tests

`RiskManagementMessageProducerTests` spins up its own `BrokerService`. It used
to bind `tcp://localhost:61616`; it now uses the **in-VM transport** and binds
no network connector at all. The producer and the broker live in the same JVM
in that test, so nothing left the process even before, and `vm://` needs no
certificates - which matters twice over, because the Policy Management
Backend's Dockerfile runs `./mvnw -B package` and would otherwise fail to build
on a machine where the stores have not been generated.

No test was disabled, no assertion was weakened, and the test counts are
unchanged.

## What was assumed

- **Property naming.** The broker's and the clients' store properties are
  `policymanagement.broker.tls.*`, following the `customercore.tls.*` naming
  established by root cause 1, so the same environment-variable override
  mechanism works: `POLICYMANAGEMENT_BROKER_TLS_KEYSTORE` and friends.
- **Plain paths, not Spring resource URLs.** Unlike `customercore.tls.*`, these
  properties hold plain filesystem paths such as `./certs/truststore.p12`
  rather than `file:./certs/truststore.p12`. ActiveMQ's
  `ActiveMQSslConnectionFactory` resolves the string itself rather than through
  Spring's `Resource` abstraction, and a plain path is the form it handles
  without ambiguity. The two conventions therefore differ by one prefix; that is
  deliberate and not an oversight.
- **Lazy store loading on the client side.** `ActiveMQSslConnectionFactory`
  takes the store paths and reads them when a connection is first created, not
  when the bean is built. That is what keeps `./mvnw test` green with no
  generated key material present, which matters because the Customer
  Self-Service Backend's `@SpringBootTest` loads the full application context
  and therefore creates the connection factory. A hand-built `SSLContext`, as
  used by the HTTP clients in root cause 1, would have read the stores at bean
  creation and broken that suite. The broker's own `SslContext` is hand-built,
  because an `ssl://` connector needs real key managers at bind time - but no
  test creates the broker bean, so that is safe.
- **`throws Exception` on three bean methods per service.**
  `ActiveMQSslConnectionFactory`'s store setters declare a checked exception, so
  `connectionFactory()` and the two bean methods that call it had to declare one
  too. No behaviour was changed by this; Spring treats a bean method's checked
  exception as a context startup failure, which is the correct outcome if the
  stores are missing.
- **One CA, one trust store, one password.** Unchanged from root cause 1:
  `changeit` throughout, for development-only material that is regenerated
  locally.
- **The in-VM transport for the producer test**, rather than a TLS connector
  that skips itself when the stores are absent. Both were permissible; `vm://`
  was chosen because it removes the dependency on generated material entirely
  instead of making the suite conditional, and because it leaves no plaintext
  broker scheme anywhere in the repository.

## What was verified

Everything below was run in this worktree.

- `bash ./generate-certificates.sh` was executed **as a file** this time, not
  reproduced command by command, and its output is what the checks below used.
  Its idempotence guard was exercised: the existing CA, trust store and four
  service key stores from root cause 1 were reused, and only
  `risk-management-server` was newly issued.
- The Policy Management Backend starts with both connectors as TLS and no
  plaintext connector:
  `Listening for connections at: stomp+ssl://...:61613?transport.needClientAuth=true`
  and `Listening for connections at: ssl://...:61616?transport.needClientAuth=true`.
- A handshake **with** a client certificate succeeds on both ports and the
  broker's certificate verifies against the CA - `Verification: OK`,
  `Verify return code: 0 (ok)`, peer `CN=policy-management-backend`:
  - `openssl s_client -connect localhost:61616 -cert certs/customer-self-service-backend.crt.pem -key certs/customer-self-service-backend.key -CAfile certs/ca.crt`
  - `openssl s_client -connect localhost:61613 -cert certs/risk-management-server.crt.pem -key certs/risk-management-server.key -CAfile certs/ca.crt`
- A handshake **without** a client certificate is rejected on both ports: the
  same commands without `-cert`/`-key` and with `-tls1_2` end in
  `tls alert handshake failure` (alert 40), and the broker logs
  `(handshake_failure) Empty client certificate chain`. Client authentication is
  genuinely required on both connectors, not merely requested.
- **The Policy Management Backend's own JMS client connects over TLS.** Its two
  `@JmsListener` containers started against `ssl://localhost:61616` with no
  `Could not refresh JMS Connection` and no `Setup of JMS message listener
  invoker failed` in the log, which is what a failed connection would have
  produced on every retry.
- **The Customer Self-Service Backend's JMS client connects over TLS.** Started
  against the running broker, it reached `Started CustomerSelfServiceApplication`
  and its three listener containers logged no JMS warning over the following
  half-minute of retry intervals.
- **An end-to-end produce and consume over mutual TLS.** With the Risk
  Management Server running (`Starting to consume PolicyEvent messages from:
  localhost 61613 queueuser (over TLS)`), a message published onto
  `/queue/newpolicies` through the `stomp+ssl` connector with a client
  certificate was received and persisted by it: `An event has been consumed:
  { "probe": "mutual-tls-over-stomp" }`. The publisher was a throwaway script
  outside the repository and is not part of this change.
- **The test suites pass with no generated key material present.** All six
  `certs/` directories were deleted and `./mvnw test` was then run in all four
  Java services, with unchanged counts and nothing skipped: Customer Core 26,
  Policy Management Backend 19, Customer Self-Service Backend 12, Customer
  Management Backend 10.
- `ssl: true` was confirmed against the installed `stompit` 1.0.0 rather than
  assumed: `node_modules/stompit/lib/connect.js` switches from `net.connect` to
  `tls.connect` on exactly that boolean and passes the remaining options
  through.
- The ActiveMQ API used was confirmed against the resolved version, 6.1.3:
  `SslContext.setKeyManagers`/`setTrustManagers`, `BrokerService.setSslContext`
  and the `ActiveMQSslConnectionFactory` store setters all compile and run
  there.

## What could not be verified, and known consequences

- **Docker Compose.** As with root cause 1, the image build and
  `docker-compose up` were not run here, so the new `risk-management-server`
  volume mount and the `ssl://policy-management-backend:61616` address are
  reasoned about rather than observed. The mount target `/usr/src/app/certs`
  follows that image's `WORKDIR`; the Java services' `/certs` target follows
  their lack of one.
- **The Kubernetes manifests now disagree with the application in one more
  place.** `kubernetes/manifests/customer-self-service-backend.yaml` still sets
  `POLICYMANAGEMENT_TCPBROKERBINDADDRESS=tcp://policy-management-backend:61616`,
  and neither `policy-management-backend.yaml` nor `risk-management-server.yaml`
  mounts any certificate material. They were left untouched on purpose, for the
  same reason as before: manifests are not read by the verifying toolchain, so a
  change there could not be shown to work. A Kubernetes deployment needs the
  stores supplied as secrets and that one value changed to `ssl`.
- **Broker authentication is unchanged.** `SimpleAuthenticationPlugin` still
  holds a single hardcoded user, `queueuser`/`secret`, from
  `spring.activemq.user` and `spring.activemq.password`. Mutual TLS now
  authenticates the peer at the transport layer, which arguably makes the shared
  password redundant, but removing it is a different change and was not made.
- **No authorisation policy was added.** Every client that holds a certificate
  from the development CA may produce to and consume from every queue. §3.7 is
  about the channel, not about per-queue authorisation, and ActiveMQ's
  `AuthorizationPlugin` would be a separate refactoring.
- **The `vm://` test fixture no longer exercises a network transport.** The
  producer test previously went through a real socket, if a plaintext one; it
  now stays in the JVM. The assertions are unchanged, but the test covers
  slightly less of the transport stack than it did. A broker-TLS integration
  test that generates material in a temporary directory would cover more; that
  would be a new test rather than a refactoring of an existing one, so it was
  not added.
- **Windows.** Unchanged from root cause 1: `generate-certificates.sh` is a bash
  script and the `.bat` run scripts have no equivalent step.
- **Certificate validity is 365 days** and nothing rotates them. The new
  `risk-management-server` certificate expires a few days after the other four,
  since it was issued later.
