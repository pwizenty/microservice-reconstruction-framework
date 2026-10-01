# Service-to-service communication in Lakeside Mutual

Reconstructed with

```
uv run mrf -p Java Spring Communication -t <LakesideMutual>
```

against `https://github.com/Microservice-API-Patterns/LakesideMutual`, the
working copy at `/Users/phil/Entwicklung/MSA-Examples/LakesideMutual`.

These are facts, not findings. Whether any of these links is the smell
*Non-Secured Service-to-Service Communications* is decided by the LEMMA
validation, which additionally needs what the callee accepts and whether a
service mesh protects the channel — neither of which this step reconstructs. See
ADR-0009.

## Links

| Source | Target | Kind | Scheme | Technology | Property | Resolved to |
|---|---|---|---|---|---|---|
| CustomerManagement | CustomerCore | SERVICE | `http` | Feign | `customercore.baseURL` | `http://localhost:8110` |
| CustomerSelfService | CustomerCore | SERVICE | `http` | RestTemplate | `customercore.baseURL` | `http://localhost:8110` |
| PolicyManagement | CustomerCore | SERVICE | `http` | RestTemplate | `customercore.baseURL` | `http://localhost:8110` |

## Transport per service

| Service | Transport | Aspect in the service model |
|---|---|---|
| CustomerManagement | `plaintext` | yes |
| CustomerSelfService | `plaintext` | yes |
| PolicyManagement | `plaintext` | yes |
| CustomerCore | — | no — it calls no other service of the system |

## Evidence

```
CustomerManagement -> CustomerCore
  customer-management-backend/src/main/java/com/lakesidemutual/customermanagement/
    infrastructure/CustomerCoreClient.java:20                              SOURCE
  @FeignClient(name="customercore", url="${customercore.baseURL}",
               configuration=CustomerCoreClientConfiguration.class)

CustomerSelfService -> CustomerCore
  customer-self-service-backend/src/main/java/com/lakesidemutual/customerselfservice/
    infrastructure/CustomerCoreRemoteProxy.java:27                         SOURCE
  @Value("${customercore.baseURL}")

PolicyManagement -> CustomerCore
  policy-management-backend/src/main/java/com/lakesidemutual/policymanagement/
    infrastructure/CustomerCoreRemoteProxy.java:29                         SOURCE
  @Value("${customercore.baseURL}")
```

Each property resolves through the calling service's own
`src/main/resources/application.properties`, which states
`customercore.baseURL=http://localhost:8110` in all three services.

The target is reported as `CustomerCore` rather than as `localhost:8110`: the
host names the machine, and the port `8110` is the `server.port` of
`customer-core`, so that is the service answering there. The address the sources
state is kept in the resolved URL and in the evidence.

## No `UNRESOLVED` values

Every placeholder resolved. There is nothing on a list of values that would need
more information.

## What this step does not report, and why

Three things a reader might expect to see here are absent by construction rather
than by failure.

**The registration with Spring Boot Admin.** Each backend reaches
`http://spring-boot-admin:9000`, stated four times in `docker-compose.yml` as
`SPRING_BOOT_ADMIN_CLIENT_URL`. It is a plaintext link to an infrastructure
component, and this step does not find it: there is no call site in Java, the
client is assembled by Spring Boot's auto-configuration, and the Compose
environment is not read. It needs the step that reads the deployment.

**The three `DefaultAuthenticatedRestTemplateClient` classes** build a
`RestTemplate` and add an API key to it. They hold no address — no `@Value`
field and no URL literal — so no call is reported for them, which is correct:
configuring a client is not calling a service.

**Nothing about TLS.** No service of Lakeside Mutual configures `server.ssl`, so
all three links are plaintext, and the system has no `client-auth`, no client
certificate, no trust-all verification and no service mesh. `kubernetes/manifests`
holds nine deployment manifests and no Istio, Linkerd or Consul resource. That is
a property of the sample system, not of the reconstruction: the cases for TLS,
mutual TLS, weakened verification, gRPC, messaging and mesh enforcement are
covered by the fixtures under `tests/fixtures/s2s-*` instead, and the remaining
ones are listed as deferred in `docs/s2s-communication-plugin-plan.md` §6.

## Reproducibility

The run is deterministic: calls are sorted by target, technology, file and line
before they are attached, and `tests/test_communication_plugin.py` asserts that
two runs over a fixture produce identical output.

The paths above are relative to the system root for readability. In the
reconstructed data they are as `load_files` produced them, which matches what
`Microservice.origin_file` already contains.
