# Plan: reconstructing the Node components

Status: **proposed, awaiting review**

Lakeside Mutual has five components that are not written in Java. MRF sees none
of them today: the Docker plugin finds their containers, and the service and
domain phases find nothing to put in them, so `risk-management-server` appears in
the operation model's skipped list and nowhere else.

---

## 1. What the five components are

Surveyed before writing this, from `package.json`, the sources and the
configuration:

| Component | Kind | Technology | Talks |
|---|---|---|---|
| `risk-management-server` | **service** | `@grpc/grpc-js`, `stompit`, `json2csv` | serves gRPC on `0.0.0.0:50051`; consumes ActiveMQ/STOMP at `localhost:61613`, queue `newpolicies` |
| `risk-management-client` | **client** | `@grpc/grpc-js`, `commander` | calls gRPC at `localhost:50051` |
| `customer-management-frontend` | UI | `react`, `react-stomp` | `REACT_APP_*` to two backends; STOMP for chat and notifications |
| `customer-self-service-frontend` | UI | `react`, `react-stomp` | `REACT_APP_*`; STOMP for chat |
| `policy-management-frontend` | UI | `vue` | `VUE_APP_POLICY_MANAGEMENT_BACKEND` |

The one that matters architecturally is `risk-management-server`: a backend
service of the system, reached from `policy-management-backend` over a message
queue and from `risk-management-client` over gRPC.

## 2. Most of it is structured, so most of it needs no JavaScript parser

This is the finding that shapes the plan. Four inputs, three of them structured:

| Input | Holds | Parser |
|---|---|---|
| `riskmanagement.proto` | the gRPC contract: a service, an rpc, three messages | proto |
| `config.json` | hosts, ports, the queue name, the broker credentials | `json` |
| `package.json` | the technologies, by dependency; the component's name | `json` |
| `index.js`, `lib/*.js` | the wiring, and whether TLS is used | JavaScript |

```proto
service RiskManagement {
  rpc Trigger (TriggerRequest) returns (stream TriggerReply) {}
}
message TriggerReply {
  oneof report_or_progress { Report report = 1; int32 progress = 2; }
}
message Report { string csv = 1; }
```

```json
{ "activemq": { "host": "localhost", "port": 61613,
                "username": "queueuser", "password": "secret",
                "queueName": "newpolicies" },
  "grpc": { "host": "0.0.0.0", "port": 50051 } }
```

A `.proto` file is a better contract than an annotated Java class: it names the
service, its operations, their parameter and return types, and the structures
those types are. **It maps onto MRF's existing concepts without a single
extension** (§3). `config.json` gives the addresses the operation and technology
facts need. `package.json` identifies the technology deterministically — a
component depending on `@grpc/grpc-js` serves or calls gRPC, one depending on
`react` or `vue` is a user interface.

What is left for JavaScript is narrow: whether the gRPC server and client are
created with `createInsecure()`, and which queue a consumer subscribes to. Both
matter, and both are one call expression. §5 proposes what to do about them.

## 3. Mapping onto the existing model

No new concept and no new collection. The proto's vocabulary and MRF's line up:

| Proto | MRF concept | Phase |
|---|---|---|
| `package riskmanagement` | the qualified name's prefix | — |
| `service RiskManagement` | `Microservice("riskmanagement.RiskManagement", "RiskManagement", …)` | service |
| `rpc Trigger(…) returns (…)` | `Operation` on an `Interface` named after the service | service |
| the rpc's request type | `Parameter`, `ExchangePattern.IN` | service |
| the rpc's return type | `Parameter`, `ExchangePattern.OUT` | service |
| `stream` on either side | `CommunicationType.ASYNCHRONOUS` | service |
| `message Report { string csv = 1; }` | `DataStructure` with a `Field` per entry | domain data |
| `oneof` | a `DataStructure` whose fields are all optional, plus meta-data naming the group | domain data |
| `int32`, `string` | `PrimitiveType` | domain data |

The gRPC endpoint, the queue and the broker become meta-data in the shapes the
existing plugins already use:

```python
Data("Endpoint", {"address": "riskmanagement.RiskManagement"})  # on the interface
Data("ServiceProperties", {"serverPort": "50051"})  # on the node
Data(
    "MessageQueue",
    {
        "name": "newpolicies",
        "role": "consumer",
        "host": "localhost",
        "port": "61613",
        "scheme": "stomp",
    },
)
```

`ServiceProperties` is the name the Docker plugin already reports a port under,
so the operation side needs no new vocabulary either.

**A frontend becomes nothing.** LEMMA's Service DSL has no concept for a user
interface, and you already decided a frontend does not belong in the operation
model. Reconstructing one as a `functional microservice` would state something
false. What a frontend *does* hold is its outgoing links, which are north-south
traffic and out of scope for the security smell — so they are read and reported
as `ServiceCall` facts with `targetKind = EXTERNAL`, or left out entirely. §8
asks which.

## 4. Where the code goes

```
mrf/plugins/data/protobuf/      messages -> data structures      (domain phase)
mrf/plugins/service/protobuf/   service + rpcs -> microservice   (service phase)
mrf/plugins/service/node/       package.json, config.json, the wiring
mrf/utilities/protobuf.py       the proto vocabulary
mrf/utilities/node.py           dependency names, config keys
```

Two plugin selections rather than one, because they belong to different phases
and the handler's phases are hardcoded (ADR-0002 is still *Proposed*):
`PluginType.PROTOBUF` and `PluginType.NODE`. A system with a `.proto` and no Node
at all — a Java gRPC service — then needs only the first, which is the better
split than one plugin that does both.

