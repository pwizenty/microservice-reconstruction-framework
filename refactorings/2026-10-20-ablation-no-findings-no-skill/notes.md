# Refactoring notes: mutual TLS for the service-to-service channels

This change secures every channel between two Lakeside Mutual services with mutual
TLS (mTLS). Both ends of every channel were changed together: each service presents a
client certificate and each service verifies its peer against a private certificate
authority, the *Lakeside Mutual Internal CA*.

Everything was done at the application level — application configuration, application
code and `docker-compose.yml`. No Kubernetes manifest and no service mesh is involved.

## The channels that were secured

| Channel | Transport before | Transport after | Server end | Client end |
| ------- | ---------------- | --------------- | ---------- | ---------- |
| Customer data | `http://…:8110` | `https://…:8110`, `client-auth=need` | `customer-core` | `customer-self-service-backend`, `customer-management-backend`, `policy-management-backend` |
| Insurance quote events | `tcp://…:61616` | `ssl://…:61616?needClientAuth=true` | `policy-management-backend` (ActiveMQ broker) | `customer-self-service-backend`, `policy-management-backend` |
| Policy events | `stomp://…:61613` | `stomp+ssl://…:61613?needClientAuth=true` | `policy-management-backend` (ActiveMQ broker) | `risk-management-server` |
| Customer data report | plaintext gRPC `:50051` | gRPC over TLS `:50051`, client certificate required | `risk-management-server` | `risk-management-client` |

The port numbers are unchanged, only the transport on them changed. mTLS was added
*next to* the authentication that was already in place (API keys, JWT tokens, the
broker's username/password); nothing was removed.

## What changed, file by file

### Key material

- **`scripts/generate-certificates.sh`** (new). Creates the Lakeside Mutual Internal CA
  and one key pair per service. Every service certificate carries `serverAuth` and
  `clientAuth` extended key usages — most services act in both roles — and its subject
  alternative names are the service's docker-compose hostname, `localhost` and
  `127.0.0.1`, so that hostname verification succeeds both inside Docker and when the
  services are started individually. It writes PKCS#12 keystores/truststores for the Java
  services and PEM files for the Node.js services, directly into the location each
  service reads from.
- **`.gitignore`**. Ignores `certs/`, which covers the CA directory at the repository
  root and every per-service `certs` directory. No generated key material is committed;
  only the script is.

### Customer Core (server end of the HTTP channel)

- **`customer-core/src/main/resources/application.properties`**. `server.ssl.*` with
  `client-auth=need`, `TLSv1.3`/`TLSv1.2`, and the PKCS#12 keystore and truststore read
  from the classpath.
- **`customer-core/src/test/resources/application-test.properties`**.
  `server.ssl.enabled=false` — the tests drive the resource API through `MockMvc` rather
  than a socket, so no embedded connector and no key material is involved.

### The three callers of the Customer Core (client end of the HTTP channel)

- **`…/infrastructure/MutualTlsContext.java`** (new, one per backend). Loads the
  service's own keystore and the CA truststore from the classpath and turns them into
  `KeyManager[]`, `TrustManager[]` and an `SSLContext`. Loading happens on demand, not in
  the constructor. It lives in the `infrastructure` package so that the `interfaces`
  layer may depend on it without breaking the ArchUnit layering rules.
- **`…/interfaces/configuration/DefaultAuthenticatedRestTemplateClient.java`** (all three
  backends). The `RestTemplate` now uses a `JdkClientHttpRequestFactory` over a
  `java.net.http.HttpClient` configured with that `SSLContext`. The JDK HTTP client
  performs certificate-chain *and* hostname verification by default.
- **`customer-management-backend/…/infrastructure/CustomerCoreClientConfiguration.java`**.
  This backend reaches the Customer Core through OpenFeign, not through the
  `RestTemplate`, so it also gets a `feign.Client` that uses the same `SSLContext` and the
  JDK's standard hostname verifier.
- The `customercore.baseURL` properties changed from `http://` to `https://`, in the
  three `application.properties` files, in `customer-self-service-backend`'s
  `application-test.properties`, and in `docker-compose.yml`.

### ActiveMQ broker (both ends)

- **`policy-management-backend/…/interfaces/configuration/MessagingConfiguration.java`**.
  The broker gets an `org.apache.activemq.broker.SslContext` built from the service's key
  material *before* its connectors are added, and both connectors are now SSL transports
  that require client authentication. The backend is also a client of its own broker, so
  its connection factory became an `ActiveMQSslConnectionFactory` pointing at
  `ssl://localhost:61616`.
- **`customer-self-service-backend/…/interfaces/configuration/MessagingConfiguration.java`**.
  The connection factory became an `ActiveMQSslConnectionFactory` with the service's
  keystore and the CA truststore.
- **`risk-management-server/index.js`** and **`config.json`**. The STOMP connection now
  passes `ssl: true` plus the key, certificate and CA through to `tls.connect`, which
  verifies the broker's certificate and hostname (Node's `rejectUnauthorized` and
  `checkServerIdentity` defaults are left untouched).
