# Plan: service-to-service dependencies in the service model

Status: **implemented**, MRF PR #7 and LEMMA PR #5, merged 2026-10-01.

Kept as the record of the design: what was read from the Service DSL before
anything was written, and the three constraints that decided the shape (§1).
Section 7 lists what the implementation does not reach, and section 9 the
questions it was built under.

When one service calls another's REST endpoint, say so in the generated LEMMA
service model, at the finest level that can be resolved: `required operations`
for the endpoint itself, falling back to `required interfaces` and
`required microservices`.

---

## 1. The target shape

LEMMA already has this repository's own hand-written model of Lakeside Mutual,
`examples/insurance-company/LEMMA models/`, and it is exactly what the
reconstruction should produce:

```
import microservices from "../customer-core/customerCore.services" as customerCoreServices

public functional microservice com.lakesidemutual.customerManagementBackend.CustomerManagementBackend {
    required microservices { customerCoreServices::com.lakesidemutual.customercore.CustomerCore }

    interface customerCoreClient { … }
}
```

So the generated `CustomerManagement.services` should gain:

```diff
 import technology from "../technology/spring.technology" as javaWithSpring
 import datatypes from "../domain/CustomerManagement.data" as CustomerManagement
+import microservices from "CustomerCore.services" as CustomerCore

 @technology(javaWithSpring)
 @javaWithSpring::_aspects.ServiceCommunicationTransport(transport = "plaintext")
 public functional microservice com.lakesidemutual.customermanagement.CustomerManagement {
+    required operations {
+        CustomerCore::…CustomerCore.CustomerInformationHolder.getCustomers,
+        CustomerCore::…CustomerCore.CustomerInformationHolder.getCustomer,
+        CustomerCore::…CustomerCore.CustomerInformationHolder.updateCustomer
+    }
+
     @endpoints(javaWithSpring::_protocols.rest:"/notifications";)
     interface NotificationInformationHolder { … }
 }
```

### Endpoint level is what LEMMA offers, and what this aims at

The Service DSL has three levels, in this order inside the microservice body:

```
required microservices { … }
required interfaces   { … }
required operations   { … }
```

`required operations` is the endpoint level: a reference to one operation of one
interface of one microservice. For Lakeside Mutual's Feign client that resolves
exactly (§3), so the generated `CustomerManagement.services` can state which
three endpoints of `customer-core` it calls:

```
import microservices from "CustomerCore.services" as CustomerCore

public functional microservice com.lakesidemutual.customermanagement.CustomerManagement {
    required operations {
        CustomerCore::com.lakesidemutual.customercore.CustomerCore.CustomerInformationHolder.getCustomers,
        CustomerCore::com.lakesidemutual.customercore.CustomerCore.CustomerInformationHolder.getCustomer,
        CustomerCore::com.lakesidemutual.customercore.CustomerCore.CustomerInformationHolder.updateCustomer
    }
    …
}
```

An operation is named by `Operation.qualifiedNameParts`, which is its interface's
qualified name plus its own: microservice, interface, operation.

**The levels are alternatives, not layers.** `warnAlreadyRequired` fires for an
interface whose microservice is also required, and for an operation whose
interface or microservice is also required. Emitting two levels for one callee
warns on every link. So the generator emits the **most precise level that
resolves** and falls back: operation → interface → microservice.

**What may be required at all** (`Microservice.canRequire`, consulted by the
scope provider, so a reference that fails it does not resolve):

| Level | Requirable when |
|---|---|
| Microservice | it is not the requiring service itself, and not `internal` |
| Interface | not `noimpl`, not effectively `internal`, not one of the requiring service's own |
| Operation | not effectively `noimpl`, not effectively `internal`, not one of the requiring service's own |

`noimpl` is the one that bites: the reconstruction marks an operation `noimpl`
when a parameter's type could not be resolved, and such an operation **cannot be
required**. No operation of the current Lakeside Mutual models is `noimpl`, so
all three above are requirable — but that was not true before the technology
types resolved `ResponseEntity`, so the fallback has to handle it rather than
assume it away.

`warnNoImplementedOperations` additionally warns when a required microservice or
interface defines no implemented operation. Our `CustomerCore` has them, so it
stays quiet.

---

## 2. What already exists

**The dependency itself is already reconstructed.** The communication plugin
(ADR-0009) writes, on each calling microservice:

```json
{"name": "ServiceCall", "values": {
  "target": "CustomerCore", "targetKind": "SERVICE", "scheme": "http",
  "technology": "Feign", "property": "customercore.baseURL",
  "resolvedUrl": "http://localhost:8110",
  "file": "…/CustomerCoreClient.java", "line": "20", "snippet": "@FeignClient(…)"}}
```

`target` is already resolved to the name of a reconstructed microservice, and
`targetKind` already separates a service of the system from a third party. A
`ServiceCall` with `targetKind = SERVICE` **is** the dependency.

So the service-level step needs **no new reconstruction**, only one missing
value and the LEMMA side.

