## Summary

Backlog item **A1**: the server half of *Non-Secured Service-to-Service
Communications*. The detectors already reconstruct what a client calls and with
which scheme; this reconstructs what the callee accepts.

```text
mrf/plugins/service/communication/
├── detectors/              what a client calls, and with which scheme   (had)
└── server.py               what the service itself answers on          (new)
```

```diff
 # the two halves now sit on the same microservice
 ServiceCommunicationTransport  transport = plaintext      ← the caller
+ServerEndpoint                 port = 8110, tlsEnabled = false  ← the callee
```

**One record per connector**, not the `additionalPlaintextPort` field the task
document named. Each record says which connector it is and whether it uses TLS,
so a plaintext management port beside a TLS main port is two records, a third
connector needs no new field, and the management connector's own TLS and
client-auth settings have somewhere to go:

```text
ServerEndpoint  connector=server      port=8443  tlsEnabled=true   clientAuth=need
ServerEndpoint  connector=management  port=9001  tlsEnabled=false
```

## Evidence

**The facts are emitted before the guard that skips a service with no outgoing
calls.** A service that calls nothing still answers on a port, and that is the
half of the smell it contributes:

```text
CustomerCore          ServerEndpoint 8110 plaintext    (no transport fact — it is the callee)
CustomerManagement    ServerEndpoint 8100 plaintext  + transport=plaintext
CustomerSelfService   ServerEndpoint 8080 plaintext  + transport=plaintext
PolicyManagement      ServerEndpoint 8090 plaintext  + transport=plaintext
```

Three services call `CustomerCore` over plaintext and `CustomerCore` accepts
plaintext. That is the complete picture the smell rule needs, as facts, with the
judgement left to the LEMMA validation (ADR-0009).

**Four rules, each a way of being wrong:**

```diff
 # Spring's server.ssl.enabled defaults to true
-tlsEnabled = (server.ssl.enabled == "true")        # a key store without
+enabled decides when set; else a key store or an    # enabled would read
+SSL bundle does                                     # as plaintext

 # the text of a placeholder is not a port
-port = "${PORT}"
+port = "unresolved"       when the service does not resolve it

 # an unconfigured port is Spring's, and says so
+port = "8080", defaulted = true

 # a fact the sources do not state is not a fact
-clientAuth = "none"       Spring's default
+clientAuth absent
```

**Measured, and it decides what can be tested at all.** Neither sample system
configures TLS anywhere:

```text
Lakeside Mutual    5 services   server.port only, properties form
park-and-charge    6 services   server.port only, YAML form
                   ─────────
                   11 services, every one a plaintext main connector,
                   no management port anywhere
```

So the plaintext case — the one the smell turns on — is covered by real code in
both configuration formats, and **every TLS-positive path is reachable only
through a fixture**. `tests/fixtures/s2s-server-connectors` is the two-connector
case, its expected output written by hand from the properties file rather than
generated from the plugin.

Worth carrying forward: **A2's positive cases will be fixture-only for the same
reason.**

```text
15 unit tests, each naming what it would catch
 5 existing golden fixtures extended — purely additive, diff reviewed
   before regenerating, 105 insertions and 9 trailing-comma changes
 1 golden fixture added for the two-connector case
138 passed | ruff clean | mypy clean
```

Verified against the real system end to end, with `-r` and all six plugins:

```text
5 contexts, 5 microservices, 11 operation nodes
ServerEndpoint on all four Spring services
```

## Merge Danger

**Door:** two-way. One new module, one method on an existing plugin, and
constants.

**Blast Radius:** the `microservice` collection, and anything reading it

Every microservice whose module has a Spring configuration gains one
`ServerEndpoint` entry per connector in its `data`. The seam stays as ADR-0009
requires it — a flat `Map<String, String>`, so `tlsEnabled` is the text
`"false"` rather than a boolean, and the LEMMA side turns it back where a
technology model asks for one. Nothing existing changes shape, so a consumer
that ignores unknown meta-data is unaffected; `MongoDbRepository` on the LEMMA
side binds with `FAIL_ON_UNKNOWN_PROPERTIES=false` and does.

A module with no configuration at all yields nothing rather than Spring's
default port — `RiskManagement`, the Node service, is such a module, and
claiming a port it was never configured with would be an invention.

The LEMMA side that makes this visible in a service model is a separate pull
request against `pwizenty/lemma`. **Re-run MRF before regenerating models**: the
aspect only appears for documents that carry the fact, so a stale database
yields a model without it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