- The bind addresses are configured in `policy-management-backend`'s
  `application.properties`; the client-side broker URLs carry
  `?socket.verifyHostName=true` so that the broker's hostname is verified too.

### gRPC (both ends)

- **`risk-management-server/index.js`**. `grpc.ServerCredentials.createSsl(ca,
  [keyCertPair], true)` — the third argument makes the server require and verify a client
  certificate.
- **`risk-management-client/index.js`** and **`config.json`**.
  `grpc.credentials.createSsl(ca, key, cert)`.

### The Customer Core's NGINX load balancing demo

`customer-core/nginx-loadbalancing` is a self-contained demo that puts four Customer
Core instances behind an NGINX reverse proxy. Since the Customer Core now requires a
client certificate, that proxy is a client of a mutual-TLS channel too, so it was
changed along with it rather than left talking plaintext to a TLS server:

- **`nginx/nginx.conf`**. `proxy_pass https://app_servers` plus `proxy_ssl_certificate`,
  `proxy_ssl_certificate_key`, `proxy_ssl_trusted_certificate` and `proxy_ssl_verify on`.
  The upstreams are addressed by container name, which is not in the Customer Core's
  certificate, so `proxy_ssl_name customer-core` states the name to verify explicitly —
  verification stays on rather than being switched off.
- **`nginx/Dockerfile`** copies the generated `certs` directory into the image, and the
  generation script now issues an `nginx-loadbalancing` certificate into it.
- The hop from the browser to NGINX (port 80) stays plain HTTP; that is the demo's
  user-facing edge, not a service-to-service channel.

### Documentation

- `README.md` gained a *Service-to-service communication* section and a step in *Getting
  started*; the port table now names the transports. The affected service READMEs explain
  the prerequisite and, for the Customer Core, how to call it with `curl`.
- `docker-compose.yml`'s header notes that the key material has to be generated before
  the images are built.
- The `run_all_applications` and `run_customer_management_applications` scripts generate
  the key material themselves if it is missing (`.sh`) or stop with a clear message
  pointing at the script (`.bat`, which cannot run it).

## What was verified

All of this was observed on a running system in this worktree, with all five Java
services and both Node.js services started.

| Check | Result |
| ----- | ------ |
| `curl` to the Customer Core with a CA-issued client certificate | 200, customer list returned |
| `curl` to the Customer Core without a client certificate | TLS failure, connection refused by the server |
| `curl` to the Customer Core with a self-signed certificate from an unknown CA | `alert certificate unknown` |
| Plaintext HTTP against port 8110 | `Bad Request — This combination of host and port requires TLS.` |
| `customer-self-service-backend` → Customer Core (`GET /cities/8640`) | 200 |
| `policy-management-backend` → Customer Core (`GET /customers`) | 200 |
| `customer-management-backend` → Customer Core via OpenFeign (`GET /customers`) | 200 |
| STOMP connect to port 61613 with a client certificate | connected |
| STOMP connect to port 61613 without a client certificate | `tlsv13 alert certificate required` |
| STOMP connect to port 61613 in plaintext | `ECONNRESET` |
| TLS probe of port 61616 without a client certificate | `tlsv13 alert certificate required` |
| End-to-end: `POST /policies` on the Policy Management backend → JMS over `ssl://…:61616` → broker → STOMP over `stomp+ssl://…:61613` → event logged by the Risk Management server | event delivered |
| `risk-management-client run` over mTLS gRPC | report written |
| gRPC call without a client certificate | `tlsv13 alert certificate required` |
| gRPC call in plaintext | `UNAVAILABLE: Connection dropped` |
| Node services started with the key material absent | clear error naming the generation script |

The test suites were then run with **all generated key material moved out of the tree**,
to reproduce a clean checkout. All five Maven modules pass:

| Module | Tests |
| ------ | ----- |
| `customer-core` | 26 pass |
| `customer-self-service-backend` | 12 pass |
| `policy-management-backend` | 19 pass |
| `customer-management-backend` | 10 pass |
| `spring-boot-admin` | no tests, builds |