**What is missing for the service level:** the callee's *qualified* name.
`required microservices` takes `Import::<qualified name>`, and
`LemmaServiceGenerator.generateModelFrom` receives one microservice at a time,
so it cannot look up what `CustomerCore` is qualified as. MRF has it at hand —
the plugin resolved the target against a specific `Microservice` object — so it
should report it:

```diff
 ServiceCall values
   target: CustomerCore
+  targetQualifiedName: com.lakesidemutual.customercore.CustomerCore
```

One line in `CommunicationPlugin.__known_targets` / `__to_data`, additive, no
schema change.

**What is missing for the endpoint level:** which endpoint is called. Section 4.

---

## 3. Matching a call to the callee's endpoint

Checked against Lakeside Mutual, and it resolves exactly:

| Caller: Feign method | Callee: reconstructed endpoint |
|---|---|
| `@GetMapping("/customers")` | `CustomerInformationHolder` base `/customers`, operation `getCustomers` (no own address) |
| `@GetMapping("/customers/{ids}")` | base `/customers` + `/{ids}` → `getCustomer` |
| `@PutMapping("/customers/{customerId}")` | base `/customers` + `/{customerId}` → `updateCustomer` |

Each one identifies a single operation of the callee, which is the endpoint
level. All three happen to land in one interface, so the interface level is
derivable from the same match as a fallback.

**The rule:** concatenate the callee's interface endpoint address with its
operation's address, normalise both sides, and match on the HTTP verb and the
path.

Normalisation, because a path template names its variables on each side
independently — the caller may write `/{id}` where the callee writes
`/{customerId}`:

```
/customers/{ids}        -> GET /customers/{}
/customers/{customerId} -> PUT /customers/{}
```

Every `{…}` segment becomes `{}`, trailing slashes go, and a missing operation
address contributes nothing. An ambiguous result — two operations of the callee
normalising to the same verb and path — resolves to the interface rather than
the operation, and if even that is ambiguous, to the microservice.

This matching belongs on the **LEMMA side**: it needs both models at once, and
the wizard already holds every reconstructed microservice. MRF reconstructs one
service at a time and should not start resolving across them.

---

## 4. MRF work

### 4.1 The callee's qualified name (service level)

`CommunicationPlugin`: carry `targetQualifiedName` on a `ServiceCall` whose
`targetKind` is `SERVICE`. `__known_targets` already maps a normalised name to
`microservice.name`; it becomes a map to the microservice itself, or to a pair.

### 4.2 The called endpoint (endpoint level)

A new detector output: per call, the endpoints the caller declares it will hit.

**Feign is exact.** The client is an interface whose methods carry the same
mapping annotations a controller's do, and `SpringPlugin` already knows how to
read them (`REST_OPERATIONS`, `MAPPING_PATH_ELEMENTS`,
`__reconstruct_endpoint`). The detector reads the interface's own
`@RequestMapping` as a base path, then each method's verb and path:

```json
{"name": "ServiceCallEndpoint", "values": {
  "target": "CustomerCore", "verb": "GetMapping", "path": "/customers/{ids}",
  "method": "getCustomer",
  "file": "…/CustomerCoreClient.java", "line": "28", "artifactType": "SOURCE"}}
```

One entry per called endpoint, flat, one evidence each — the same shape
constraint ADR-0009 settled, so no schema change and no new ADR.

**RestTemplate and the other HTTP clients are not.** The path is assembled in
the call expression:

```java
restTemplate.getForObject(customerCoreBaseURL + "/customers/" + ids, …)
```

A literal fragment is recoverable; the whole path is not, and the verb is in the
method name (`getForObject`, `exchange(…, HttpMethod.PUT, …)`) rather than in an
annotation. Options, in order of honesty:

1. **Recover nothing** for these clients. The link stays at service level.
2. Recover the verb from the method name and the literal fragments, and report
   the path as a prefix with a marker. A *partial* path cannot be matched
   against a callee endpoint without guessing which operation it is.

**Recommended: 1.** Two of Lakeside Mutual's three links are `RestTemplate`, so
this is not a corner case — it is the common case, and a service-level
dependency that is certainly true beats an operation-level one that is probably
wrong. Section 7 records what would change that.

### 4.3 Where the code goes

No new plugin. `mrf/plugins/service/communication/detectors/feign.py` grows the
endpoint reading; `mrf/utilities/communication.py` grows the meta-data name and
keys. `SpringPlugin`'s endpoint helpers move to a shared place if the duplication
is more than a few lines — checked first, not assumed.

---

## 5. LEMMA work

### 5.1 The generator needs every microservice, not one

`LemmaServiceGenerator.generateModelFrom(Microservice, String)` takes one
reconstructed microservice. To emit `required interfaces` it has to see the
callee's interfaces and their endpoints.

Smallest change that does it: an optional second input, the other reconstructed
microservices, used only to resolve a dependency:

```xtend
def ServiceModel generateModelFrom(Microservice reconstructedMicroservice,
    String technologyFolder, List<Microservice> otherMicroservices)
```

The existing two-argument form delegates with an empty list, so nothing that
calls it today changes. `LemmaReconstructionHandler` already iterates all of
them, so it has the list.

### 5.2 Emitting the dependency

- An import of the callee's service model, `import microservices from
  "<Callee>.services" as <Callee>`. `LemmaOperationGenerator.serviceImportFor`
  is the precedent; the service generator's `getOrCreateImport` currently only
  makes `datatypes` imports, so it gains a sibling. Both models sit in the same
  `service/` folder, so the URI is the bare file name.
- `requiredMicroservices` or `requiredInterfaces`, per §1 — never both for the
  same callee.
- A detached `Microservice`/`Interface` carrying the right name, as the generator
  already does for types, protocols and aspects. What matters is the text the
  extractor writes; the reference resolves when the written file is re-parsed.

### 5.3 The extractor prints neither today

`ServiceDslExtractor.generate(Microservice)` writes the body as

```xtend
«preamble» microservice «service.lemmaName» {
    «FOR iface : service.interfaces SEPARATOR '\n'»…«ENDFOR»
}
```

and never looks at `requiredMicroservices`, `requiredInterfaces` or
`requiredOperations`. All three need printing, in the grammar's order, before the
interfaces — the fourth gap of this kind in that file, after interface endpoints,
interface aspects and microservice aspects.

An interface is named by its `qualifiedNameParts`, which the scope provider
builds as the microservice's qualified name plus the interface name:
`CustomerCore::com.lakesidemutual.customercore.CustomerCore.CustomerInformationHolder`.

---

## 6. Tests

**MRF.** A fixture where the caller declares a Feign client with two mapped
methods and the callee is a controller with matching endpoints, asserting the
`ServiceCallEndpoint` entries and `targetQualifiedName`. Extend `s2s-placeholder`
rather than adding a system: it already has a Feign client and a callee.
Determinism is covered by the existing per-fixture test.

**LEMMA.** The `lakeside-mutual` fixture already holds all four services, so its
expected models become the test: `CustomerManagement.services` gains the import
and the `required` entry, `CustomerCore.services` gains nothing. The three
`RestTemplate` callers show the service level, the Feign caller the interface
level — one fixture covering both outcomes.

The matching rule itself wants unit tests of its own on the normalisation:
`/customers/{ids}` vs `/customers/{customerId}` match, `/customers` vs
`/customers/{id}` do not, a trailing slash is irrelevant, and an ambiguous
callee falls back.

---

## 7. Limits, stated before they are discovered

- **Two of Lakeside Mutual's three links stay at service level**, because
  `RestTemplate` assembles its paths. The interface level will look
  under-exercised on this system; that is the system, not the rule.
- **A call the communication plugin does not find produces no dependency.** The
  Spring Boot Admin registration, which lives only in `docker-compose.yml`, is
  the known example.
- **A `noimpl` operation cannot be required**, so a callee whose operation could
  not be fully typed drops that link to the interface or the microservice level.
  None of Lakeside Mutual's are `noimpl` today; before the technology types
  resolved `ResponseEntity`, one was.
- **Transitive dependencies are not inferred.** Only calls that were found.
- **A cyclic dependency** would be emitted as found. Two service models importing
  each other is legal in LEMMA; if the editor disagrees, that is worth knowing
  and is checked before this is called done.

---

## 8. Steps

| Step | Content |
|---|---|
| 1 | MRF: `targetQualifiedName` on a `SERVICE` call. LEMMA: microservices import, `requiredMicroservices`, extractor printing the three `required` blocks. **Service level, end to end.** |
| 2 | MRF: `ServiceCallEndpoint` from a Feign client's methods, with a fixture. |
| 3 | LEMMA: the matching rule, then `requiredOperations` where an endpoint resolves, `requiredInterfaces` where only the interface does, `requiredMicroservices` otherwise. Expected models of `lakeside-mutual` updated. |

Step 1 is worth having on its own: it is small, it needs no matching, and it
produces the shape the hand-written reference model uses.

---

## 9. Open questions

1. **Is step 1 worth shipping on its own**, or should the first visible output
   already be the endpoint level? Step 1 is small and produces the shape the
   hand-written reference model uses, but it states less than the sources give,
   and the three `RestTemplate` links never get beyond it anyway.
2. **The Feign client as an interface of the caller.** The reference model also
   turns `CustomerCoreClient` into `interface customerCoreClient { … }` on the
   *calling* service — a client-side contract, which our reconstruction does not
   produce at all, because `SpringPlugin` only reads `@RestController`. That is a
   separate feature from a dependency; worth its own decision rather than being
   folded in here.
3. **Does this need an ADR?** No persistence or model change — the facts are
   meta-data, as ADR-0009 settled. The LEMMA generator's signature change is
   internal. I would not write one, but the cross-model resolution in §3 is a
   new kind of thing for that generator and could be recorded.
