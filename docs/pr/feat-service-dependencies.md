## Summary

What a service calls is only as precise as what its sources say, so the plugin
reports the two facts a consumer needs to state a dependency at the finest level
LEMMA allows.

```diff
 ServiceCall
+  targetQualifiedName: com.lakesidemutual.customercore.CustomerCore
+
+ServiceCallEndpoint
+  target: CustomerCore, verb: GetMapping, path: /customers/{ids},
+  method: getCustomer, file: …/CustomerCoreClient.java, line: 29
```

**Feign states its endpoints; the other HTTP clients do not.** A Feign client
declares what it calls the way a controller declares what it offers — a base path
on the interface, a mapping annotation on every method — so its endpoints are read
exactly. `RestTemplate`, `RestClient` and `WebClient` assemble the path in the
call expression, which puts the verb in a method name and the path in fragments.
Nothing is reported for them: a partial path cannot be matched to an operation of
the callee without guessing which one it meant, and the call itself is still
reported. **Two of Lakeside Mutual's three links are of that kind**, so this is
the common case rather than a corner.

The qualified name is reported because a reference to the callee in a LEMMA model
is qualified, and the generator sees one service at a time.

Reading a mapping annotation moves to `mrf/plugins/common/spring_mapping.py`, now
that both sides of a call need it. It hands back the annotation rather than its
name, so a fact cites the line the path was read from rather than the line of the
method below it.

## Evidence

Lakeside Mutual, `-p Java Spring Docker Communication -t <root> --replace`:

| Caller | Endpoints reported |
|---|---|
| CustomerManagement (Feign) | `GET /customers`, `GET /customers/{ids}`, `PUT /customers/{customerId}` |
| CustomerSelfService (RestTemplate) | none — call only |
| PolicyManagement (RestTemplate) | none — call only |

Each matches an operation of `customer-core` exactly, which the LEMMA side turns
into `required operations`.

```text
ruff    All checks passed!
mypy    Success: no issues found in 44 source files
pytest  83 passed          # 78 before
```

`s2s-placeholder` and `s2s-unresolved` gain a client with a base path and two
methods, so the join of `/api` and `/items` is covered, and five unit tests pin
`find_mapping` across all four shapes a mapping annotation takes.

One expectation in a fixture README was wrong and is corrected in the same change:
an unresolvable address does **not** suppress the endpoints. What is unknown there
is the transport, not the dependency — the annotation says which endpoint is
addressed either way.

## Merge Danger

**Door:** two-way. Additive meta-data; `targetQualifiedName` and the endpoint
entries are new keys and a new name, and every existing expectation changed by
addition only.

**Blast Radius:** microservice documents, when the Communication plugin is selected

**Merge before the matching LEMMA branch** — the LEMMA fixture's documents come
from this reconstruction, so its expected models assume these facts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