No test was disabled and no assertion was weakened. Two test configuration files were
updated so that they address the new transport: `server.ssl.enabled=false` in
`customer-core`'s test properties (its tests use `MockMvc`, so there is no socket to
secure) and `customercore.baseURL` switched to `https` in `customer-self-service-backend`'s
test properties.

### A note on the local environment

The Maven on this machine runs on a JDK 27, and the Byte Buddy version that Mockito 5.11
pulls in does not support that class file version. On a clean checkout *before* this
change, `customer-core`'s `CustomerInformationHolderTests` already failed for that reason
with `Java 27 (71) is not supported by the current version of Byte Buddy`. This is a
pre-existing environment problem, unrelated to mTLS. The runs reported above were made
with `-DargLine=-Dnet.bytebuddy.experimental=true` to work around it; no file in the
repository was changed for it.

## Decisions and assumptions

1. **"Service-to-service" excludes the browser.** The React and Vue frontends talk to
   ports 8080, 8090 and 8100. A browser cannot present a service certificate, so those
   three ports keep plain HTTP and client authentication was *not* enabled on them.
   Enabling it would have made the frontends unusable. The Customer Core (port 8110) has
   no browser clients at all, which is why it is the one HTTP server that requires client
   certificates.

2. **Spring Boot Admin was left as it is.** Its README describes it as an optional
   convenience "with all security disabled", and the actuator endpoints it scrapes live on
   the same browser-facing ports as the application APIs. Securing that channel properly
   would have meant moving every service's actuator to a separate mTLS management port
   (changing the documented port map) plus custom `RegistrationClient` and
   `InstanceWebClient` beans. I judged that out of proportion for a development tool, so
   the monitoring channel is unchanged — plaintext on *both* ends, not half-migrated. The
   visible consequence is that Spring Boot Admin can no longer scrape the Customer Core,
   which now requires a client certificate, and will show it as offline. This is the one
   piece of the system where a service-to-service channel is still plaintext, and it is
   stated here deliberately rather than hidden.

3. **One CA, one certificate per service, no certificate pinning.** Any service holding a
   CA-issued certificate can connect to any other. mTLS here proves *membership of the
   system*, not a specific identity; per-peer authorisation stays the job of the existing
   API keys and broker credentials. A stricter deployment would check the peer's subject,
   which would be the natural next step.

4. **Ports and property names were kept.** `policymanagement.tcpBrokerBindAddress` now
   holds an `ssl://` URL. Renaming it would have rippled through `docker-compose.yml` and
   any external tooling for no functional gain.

5. **Keystore passwords are in `application.properties`.** They sit next to the API keys
   and the broker password that this sample application already keeps there, with the same
   comment pointing out that a real deployment would inject them. The passwords protect
   files that are themselves never committed.

6. **Key material lives on the classpath.** Each Java service reads
   `certs/keystore.p12` and `certs/truststore.p12` from `src/main/resources`, so the
   material is packaged into the application JAR and is available inside the Docker images
   without touching any Dockerfile. The Node.js services read PEM files from their own
   `certs` directory, which their existing `COPY . ./` already picks up.

## Not verified

- **Docker.** `docker-compose up` was not run; no Docker daemon was available in this
  environment. The compose file's endpoints were updated to `https://` / `ssl://` and the
  certificates carry the compose service names as subject alternative names, but the
  containerised system has not been observed handshaking. The failure mode to watch for is
  a certificate that does not cover a hostname.
- **The NGINX load balancing demo**, for the same reason: it is Docker-only, so its
  `proxy_ssl_*` configuration is the one part of this change that was written without
  being observed working. It is correct by construction (the proxy presents a CA-issued
  certificate and verifies the upstream against the CA and the name `customer-core`,
  which the Customer Core's certificate carries), but it has not been run.
- **`scripts/generate-certificates.sh` on Windows.** It is a Bash script and was only run
  on macOS. The README points Windows users at Git Bash or WSL. A `.bat` counterpart, like
  the ones that exist for the run scripts, would be a reasonable follow-up.
- **Certificate expiry.** Service certificates are valid for 825 days and the CA for 10
  years. There is no renewal or rotation mechanism; regenerating means re-running the
  script and restarting every service.
- **The insurance quote round trip over OpenWire** was verified in one direction (the
  Policy Management backend produced and the broker accepted a message over
  `ssl://…:61616`, and the Customer Self-Service backend's JMS listener containers held
  live subscriptions on that same SSL-only port for several minutes without a single
  reconnect warning). A full quote-request round trip through the Customer Self-Service
  backend's REST API was not driven end to end.
