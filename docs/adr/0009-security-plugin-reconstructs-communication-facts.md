# ADR-0009: Reconstruct communication security as meta-data, in a plugin of its own

- Status: Accepted
- Date: 2026-10-01
- Deciders: Philip Wizenty
- Supersedes: –

## Context and problem statement
MRF is the first step of a security-smell resolution pipeline: MRF reconstructs
architecture information, the LEMMA Model Extractor derives LEMMA models from
it, LEMMA validation rules report smells, and the findings become refactorings.
The first smell to be supported is **Non-Secured Service-to-Service
Communications** (Ponce et al., JSS 2022): two microservices of an application
communicate without a secure channel.

Deciding that smell needs facts from three places - the scheme a client calls
with, the TLS and client authentication the callee accepts, and whether a
service mesh enforces mTLS. The first step reconstructs only the first of them:
**which transport a service uses when it calls another service of the system.**

Nothing in MRF expresses it today:

- `mrf/modules/service.py` has `Microservice`, `Interface`, `Operation` and
  `Parameter`, and no notion of one microservice calling another.
  `OperationNode.depends_on` (`mrf/modules/operation.py`) looks related but is
  Compose `depends_on`, a start-up order between containers.
- There is no Technology viewpoint. Technology facts are carried as `Data`
  meta-data on a service-viewpoint element - that is how the REST annotations
  and endpoints of a controller are reconstructed - and interpreted against a
  hand-written `.technology` model on the LEMMA side.
- `SpringPlugin` reads the annotations of a `@RestController`, which is what a
  service *offers*. What a service *calls* is read nowhere.

The facts are in the sources. Lakeside Mutual states them in two shapes:

```java
@FeignClient(name="customercore", url="${customercore.baseURL}", …)     // 1 service
@Value("${customercore.baseURL}") private String customerCoreBaseURL;    // 2 services
```
```properties
customercore.baseURL=http://localhost:8110    # application.properties, 3 services
```

## Decision drivers
- MRF collects facts; the smell decision belongs to the LEMMA validation. A
  reconstructed field named `insecure`, or a severity, would move the decision
  into the wrong step of the pipeline.
