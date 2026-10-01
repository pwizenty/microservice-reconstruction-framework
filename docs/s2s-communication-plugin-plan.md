# Plan: reconstructing service-to-service communication security

Status: **proposed, awaiting review (Checkpoint 1)**

A plugin that collects the facts needed to detect *Non-Secured
Service-to-Service Communications* (Ponce et al., JSS 2022). The plugin collects
facts only; whether a link is a smell is decided by the LEMMA validation in step
3 of the pipeline.

---

## 1. Findings: how MRF works today

### 1.1 Plugin contract

`mrf/plugins/reconstruction_plugin.py` defines `Plugin`, an ABC with two
abstract methods:

```python
class Plugin(ABC):
    def file_types(self) -> list[str]: ...  # suffixes the plugin reads
    def execute_reconstruction(self, source_files) -> Any: ...
```

`file_types()` is **advisory**. The framework does not filter by it: every
plugin receives all source files and filters itself (`DockerPlugin` matches
`COMPOSE_FILE_NAMES`, `SpringPlugin` passes its suffixes to `load_classes`).
`execute_reconstruction` has no declared return type — each plugin returns
whatever the handler expects of it.

### 1.2 Registration and discovery

There is **no discovery**. A plugin is wired in by hand in three places:

| Place | What has to be added |
|---|---|
| `mrf/plugins/reconstruction_plugin.py` | a member of the `PluginType` enum |
| `mrf/utilities/command_line.py` | the literal in `choices=["Java", "Docker", "Spring"]` |
| `mrf/modules/reconstruction_handler.py` | an `if PluginType.X in self.plugins` branch in a phase method |

ADR-0002 (*Discover plugins via entry points*) is still **Proposed**, so the
hand-wiring is the current contract. This plan does not change it; doing so is a
separate decision.

The CLI `choices` are case-sensitive and must match the `PluginType` **values**
exactly.

### 1.3 Phase order and sharing data between plugins

`ReconstructionHandler.reconstruct_start` runs three hardcoded phases:

```
__reconstruct_data(…)       JavaPlugin      -> reconstructed_data      (contexts)
__reconstruct_service(…)    SpringPlugin    -> reconstructed_service   (microservices)
                            JavaPlugin.reconstruct_dependencies(…)
__reconstruct_operation(…)  DockerPlugin    -> reconstructed_operation (nodes)
```

There is **no dependency mechanism**. A plugin reads another's results only
because the handler hands them over explicitly. There is one precedent, and it
is the pattern to follow:

```python
plugin = DockerPlugin()
plugin.execute_reconstruction(source_files)  # what the files alone say
nodes = plugin.assign_deployed_services(self.reconstructed_service)
```

`DockerPlugin` keeps what it needs for the second step in instance state
(`build_directories`, `defining_files`). A plugin that needs results of an
earlier phase therefore splits into *read the files* and *resolve against what
is now known*.

`ReconstructionHandler` is a singleton whose state is class level, so it leaks
between runs and tests (a known issue in `CLAUDE.md`). `tests/test_golden.py`
works around it with `reset_handler()`.

### 1.4 Data model and persistence

Three viewpoints, three modules, three collections:

| Module | Concepts | Collection |
|---|---|---|
| `mrf/modules/domain_data.py` | `Context`, `DataStructure`, `Field`, `ComplexType`, `PrimitiveType`, `ClassType` | `context` |
| `mrf/modules/service.py` | `Microservice`, `Interface`, `Operation`, `Parameter`, `CommunicationType`, `ExchangePattern` | `microservice` |
| `mrf/modules/operation.py` | `OperationNode`, `NodeType`, `DeployedService` | `operation` |

Mapping layer: `mrf/repositories/<viewpoint>/…` defines an `R*` dataclass per
concept and a `transform_*_for_database` function.
`mrf/repositories/mongo_repository.py` has one `save_*` per viewpoint and writes
`dataclasses.asdict(...)`, keyed on `qualified_name`:

```python
collection.replace_one(
    {"qualified_name": document["qualified_name"]}, document, upsert=True
)
```

Every concept carries meta-data through one shared mechanism:

```python
@dataclass
class Data:
    name: str
    values: dict[str, str] = field(default_factory=dict)
```