`NODE` runs in the service phase after `PROTOBUF`, and attaches what it reads
from `config.json` and `package.json` to the microservice the proto produced,
following the two-step shape `DockerPlugin` and `CommunicationPlugin` both use.

## 5. The two things that need JavaScript, and three ways to get them

`grpc.ServerCredentials.createInsecure()` and `grpc.credentials.createInsecure()`
say the channel is plaintext — which is exactly the criterion of the smell
ADR-0009 serves. `channel.subscribe({destination: …})` says which queue is
consumed.

1. **A JavaScript parser.** `esprima` is pure Python and needs no build, but is
   ES5-era and would choke on modern syntax; `tree-sitter-javascript` is current
   but a native build. Either is a **new dependency**, so it needs asking about
   and an ADR.
2. **Infer from `package.json` and `config.json` alone.** `@grpc/grpc-js` with a
   `grpc.port` and no TLS configuration anywhere is plaintext in every case
   Lakeside Mutual has, and `config.json` names the queue. Deterministic, no
   dependency, and it states *less*: an inference from absence, not a fact read
   from a call.
3. **A token scan for the two call expressions**, pre-selected by file. The
   project's rule is real parsers, with regex only to pre-select candidates —
   `CLAUDE.md` and the smell task both say so — so this would be a deliberate
   exception for two fixed names.

**Recommended: 2 for the first step**, with the gRPC transport reported as
`UNRESOLVED` rather than `plaintext` where only absence supports it, and 1 as a
later step if the detail turns out to matter. That keeps the first step free of a
new dependency and free of a claim the sources do not make.

## 6. Tests

Fixtures under `tests/fixtures/`, each a minimal tree:

| Fixture | Covers |
|---|---|
| `protobuf-minimal` | a service, two rpcs, three messages, a nested `oneof`, `stream` on the reply |
| `protobuf-types` | every scalar proto type that maps onto a `PrimitiveType`, and one that does not |
| `node-service` | `package.json` + `config.json` + a `.proto`, the shape of `risk-management-server` |
| `node-frontend` | a `react` component with `REACT_APP_*`, asserting **no** microservice is reconstructed |

The expected output is written by hand from the fixture, per the
`add-golden-fixture` skill. The existing fixtures must not move: both plugins are
new and only run when selected, which is asserted rather than assumed.

### Smoke test

`docs/node-lakeside-mutual-results.md`, as for the communication plugin: what is
reconstructed for each of the five components and what is deliberately empty.
Expected — one new microservice, `riskmanagement.RiskManagement`, with one
interface and one operation; one new context with three data structures; a queue
fact; and nothing for the three frontends or the client.

## 7. What this changes about existing output

Worth knowing before it surprises anyone:

- **A fifth microservice and a fifth context appear.** Both are new documents, so
  nothing existing changes, but every consumer that counts them will see a
  different number.
- **`RiskManagementServerContainer` stops being skipped** in the operation model,
  because it will deploy a microservice. That is the point, and it means the
  operation model gains a container.
- **The container needs an operation environment the technology model declares.**
  Its Dockerfile is `node:16`, which `deployment_base.technology` already lists.
- **The strict deployment model demands `springApplicationName` and
  `serverPort`** of every container that deploys a service. A Node service has no
  `spring.application.name`. So either the Node plugin reports the two keys from
  `package.json` and `config.json` — defensible, the names are the technology
  model's, not Spring's — or the operation generator needs a second deployment
  technology for a node that is not a Spring service. **This is the one place
  where the step touches something that already works**, and §8 asks about it.

## 8. Open questions

1. **The frontends.** Reconstruct nothing at all, or their outgoing calls as
   `EXTERNAL` facts? Nothing is the honest default; the calls are real
   architecture information that no other plugin will ever see.
2. **`risk-management-client`.** A command line tool, not a service. Nothing, or
   a `utility` microservice? I would reconstruct nothing and record why.
3. **The deployment properties of a non-Spring container** (§7). Report
   `springApplicationName` from `package.json`'s name, or declare a second
   deployment technology? The first is a small lie with a tidy result; the second
   is honest and touches the technology model.
4. **A proto parser.** `grpcio-tools` ships `protoc` and is heavy;
   `protobuf` alone does not parse `.proto` source. A hand-written parser for
   proto3's `service`, `rpc`, `message` and `enum` is perhaps 150 lines and has no
   dependency — and proto3's grammar is small and stable enough that this is not
   the usual false economy. Which way?
5. **Scope of the first step.** Only `protobuf`, which yields the service, its
   operation and its data structures with no new dependency and no Node parsing
   at all? That is the smallest thing that makes `risk-management-server` appear
   in the models.

## 9. Steps

| Step | Content |
|---|---|
| 1 | `protobuf` plugin: messages into the domain phase, service and rpcs into the service phase. Fixtures `protobuf-minimal`, `protobuf-types`. No Node, no new dependency. |
| 2 | `node` plugin: `package.json` and `config.json` onto the microservice the proto produced — the gRPC port, the queue, the broker. Fixture `node-service`. Resolves §7's deployment question. |
| 3 | The frontends, per §8.1, and the smoke test. |
| 4 | Only if §5 says so: a JavaScript parser for `createInsecure()` and the subscription, behind an ADR. |

Step 1 stands alone: it is what makes the component visible, and nothing in it
depends on how the Node questions are answered.