- Reproducibility: same repository in, same facts out. No LLM or network call
  takes part in the reconstruction (ADR-0005's research-software constraint).
- The Mongo seam must stay backward compatible. The LEMMA side binds `Data` with
  Jackson as `List<MetaData>` with `Map<String, String> values`
  (`MongoDbRepository.xtend`, `MetaData.xtend`), so a nested value would fail to
  deserialise against the bundle in the field.
- The first step has to be visible end to end - in a generated LEMMA service
  model - rather than only in the database.
- The facts deferred to later steps must fit without rewriting the seam.

## Considered options
1. A plugin of its own in the service phase, facts as `Data` meta-data on the
   reconstructed microservice
2. Extend `SpringPlugin` with the detection
3. A fourth viewpoint module and a fourth collection, with first-class concepts
   for links, server endpoints and evidence
4. Keep status quo: reconstruct nothing about communication security

## Decision
Chosen option: **1**.

**A plugin of its own, `CommunicationPlugin`, under
`mrf/plugins/service/communication/`.** Service viewpoint, because the facts
attach to a microservice. `PluginType.COMMUNICATION` with the CLI value
`Communication`, registered the way every plugin is until ADR-0002 is accepted:
the enum, the `choices` list in `mrf/utilities/command_line.py`, and a branch in
a phase method.

It runs **in the service phase, after `SpringPlugin`**, and follows the
two-step shape `DockerPlugin` established for a plugin that needs another
phase's results:

```python
plugin = CommunicationPlugin()
plugin.execute_reconstruction(source_files)  # what the sources say
plugin.assign_to(self.reconstructed_service)  # attach to the microservices
```

The microservices are needed to tell a call to another service of the system
from a call to a third party. Nothing from the operation phase is needed,
because the **scheme** of a call is already stated in
`application*.properties`/`.yml`; the Compose environment overrides the host,
not the scheme.

**The facts are `Data` meta-data, not new concepts.** One entry per detected
call, and one aggregate entry the LEMMA aspect is generated from:

```json
{"name": "ServiceCall", "values": {
  "target": "customercore", "scheme": "http", "technology": "Feign",
  "targetKind": "SERVICE", "property": "customercore.baseURL",
  "resolvedUrl": "http://localhost:8110",
  "file": "…/CustomerCoreClient.java", "line": "20",
  "artifactType": "SOURCE", "snippet": "@FeignClient(…)"}}

{"name": "ServiceCommunicationTransport", "values": {"transport": "plaintext"}}
```

`values` stays `dict[str, str]`: one evidence per call fits as three keys of the
same entry, and several calls are several entries of the same name. This is what
makes the step additive - no new collection, no new module, and a bundle that
has not been rebuilt simply ignores the entries.

`transport` is `plaintext`, `tls`, `mixed` or `unresolved`. It is an
**aggregation of the observed schemes**, not a verdict: the smell additionally
requires the callee's `clientAuth`, the mesh mode and whether a client
certificate is configured, none of which this step reconstructs. `mixed` and
`unresolved` exist so the aggregation never has to guess. A service that calls
no other service of the system gets no aggregate entry.

The aggregation happens in MRF rather than in the LEMMA generator so the rule
lives in one place and the generator stays a mapping.

**Unresolved stays unresolved.** A placeholder with no definition, or a URL
assembled where the parser cannot follow it, is recorded with
`scheme = UNRESOLVED`. ljavalang gives a parse tree with no symbol resolution
(ADR-0003), so a call is recognised only where the URL source and the call site
are in the same class - the remote-proxy shape. A base URL injected into a
shared helper is `UNRESOLVED` by construction, and is reported as such rather
than guessed.

**Detection is modular.** One detector per client technology behind a
`ClientDetector` protocol, in `detectors/`, so adding gRPC or a messaging client
later is a module and a registry entry rather than a change to the plugin.

**On the LEMMA side** the aspect is declared in the hand-written
`models/technology/spring.technology` and emitted by the existing mechanism:
`TechnologyAspects` reads which aspects a technology model declares, for which
join points, with which properties, and `LemmaServiceGenerator` emits only what
is declared. As with ADR-0008, MRF states what the sources say and the LEMMA
technology model remains the vocabulary that bounds what can be expressed.

## Consequences
- Positive: additive. No collection, no module and no existing plugin changes,
  so a LEMMA bundle that is not rebuilt keeps working and reads the new entries
  as meta-data it does not know.
- Positive: the facts arrive where the LEMMA side already looks. Microservice
  meta-data is read today for visibility and microservice type.
- Positive: a later step can promote the facts to first-class concepts without
  changing what this one writes, because the entries are named.
- Negative: `Data.values` is flat, so a fact can carry **one** evidence record.
  The task's requirement of several evidence records per fact is not met and
  needs the fourth collection that was considered as option 3.
- Negative: the aggregate `transport` is derived data living beside the facts it
  is derived from. A consumer that reads only the aggregate cannot see which
  call made it `plaintext` without reading the `ServiceCall` entries.
- Negative: a fifth selectable plugin on a CLI whose `choices` are a hardcoded
  list, the fourth place that list has to be kept in step with `PluginType`.
  ADR-0002 would remove the duplication and is still Proposed.
- Negative: `ReconstructionHandler` gains another consumer of its class-level
  state, a known issue in `CLAUDE.md`. `reset_handler()` in
  `tests/test_golden.py` has to stay in step.
- Follow-up: the server side (`tlsEnabled`, `clientAuth`,
  `additionalPlaintextPort`, `valueSource`) is flat and fits `Data` on a
  microservice or an operation node; the mesh facts fit `OperationNode.data`.
  Both are later steps.
- Follow-up: resolving the target *host* needs the Compose and Kubernetes
  environment, and so Spring's relaxed binding
  (`CUSTOMERCORE_BASEURL` → `customercore.baseURL`) and a dependency on the
  operation phase.
- Follow-up: `targetKind` is decided by matching a host against the known
  service names. A target spelled differently in code and in the deployment is
  classified `EXTERNAL` wrongly; the evidence is recorded so it can be reviewed.
- TODO(author): whether the reconstruction of further smells should keep using
  meta-data or trigger the fourth viewpoint, and whether that decision belongs
  in this ADR or a later one.

## Pros and cons of the options
### 1. Own plugin, facts as meta-data
- Good, because it is additive: nothing existing changes and the LEMMA seam
  keeps its shape.
- Good, because the plugin is where later steps of the smell belong, and
  `SpringPlugin` does not grow further.
- Good, because the detection is selectable; a run without `Communication`
  behaves exactly as before.
- Bad, because meta-data is flat, so one evidence per fact is the ceiling.
- Bad, because a plugin that needs the microservices of another plugin repeats
  the hand-wiring that `DockerPlugin` already shows is awkward.

### 2. Extend `SpringPlugin`
- Good, because the facts come from Spring annotations on classes that plugin
  already parses, and no `PluginType`, CLI entry or phase branch is needed.
- Good, because the microservices are at hand, with no cross-plugin hand-over.
- Bad, because the detection could not be switched off independently, and every
  existing golden fixture's expected output would change.
- Bad, because `SpringPlugin` is already the largest plugin and the later steps
  of this smell read deployment files, which have nothing to do with it.

### 3. Fourth viewpoint module and collection
- Good, because links, server endpoints and evidence become first-class, with
  as many evidence records per fact as the sources give.
- Good, because it is where the full smell ends up.
- Bad, because it is a persistence change for one flat fact, and the LEMMA side
  would need a new reader before anything is visible at all.
- Bad, because it fixes the shape of concepts before the detection has shown
  what they need to hold.

### 4. Keep status quo
- Good, because the pipeline's later steps are not yet built, so nothing
  consumes the facts today.
- Bad, because the smell cannot be detected at all, which is the point of the
  pipeline.