It is attached to `Microservice`, `Interface`, `Operation`, `Parameter`,
`OperationNode`, `DataStructure` and `Field`, persisted as `data`, and read on
the LEMMA side as `List<MetaData>` with `Map<String, String> values`.

**Concepts that do not exist**, and that this smell needs:

- **No Technology viewpoint.** The task assumes the viewpoints *Domain,
  Service, Technology, Operation*. MRF has three: domain data, service,
  operation. Technology facts are currently carried as `Data` meta-data on a
  service-viewpoint element (the REST aspects and endpoints) or named in a
  hand-written LEMMA technology model. There is no place of their own.
- **No dependency between services.** `Microservice` has no "required
  microservices". `OperationNode.depends_on` exists but is Compose
  `depends_on`, a start-up order between containers, not a call.
- **No endpoint/port/protocol concept.** A REST address is a `Data` entry named
  `Endpoint` on an interface or operation (added for the REST technology work);
  a port is a plain string in a container's `ServiceProperties`.
- **No traceability mechanism.** `Microservice.origin_file` is the only link
  back to source, one path per microservice, no line and no snippet. `Data`
  cannot hold evidence: `values` is `dict[str, str]`, so neither a list of
  evidence records nor a nested record fits it.

### 1.5 Reference plugins

- **Java** (`mrf/plugins/data/java/java_plugin.py`): parses with **ljavalang**
  (a fork, imported as `javalang`), via `mrf/utilities/java_utils.py`
  (`load_classes`, `parse_java_file`, `has_annotation`, `find_annotation`,
  `get_annotation_values`, `resolve_complex_field`). `load_classes` skips a file
  the parser rejects, with a warning.
- **Spring** (`mrf/plugins/service/spring/spring_plugin.py`): walks the parsed
  classes, matches annotations from `mrf/utilities/sping.py`.
- **Docker** (`mrf/plugins/operation/docker/docker_plugin.py`): `yaml.safe_load`
  on Compose files, line-wise reading of a Dockerfile, constants in
  `mrf/utilities/docker.py`. It already reads `application.properties` for
  `spring.application.name` and `server.port` (`__read_properties`).

Everything needed to read Java, YAML and properties files is therefore present.
**No new third-party dependency is expected.**

What ljavalang does **not** give is symbol or type resolution: the parse tree
has no bean graph and no cross-file linking. Section 3.4 states the consequence.

### 1.6 Tests

- `tests/test_golden.py` — golden fixtures under `tests/fixtures/<system>/src/`,
  compared with `deepdiff(..., ignore_order=True)` against `expected.json`
  (plugins alone) and `expected_pipeline.json` (the whole handler). Fixtures are
  auto-discovered by the presence of those files. Marked `@pytest.mark.golden`.
- Unit tests per utility module (`tests/test_java_utils.py`, …).
- `tests/test_mongo_repository.py` uses `mongomock`; no test touches a real
  MongoDB.
- Skill `add-golden-fixture` documents the rules: fixtures minimal, expected
  output human-reviewed, never regenerated just to make a test pass.

### 1.7 Build setup

MRF is a plain Python package: `uv`, `pyproject.toml`, Python ≥ 3.12, `ruff`,
`mypy`, `pytest`. No OSGi, no Eclipse plug-in project, nothing to declare twice.
The gate is `ruff check`, `ruff format`, `mypy`, `pytest`.

(The Eclipse/PDE concern in the task applies to the **LEMMA** repository, where
`de.fhdo.lemma.reconstruction` is an OSGi bundle with `MANIFEST.MF` and
`build.properties`. That is Phase 2 and out of scope here.)

### 1.8 LEMMA side (read only)

`de.fhdo.lemma.reconstruction/src/…/MongoDbRepository.xtend` reads exactly three
collections by name — `context`, `microservice`, `operation` — and deserialises
each document with Jackson into `Context`, `Microservice`, `OperationNode`.
Field names are bound with `@JsonProperty`; unknown properties are ignored
(`FAIL_ON_UNKNOWN_PROPERTIES, false`).

Generators: `LemmaDomainGenerator`, `LemmaServiceGenerator`,
`LemmaOperationGenerator`. `LemmaServiceGenerator` already maps `Data`
meta-data onto a LEMMA technology model: `TechnologyTypes` and
`TechnologyAspects` scan `models/technology/spring.technology` for the types and
service aspects it declares, and only a declared name is emitted. That is the
mechanism Phase 2 would extend — a new fact becomes an aspect in a technology
model, and the generator emits it when the model declares it.

