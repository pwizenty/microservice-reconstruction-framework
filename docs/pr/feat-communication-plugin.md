## Summary

First step towards the security smell **Non-Secured Service-to-Service
Communications**: which transport a service uses to call the other services of
the system. Facts only — the smell decision stays with the LEMMA validation.

```text
mrf/plugins/service/communication/
├── communication_plugin.py   # attaches the facts to the microservices
├── configuration.py          # ${…} -> application*.properties / *.yml
├── urls.py                   # reading an address, and the evidence for it
└── detectors/                # one per client technology
    ├── feign.py              # @FeignClient, address on the annotation
    └── rest_template.py      # RestTemplate / RestClient / WebClient
```

```diff
 microservice CustomerManagement
   data: [public, functional,
+   ServiceCall {target: CustomerCore, targetKind: SERVICE, scheme: http,
+                technology: Feign, property: customercore.baseURL,
+                resolvedUrl: http://localhost:8110,
+                file: …/CustomerCoreClient.java, line: 20, snippet: "@FeignClient(…)"},
+   ServiceCommunicationTransport {transport: plaintext}]
```

`transport` is `plaintext`, `tls`, `mixed` or `unresolved` — an **aggregation** of
the observed schemes, not a verdict. Deciding the smell additionally needs what
the callee accepts and whether a mesh protects the channel, neither of which this
step reconstructs. **A call of unknown transport makes the aggregate
`unresolved`, never `tls`**: reporting it as encrypted would claim what the
sources do not state.

Facts are `Data` meta-data rather than new concepts, so the step is additive —
no collection, no module, and a LEMMA bundle that is not rebuilt ignores them.
See ADR-0009 (Proposed) for why, and for the one ceiling that follows: `values`
is flat, so a fact carries one evidence record.

## Evidence

Lakeside Mutual, `-p Java Spring Docker Communication -t <root> --replace`, no
`UNRESOLVED` value:

| Source | Target | Kind | Scheme | Technology |
|---|---|---|---|---|
| CustomerManagement | CustomerCore | SERVICE | `http` | Feign |
| CustomerSelfService | CustomerCore | SERVICE | `http` | RestTemplate |
| PolicyManagement | CustomerCore | SERVICE | `http` | RestTemplate |

`CustomerCore` calls nobody and gets no aggregate. All three address
`http://localhost:8110`; the port is `customer-core`'s `server.port`, so the
target is reported under the name the reconstruction knows and the literal
address stays in `resolvedUrl` and the evidence.

```text
ruff    All checks passed!
mypy    Success: no issues found in 43 source files
pytest  78 passed          # 57 before
```

Five fixtures, each failing without the behaviour it covers, plus a determinism
test per fixture:

- `s2s-plaintext` literal URL; a service that calls nobody gets no aspect
- `s2s-placeholder` Feign + placeholder from `application.properties`, over TLS
- `s2s-unresolved` one unknown call makes the aggregate `unresolved`, not `tls`
- `s2s-excluded` XML schema host, test code, external target, and an
  unresolvable `@Value` that is deliberately **not** a call
- `s2s-mixed` one `http` and one `https` peer

`docs/s2s-lakeside-mutual-results.md` records the run and, explicitly, what it
does not find: the Spring Boot Admin registration, which lives only in
`docker-compose.yml` and needs the step that reads the deployment.

## Merge Danger

**Door:** two-way. Nothing existing changes; the plugin only runs when selected
with `-p … Communication`, which is asserted rather than assumed.

**Blast Radius:** microservice documents, when the plugin is selected

**Merge after `feat/rest-technology-information`** — this branch contains its
commit, because the plugin needs `get_annotation_values` from it.

Known limits, all of which yield `UNRESOLVED` or a recorded fact rather than a
guess: ljavalang resolves no symbols, so a call is recognised only where the
address and the call site are in the same class (the remote-proxy shape); for the
HTTP clients the unit of detection is therefore the class, so a class that
injects an address it does not call would still be reported, with the line as
evidence.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
