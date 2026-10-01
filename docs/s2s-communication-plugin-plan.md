# Plan: a technology aspect for service-to-service communication

Status: **proposed, awaiting review (Checkpoint 1)**

First step towards the security smell *Non-Secured Service-to-Service
Communications* (Ponce et al., JSS 2022): reconstruct which transport a service
uses when it calls another service, and mark it in the generated LEMMA service
model as a technology aspect.

Scope is deliberately one fact. Everything else the smell needs — the server's
TLS and client authentication, the service mesh, gRPC, messaging, client
certificates, weakened verification — is listed in §6 and left for later steps.

---

## 1. What this step delivers

```diff
  service models
  @technology(javaWithSpring)
+ @javaWithSpring::_aspects.ServiceCommunicationTransport(transport = "plaintext")
  public functional microservice com.lakesidemutual.customermanagement.CustomerManagement {
```

The aspect states what the reconstruction observed, not whether it is a smell.
`transport` takes one of four values:

| Value | Meaning |
|---|---|
| `plaintext` | at least one call to another service of the system over `http` |
| `tls` | every such call uses `https` |
| `mixed` | both occur |
| `unresolved` | calls were found but no scheme could be determined |

A service that calls no other service of the system gets no aspect at all.

### Why this is a fact and not a smell decision

The task document rules out the plugin deciding the smell, and that still
holds. `transport = plaintext` is an observation about the scheme of the
outgoing calls. Deciding the smell additionally needs the callee's
`clientAuth`, the mesh mode, and whether a client certificate is configured —
none of which this step collects. The LEMMA validation keeps the decision, and
this aspect is one of its inputs.

`mixed` and `unresolved` exist so that the aggregation never has to guess. No
field is named `insecure`, and nothing carries a severity.

---

## 2. Findings from Phase 0 that shape the design

Read from the code, not assumed.

### 2.1 Plugin contract and registration

`Plugin` (`mrf/plugins/reconstruction_plugin.py`) is an ABC with `file_types()`
and `execute_reconstruction(source_files)`. `file_types()` is advisory — the
framework passes every file to every plugin, which filters itself.

There is no discovery. ADR-0002 (*entry points*) is still **Proposed**, so a
plugin is wired in by hand in three places: the `PluginType` enum, the
`choices=[…]` list in `mrf/utilities/command_line.py` (case-sensitive, must
match the enum *values*), and a branch in a phase method of
`ReconstructionHandler`.

### 2.2 Phases and reading another plugin's results

`reconstruct_start` runs three hardcoded phases: domain data (`JavaPlugin`),
service (`SpringPlugin` + `JavaPlugin.reconstruct_dependencies`), operation
(`DockerPlugin`). No dependency mechanism exists; a plugin sees another's
results only because the handler hands them over. The one precedent is the
pattern to copy:

```python
plugin = DockerPlugin()
plugin.execute_reconstruction(source_files)  # what the files alone say
nodes = plugin.assign_deployed_services(self.reconstructed_service)
```

`ReconstructionHandler` is a singleton with class-level state that leaks between
runs and tests; `tests/test_golden.py` resets it with `reset_handler()`.

### 2.3 The meta-data mechanism fits this fact

```python
@dataclass
class Data:
    name: str
    values: dict[str, str] = field(default_factory=dict)
```

`Data` is attached to `Microservice`, `Interface`, `Operation`, `Parameter`,
`OperationNode`, `DataStructure` and `Field`, persisted as `data`, and read on
the LEMMA side as `List<MetaData>` with `Map<String, String> values`.

`values` is flat, so it cannot hold a *list* of evidence records per fact. With
**one evidence per call** — `file`, `line`, `snippet` as three keys of the same
entry — it fits, and several calls are several `Data` entries with the same
name. That is the whole reason this step needs **no new collection, no new
module and no ADR for persistence**, where the full smell did.

### 2.4 The scheme does not need the operation phase

Lakeside Mutual resolves its one cross-service call like this:

```java
@FeignClient(name="customercore", url="${customercore.baseURL}", …)   // client
@Value("${customercore.baseURL}") private String customerCoreBaseURL;  // client
```

```properties
customercore.baseURL=http://localhost:8110        # application.properties
```
```yaml
CUSTOMERCORE_BASEURL=http://customer-core:8110    # docker-compose.yml
```

The Compose environment changes the **host**, not the **scheme**. Since this
step only reports the scheme, `application*.properties`/`.yml` is sufficient and
the plugin needs nothing from the operation phase. Compose and Kubernetes
resolution becomes necessary only when the resolved URL and the target identity
matter, which is a later step.

### 2.5 The LEMMA side needs two small additions

Checked in the code:

- `de.fhdo.lemma.service.Microservice` **has** `getAspects()`.
- `ServiceDslExtractor.generate(Microservice)` does **not** print them — the
  same gap that `generate(Interface)` had before the REST work.