**Consequence for the schema:** a *new collection* is invisible to the LEMMA
side until a reader is added, which is backward compatible. *Changing the shape
of `Data.values`* is not: `Map<String, String>` would fail to deserialise a
nested value. So `Data` must stay as it is.

---

## 2. Mapping the facts onto the model

### 2.1 What fits an existing concept

| Fact (§4 of the task) | Existing concept | How |
|---|---|---|
| Service name of source/target | `Microservice.name`, `Data("ServiceProperties").values["springApplicationName"]`, `OperationNode` name and `Data("ComposeService").values["Name"]` | resolved against, not re-reconstructed |
| Exposed port | `Data("ServiceProperties").values["serverPort"]` on a container | read as an input |
| Mesh facts per service (§4.3) | `OperationNode.data` | one `Data("ServiceMesh")` entry per node, flat string values — fits `dict[str, str]` |

### 2.2 What needs new concepts

The server configuration (§4.1), the communication links (§4.2) and the
evidence (§4.4) do not fit. Each is a list of records with several fields, and
each record carries a list of evidence; `Data.values` is flat `str → str`.

**Proposal: a fourth viewpoint module and a fourth collection.**

```
mrf/modules/communication.py
    Evidence(file, line, artifact_type: ArtifactType, snippet)
    ArtifactType          SOURCE | CONFIGURATION | DEPLOYMENT
    ServerEndpoint(port, protocol: Protocol, tls_enabled, client_auth: ClientAuth,
                   additional_plaintext_port, value_source: ValueSource,
                   evidence: list[Evidence])
    CommunicationLink(source, target, target_kind: TargetKind, channel: Channel,
                      technology, scheme: Scheme, resolved_url, profile,
                      profile_active, client_certificate_configured,
                      verification_weakened, evidence: list[Evidence])
    ServiceCommunication(qualified_name, name,
                         server_endpoints: list[ServerEndpoint],
                         outgoing_links: list[CommunicationLink],
                         data: list[Data])

mrf/repositories/communication/communication.py   R* classes + transform
mrf/repositories/mongo_repository.py              save_service_communications(...)
                                                  -> collection "communication"
```

One document per service, keyed on `qualified_name` so `__save` upserts it like
every other document. Enumerations are persisted by value, as
`RExchangePattern`/`RCommunicationType` already do.

**Why a new collection rather than extending `microservice`:**

1. The facts span viewpoints. A link is Service, its TLS configuration is
   Technology, the mesh is Operation. Hanging all of it on `microservice` would
   put deployment facts into the service viewpoint.
2. `Data.values` cannot carry evidence, and widening it to `dict[str, Any]`
   would break the Jackson binding on the LEMMA side (§1.8).
3. ADR-0008 set the precedent: the operation phase got concepts and a
   collection of its own rather than being folded into an existing one.
4. A new collection is additive. Nothing on the LEMMA side reads it until
   Phase 2 adds a reader, so no existing behaviour changes.

**Mesh facts are the exception**: they are per node, flat, and belong to the
operation viewpoint, where `OperationNode.data` already exists and the LEMMA
operation generator already reads meta-data. Putting them there keeps the new
collection to what genuinely needs it.

### 2.3 ADR

`CLAUDE.md` requires an ADR for changes to persistence or the model, and this
adds both a fourth collection and a fourth module. **ADR-0009 "Reconstruct
communication security facts in a fourth collection"** has to be drafted (skill
`write-adr`) and will start as *Proposed*. The plan assumes that ADR; if it is
rejected, the fallback is §2.2 option (i), encoding records into composite keys
in `Data.values`, which I do not recommend — it makes the LEMMA side parse
strings.

---

## 3. Implementation

### 3.1 Structure

