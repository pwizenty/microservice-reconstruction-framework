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
