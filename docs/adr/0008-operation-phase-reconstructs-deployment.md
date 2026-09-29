# ADR-0008: Reconstruct deployment into operation nodes, in a third collection

- Status: Accepted
- Date: 2026-09-29
- Deciders: Philip Wizenty
- Supersedes: –

## Context and problem statement
`ReconstructionHandler.reconstruct_start()` names three phases - domain data,
microservices, operation - and runs two. `mrf/plugins/operation/` is an empty
package, `PluginType.DOCKER` is declared and accepted by the CLI, and
`de.fhdo.lemma.reconstruction` already requires `de.fhdo.lemma.operationdsl`.
The third phase is prepared everywhere and implemented nowhere.

LEMMA's operation models describe how the reconstructed microservices are
deployed. Its grammar (`OperationDsl.xtext`) knows two kinds of node:

- `Container`, which `deploys` one or more microservices
- `InfrastructureNode`, for the parts a system runs on rather than in

Both mandatorily carry `@technology(...)` annotations and a
`deployment technology` reference, both of which point into a `.technology`
model. `with operation environment` is optional and names a base image.

The deployment information is not in the Java sources the first two phases
read. For Lakeside Mutual it is spread over a root `docker-compose.yml`, a
`Dockerfile` per service, `kubernetes/manifests`, and an
`application.properties` per service.

## Decision drivers
- The first two phases read one service at a time; deployment is a property of
  the system, and the compose file exists once, at its root
- Reproducibility: a reconstruction result must not depend on files outside the
  analysed target
- MRF must not name LEMMA concepts it cannot observe in the sources
- Reusing the vocabulary the reconstruction already has, rather than adding a
  parallel one

## Considered options
1. A third collection `operation`, holding both node kinds, discriminated by a
   node type
2. Two collections, `container` and `infrastructure_node`, one per node kind
3. Attach the deployment information to the existing `microservice` documents
4. Keep status quo: no operation phase

## Decision
Chosen option: **1**.

**A third collection `operation`**, symmetric to `context` and `microservice`,
read by a `getReconstructedOperationNodes()` on the LEMMA side. One collection
with a node type rather than two collections (option 2), because the two kinds
share every field that is reconstructable and differ only in what they may
reference. Option 3 was rejected because a container is not a property of a
microservice: it deploys one, and an infrastructure node deploys none at all.

**Functional microservices become containers, infrastructure becomes
infrastructure nodes.** This reuses the classification the Spring plugin
already makes: it tags a reconstructed microservice with the meta-data
`MICROSERVICE_FUNCTIONAL`, and LEMMA's `MicroserviceType` already distinguishes
`FUNCTIONAL`, `UTILITY` and `INFRASTRUCTURE`.

**The operation phase reads the system root.** No new command line option: the
scope is already the target path, because `load_files` globs from it, and
`PluginType.DOCKER` already selects the phase. `mrf -p Java Spring Docker -t
<system root>` reconstructs all three phases for the whole system; pointing at
a single service simply finds no compose file, which is reported rather than
treated as an error.

**MRF does not emit the deployment technology, and does not reconstruct
technology models.** Both are chosen in LEMMA, against a hand-written
`.technology` model. A deployment technology is a reference into that model,
not something a compose file states, and the technology model is the vocabulary
that constrains the rest: its `operation environments` list bounds which base
images may be referenced, its `service properties` bound which `default values`
keys exist. MRF reconstructs what the sources say and leaves the LEMMA concepts
to LEMMA.

**`INFRASTRUCTURE_TECHNOLOGIES` becomes scoped to the service phase.** Today
`sping.py:15` lists `eureka` and `zuul`, and both `spring_plugin.py:121` and
`java_plugin.py:125` drop them from the reconstruction entirely. They are not
business microservices, which is why they are skipped, but they are exactly
what an infrastructure node is. The skip stays for the domain and service
phases and does not apply to the operation phase.

The document shape, which the LEMMA side is built against:

```json
{
  "name": "CustomerCoreContainer",
  "qualified_name": "…",
  "node_type": "CONTAINER",
  "deployed_services": [{"name": "CustomerCore", "qualified_name": "…"}],
  "operation_environment": "openjdk:11-jre",
  "depends_on": ["SpringBootAdmin"],
  "data": []
}
```

`operation_environment` is null when no `Dockerfile` is found. `data` carries
meta-data as everywhere else in the reconstruction. No `schemaVersion`: adding
one was considered and deliberately postponed until the shape settles.

## Consequences
- Positive: the third phase fits the existing seam. The LEMMA side gains one
  repository method and one generator, mirroring domain and service.
- Positive: nothing MRF writes depends on a LEMMA technology model, so the two
  can evolve separately.
- Negative: the operation phase only produces useful results at the system
  root, while the run configurations of the first two phases point at single
  services. Two ways of running MRF now coexist.
- Negative: a compose service without a reconstructed microservice cannot
  become a container, because `deploys` is mandatory. Lakeside Mutual has four
  such services - three frontends and `risk-management-server`. How they are
  reported is deferred until the first service works.
- Negative: reconstructing at the system root exposes an existing gap that
  per-service runs hide: types referenced by one microservice but reconstructed
  into another service's context. Twelve such types in Lakeside Mutual.
- Follow-up: `INFRASTRUCTURE_TECHNOLOGIES` is name-based and incomplete.
  `spring-boot-admin` is not in it and is currently reconstructed as a
  microservice with no interfaces and a context with no data structures.
- Follow-up: decide how an infrastructure node is recognised in a compose file -
  by name, by image, or by the absence of a reconstructed microservice.

## Pros and cons of the options
### 1. Third collection with a node type
- Good, because it mirrors the two collections that exist and needs one new
  read on the LEMMA side.
- Good, because both node kinds share their reconstructable fields.
- Bad, because a consumer must branch on the node type.

### 2. Two collections
- Good, because each document kind is uniform.
- Bad, because it doubles the seam for a distinction that is one field, and
  every future node kind adds another collection.

### 3. Attach to the microservice documents
- Good, because no new collection and no new read.
- Bad, because it misrepresents the relation: a container deploys a
  microservice, and an infrastructure node deploys none, so it would have
  nowhere to live.