```
mrf/plugins/communication/
    __init__.py
    communication_plugin.py          CommunicationPlugin(Plugin)
    detectors/
        __init__.py                  DETECTORS registry
        detector.py                  ClientDetector protocol
        rest_template.py             RestTemplate, RestClient, WebClient
        feign.py                     @FeignClient
        grpc.py                      ManagedChannelBuilder, usePlaintext()
        messaging.py                 RabbitMQ, Kafka, ActiveMQ
    server_configuration.py          §4.1 from application*.properties/yml
    mesh.py                          §4.3 from Kubernetes manifests
    placeholders.py                  the resolution chain of §5
    verification.py                  weakened-verification detection
mrf/utilities/security.py            constants: annotation and property names
```

One detector per client technology behind a small protocol, as the task asks:

```python
class ClientDetector(Protocol):
    technology: str
    channel: Channel

    def detect(
        self, clazz, unit, context: DetectionContext
    ) -> list[CommunicationLink]: ...
```

Adding a technology is a new module plus one entry in `DETECTORS`.

### 3.2 Wiring

- `PluginType.COMMUNICATION = "Communication"`, added to the CLI `choices`.
- A **fourth phase**, `__reconstruct_communication`, after the operation phase,
  following the `assign_deployed_services` precedent:

```python
plugin = CommunicationPlugin()
plugin.execute_reconstruction(source_files)  # facts from files
ReconstructionHandler.reconstructed_communication = list(
    plugin.resolve(self.reconstructed_service, self.reconstructed_operation)
)
```

It must run last: targets are resolved against the microservice names of the
service phase and the Compose environment of the operation phase.
`reconstruct_save` gains `save_service_communications(...)`, and
`reset_handler()` in `tests/test_golden.py` the fourth list.

Running `-p Communication` without `Spring`/`Docker` is allowed; targets then
resolve to `EXTERNAL` or `UNRESOLVED`, and the plugin logs that at warning level
rather than guessing.

### 3.3 Extraction rules

Mostly as specified in §5 of the task. Three points worth settling now:

**Spring relaxed binding.** Lakeside Mutual resolves
`@Value("${customercore.baseURL}")` against `CUSTOMERCORE_BASEURL` in the
Compose `environment`. Mapping an environment variable name to a property name
(upper case, `.`/`-`/camel-case boundaries to `_`) has to be implemented
explicitly; it is the only way case 2 of the fixture table resolves.

**Precedence**, highest first: Compose `environment` / Kubernetes `env` →
`env_file` / ConfigMap → `application-<profile>.properties|yml` →
`application.properties|yml`. One link per profile, the profile named by
`SPRING_PROFILES_ACTIVE` marked active.

**Exclusions** (§5): `src/test/**`, `*Test`, `*IT`, WireMock/MockServer/
Testcontainers, commented-out code, and the XML namespace hosts
(`w3.org`, `springframework.org/schema`, `maven.apache.org`). Comments are
dropped by the Java parser for annotations and string literals in code, but a
URL in a properties file needs the `#`/`!` comment rule that
`DockerPlugin.__read_properties` already applies.

### 3.4 Honest limits of the static analysis

These follow from ljavalang having no symbol resolution, and should be read
before the fixture table is taken as a quality bar:

1. **A link is anchored in one class.** The URL source (a `@FeignClient`
   annotation, or a `@Value` field) and the call have to be in the same class.
   Lakeside Mutual's `CustomerCoreRemoteProxy` and `CustomerCoreClient` are
   exactly that shape, which is the common "remote proxy" pattern. A base URL
   injected into a shared helper and used elsewhere resolves to `UNRESOLVED`.
2. **`@ConfigurationProperties` is partial.** The prefix and the field name give
   the property name; a value assembled at runtime does not.
3. **Weakened verification is name-based.** `TrustAllStrategy`,
   `NoopHostnameVerifier`, `InsecureTrustManagerFactory` and friends are
   recognised by name. An `X509TrustManager` with an empty `checkServerTrusted`
   is recognised by an empty method body in a class implementing that
   interface — a custom verifier that returns `true` through a helper is not.
4. **`targetKind`** is decided by matching the host against the known service
   and node names; anything else is `EXTERNAL`. A target that is spelled
   differently in code and in Compose (an alias) is `EXTERNAL` wrongly, so the
   match is reported with its evidence for review.

Every one of these produces `UNRESOLVED` or a recorded fact with evidence, never
a guess (§5 rule 5).

### 3.5 Determinism