- `LemmaServiceGenerator` calls `assignAspects` for interfaces, operations and
  parameters, but **not** for the microservice.

The filtering mechanism needs no change at all: `TechnologyAspects` already
reads a technology model for the aspects it declares, the join points it
declares them for, and the properties they carry, and the generator emits only
what the model declares. Declaring the aspect for `microservices` and naming the
meta-datum after it is enough.

---

## 3. What gets reconstructed

One `Data` entry per detected call, on the `Microservice` that makes it:

```python
Data(
    "ServiceCall",
    {
        "target": "customercore",  # as written in the code
        "scheme": "http",  # http | https | UNRESOLVED
        "technology": "Feign",  # Feign | RestTemplate | RestClient | WebClient
        "property": "customercore.baseURL",  # the placeholder, if there was one
        "resolvedUrl": "http://localhost:8110",  # or absent when UNRESOLVED
        "file": "…/infrastructure/CustomerCoreClient.java",
        "line": "20",
        "snippet": '@FeignClient(name="customercore", url="${customercore.baseURL}")',
        "artifactType": "SOURCE",
    },
)
```

and one aggregate entry that the LEMMA aspect is generated from:

```python
Data("ServiceCommunicationTransport", {"transport": "plaintext"})
```

The aggregate is computed in MRF rather than in the generator so the generator
stays a mapping and the rule lives in one place. It is an aggregation of the
`scheme` values above, nothing more.

Calls whose host is not one of the system's own services are recorded with
`targetKind = EXTERNAL` on the `ServiceCall` entry and **excluded** from the
aggregate — this smell is about internal traffic. Resolving "own service" uses
the microservice names the service phase already produced, which is why the
plugin receives them (§4.2).

---

## 4. Implementation

### 4.1 Structure

```
mrf/plugins/service/communication/
    __init__.py
    communication_plugin.py       CommunicationPlugin(Plugin)
    detectors/
        __init__.py               DETECTORS registry
        detector.py               ClientDetector protocol
        feign.py                  @FeignClient
        rest_template.py          RestTemplate, RestClient, WebClient
    placeholders.py               ${…} -> application*.properties / *.yml
mrf/utilities/communication.py    annotation names, property keys, enumerations
```

Service viewpoint, because the facts attach to a microservice. One detector per
client technology behind a protocol, so a technology is added as a module plus
one registry entry:

```python
class ClientDetector(Protocol):
    technology: str

    def detect(self, clazz, unit, context: DetectionContext) -> list[ServiceCall]: ...
```

Parsing reuses what exists: `load_classes`, `has_annotation`, `find_annotation`,
`get_annotation_values` from `mrf/utilities/java_utils.py`, and the
properties reader of the Docker plugin for `application.properties`. YAML via
`yaml.safe_load`, as `DockerPlugin` does. **No new dependency.**

### 4.2 Wiring

- `PluginType.COMMUNICATION = "Communication"`, added to the CLI `choices`.
- Runs in the **service phase**, after `SpringPlugin`, because it attaches its
  meta-data to the microservices that phase produced:

```python
if PluginType.COMMUNICATION in self.plugins:
    plugin = CommunicationPlugin()
    plugin.execute_reconstruction(source_files)
    plugin.assign_to(self.reconstructed_service)  # attaches the Data entries
```

Nothing else in the handler changes: the facts ride on the existing
microservice documents, so `reconstruct_save` and the collections stay as they
are. Selecting `Communication` without `Spring` reconstructs nothing and logs
why, rather than guessing.

### 4.3 Extraction rules for this step

| Rule | Behaviour |
|---|---|
| Literal URL in the annotation or call | scheme taken from it |
| `${placeholder}` | looked up in `application.properties`, `application.yml`, then `application-<profile>.*`; first hit wins, profile recorded |
| Resolution fails | `scheme = UNRESOLVED`, never a guess |
| Discovery call (`@FeignClient` with a name and no URL, `@LoadBalanced`) | scheme from the code if present, else `UNRESOLVED` |
| Excluded | `src/test/**`, `*Test`, `*IT`, WireMock/MockServer/Testcontainers, and the XML namespace hosts `w3.org`, `springframework.org/schema`, `maven.apache.org` |
| Determinism | calls sorted by `(target, technology, file, line)` before they are attached |

**Limit, from the parser:** ljavalang gives a parse tree with no symbol
resolution, so a call is only recognised when the URL source and the call site
are in the same class — the "remote proxy" shape that Lakeside Mutual uses. A
base URL injected into a shared helper and used elsewhere yields `UNRESOLVED`.
This is a structural limit, not a matter of effort.

### 4.4 LEMMA side

Three additions, each mirroring the REST technology work:

1. `models/technology/spring.technology`:

```
aspect ServiceCommunicationTransport<singleval> for microservices {
    string transport <mandatory>;
}
```

2. `LemmaServiceGenerator.generateMicroserviceFrom`: one call,
   `assignAspects(microservice.aspects, reconstructedMicroservice.metaData, MICROSERVICES)`,
   plus the `MICROSERVICES` constant. The `public`/`functional` meta-data
   already on a microservice are not declared aspects, so the existing filter
   drops them.

3. `ServiceDslExtractor.generate(Microservice)`: print the aspects, exactly as
   `generate(Interface)` now does.

Verified end to end by compiling both bundles with the Xtend batch compiler and
running `ReconstructionRegressionTest` headlessly.

---

## 5. Tests

Fixtures under `tests/fixtures/`, each two services, written by hand per the
`add-golden-fixture` skill — the six cases of the task's table that this step
covers:

| # | Case | Expected |
|---|---|---|
| 1 | `RestTemplate` with a literal `http://` URL | `scheme=http`, `transport=plaintext` |
| 2 | `@FeignClient` with `url="${…}"` resolved from `application.properties` | resolved URL, scheme, evidence in code and configuration |
| 3 | `https://` throughout | `transport=tls` |
| 11 | placeholder with no definition | `scheme=UNRESOLVED`, `transport=unresolved` |
| 12 | `http://` only in test code and an XML schema URL | no call recorded, no aspect |
| 14 | call to a third-party host | `targetKind=EXTERNAL`, excluded from the aggregate |
| — | one `http` and one `https` call | `transport=mixed` |
| — | determinism: two runs over one fixture | identical output |

Existing tests must stay green. The plugin adds a phase branch and touches
`reconstruction_plugin.py` and `command_line.py`; no existing plugin changes.
`expected_pipeline.json` of the current fixtures should not move, because the
new plugin is only run when selected — that is asserted rather than assumed.

### Lakeside Mutual smoke test

`docs/s2s-lakeside-mutual-results.md`, with the calls, their schemes and
evidence. Expected from the survey: three services calling `customer-core`
through `customercore.baseURL = http://localhost:8110`, one by Feign and two by
`RestTemplate`, so `transport = plaintext` on each of them and no aspect on
`CustomerCore` itself. Every `UNRESOLVED` listed with what would resolve it. No
interpretation as a smell.

---

## 6. Deliberately left for later steps

Each is listed so the reduced scope does not read as the whole picture. None of
them requires changing what this step writes.

| Fact | Needs |
|---|---|
| Server `port`, `protocol`, `tlsEnabled`, `clientAuth`, `additionalPlaintextPort`, `valueSource` (§4.1 of the task) | a place for per-port records; `Data` can hold one entry per port, flat |
| Mesh `meshType`, `sidecarInjected`, `peerAuthenticationMode`, `destinationRuleTlsMode` (§4.3) | reading `kubernetes/manifests/**`, which MRF does not do at all today; flat, fits `OperationNode.data` |
| Resolved URL and target identity via Compose `environment`, `env_file`, Kubernetes `env`, ConfigMaps | the operation phase's results, so a fourth phase or a second step like `assign_deployed_services` |
| Spring relaxed binding (`CUSTOMERCORE_BASEURL` → `customercore.baseURL`) | explicit name mapping; only needed once the host matters |
| `clientCertificateConfigured`, `verificationWeakened` | SSL bundle and `SSLContext` analysis; name-based detection of `TrustAllStrategy`, `NoopHostnameVerifier`, `InsecureTrustManagerFactory` |
| gRPC (`usePlaintext()`), messaging (`amqp://`, Kafka `security.protocol`) | further detectors; **absent from every sample system available** |
| One link per profile with the active one marked | profile-specific files plus `SPRING_PROFILES_ACTIVE` from the deployment |
| Multiple evidence records per fact | a nested structure, which `Data.values` cannot hold — this is where the fourth collection and an ADR become necessary |

---

## 7. Open questions for the review

1. **Aspect shape.** `ServiceCommunicationTransport(transport = "plaintext")`,
   one aspect with a value — recommended, because it states `mixed` and
   `unresolved` without ambiguity. The alternative is two marker aspects,
   `PlaintextServiceCommunication` and `TlsServiceCommunication`, which read
   more directly but say nothing useful when both apply.
2. **Separate plugin, or an extension of `SpringPlugin`?** The facts come from
   Spring annotations on classes `SpringPlugin` already parses, so folding them
   in would avoid a new `PluginType`, a CLI entry and a handler branch. A
   separate plugin keeps `SpringPlugin` from growing and is where the later
   steps belong. Recommended: separate.
3. **Does this step want an ADR?** No persistence or model change is involved,
   so `CLAUDE.md` does not require one. Worth one anyway to record the
   viewpoint decision and the aspect name, since later steps build on both.