Collections sorted before they are returned: services by `qualified_name`, links
by `(target, channel, profile, file, line)`, endpoints by `port`, evidence by
`(file, line)`. The determinism test runs the plugin twice over a fixture and
compares the serialised result, in the shape `tests/test_golden.py` already
serialises models.

---

## 4. Tests

- One fixture per case of the task's table, under
  `tests/fixtures/s2s-<case>/`, each two or three small services. Cases 7–10
  (gRPC, messaging, Istio `STRICT`, Istio `PERMISSIVE`) have no counterpart in
  Lakeside Mutual, so they are hand-written from the specification.
- `expected.json` written by hand from the fixture, per the
  `add-golden-fixture` skill, not generated from the new plugin.
- The determinism test of §3.5.
- Existing tests stay green. The plugin adds a phase and touches
  `reconstruction_handler.py`, `reconstruction_plugin.py` and
  `command_line.py`; no existing plugin changes, so the current fixtures should
  not move. Should any `expected_pipeline.json` change, the diff gets reviewed
  before it is accepted.

### What Lakeside Mutual will and will not show

Surveyed before writing this plan:

| | Present |
|---|---|
| Client call sites | RestTemplate ×5, RestClient ×2, `@FeignClient` ×2 |
| Placeholder resolved via Compose | `customercore.baseURL` → `CUSTOMERCORE_BASEURL=http://customer-core:8110` |
| Infrastructure target | `SPRING_BOOT_ADMIN_CLIENT_URL=http://spring-boot-admin:9000` |
| `server.ssl` anywhere | **none** → every service `tlsEnabled=false`, `FRAMEWORK_DEFAULT` |
| Kubernetes manifests | `kubernetes/manifests/*.yaml`, 9 files |
| Istio / Linkerd / Consul | **none** → `meshType=NONE` |
| gRPC, RabbitMQ, Kafka | **none** |
| mTLS, trust-all, profiles with different URLs | **none** |

So the smoke test will produce a short, uniform table — plaintext HTTP
throughout, no mesh — and that is the expected outcome, not a failure of the
plugin. Roughly five of the fourteen cases are exercised by it; the other nine
rest on the fixtures alone. `docs/s2s-lakeside-mutual-results.md` will say so
explicitly, and will list every `UNRESOLVED` value with what would resolve it.

---

## 5. Proposed delivery, in reviewable steps

One branch per step, each cut from `dev` and merged by PR, each green on ruff,
mypy and pytest:

| Step | Content |
|---|---|
| 1 | ADR-0009; `mrf/modules/communication.py`; `R*` classes; `save_service_communications`; `mongomock` test. No plugin yet. |
| 2 | Plugin skeleton, wiring, the fourth phase, server configuration (§4.1) and the mesh (§4.3) — the parts that read configuration and deployment files. Fixtures 3, 4, 5, 9, 10. |
| 3 | Client detectors: RestTemplate/RestClient/WebClient, Feign, placeholder resolution. Fixtures 1, 2, 11, 12, 13, 14. |
| 4 | gRPC, messaging, weakened verification, client certificates. Fixtures 6, 7, 8. Determinism test. Lakeside Mutual smoke test and `docs/s2s-lakeside-mutual-results.md`. |

Step 1 is the one to get right, because it fixes the schema the rest writes
into. Steps 2–4 are additive.

---

## 6. Open questions for the review

1. **Fourth collection and ADR-0009** — agreed, or should the facts be squeezed
   into `Data` meta-data on the existing documents (§2.3 fallback)?
2. **Plugin name.** `PluginType.COMMUNICATION` / `-p Communication`. The plugin
   collects communication facts, so naming it after the smell would be wrong,
   but "Communication" is broad. Alternative: `SECURITY`.
3. **Is Kubernetes in scope for Phase 1?** The task asks for Kubernetes `env`,
   ConfigMaps and mesh resources. MRF has no Kubernetes plugin at all today, so
   this plugin would be the first thing to read `kubernetes/manifests/**`.
   Lakeside Mutual has manifests but no mesh, so the mesh path would be covered
   by fixtures only. It can be deferred to a later step without affecting the
   schema.
4. **Mesh facts on `OperationNode.data`** rather than in the new collection
   (§2.2) — agreed?
5. **Scope of step 4.** gRPC and messaging appear in none of your sample
   systems. Worth building now, or specified and deferred until a system needs
   them?
