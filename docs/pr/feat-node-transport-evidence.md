## Summary

Two things that cannot be separated without one of them losing its evidence:
the **last missing communication fact** of a Node service, and the **record of
the experiment that fact changed**.

Step 3 of `docs/node-plugin-plan.md`, backlog **B3**, and no JavaScript parser.
A Node service names an address in its configuration and decides the transport
in the code that opens the channel, so the fact stayed `UNRESOLVED` and the two
channels of Lakeside Mutual's Risk Management server reached no model and no
detection.

```diff
 GrpcServer    {host, port, transportSecurity: UNRESOLVED}
+GrpcServer    {host, port, transportSecurity: plaintext|tls, clientAuth: need,
+               valueSource: <file>}
 MessageQueue  {…, transportSecurity: UNRESOLVED}
+MessageQueue  {…, transportSecurity: plaintext|tls, valueSource: <file>}
```

**Read by name, not parsed.** `ServerCredentials.createInsecure` is a call, not
a property; so is `createSsl`, and its third argument is what makes the channel
mutual. The names are API of the libraries, a call to one of them is the
evidence, and `mrf/plugins/service/node/javascript.py` scans source text for
them exactly as backlog A2 reads `TrustAllStrategy` on the Java side. Scanning
for an API name is not parsing, so **ADR-0003 is untouched and no ADR was
needed**.

The fixture states both halves of the rule in one system:

```text
ingest.Ingest     GrpcServer    port 50061, transportSecurity plaintext
                  MessageQueue  queue batches, scheme stomp, plaintext
report.Report     GrpcServer    port 50062, transportSecurity tls, clientAuth need
                  MessageQueue  queue reports, scheme stomp, tls
```

### What the fact changed, measured

The detection on Lakeside Mutual read **nine** findings and said nothing about
two channels it had never looked at. With the fact declared on the LEMMA side it
reads **eleven over four root causes**: the three calls to `CustomerCore`, the
six queue channels over the broker's TCP connector, the gRPC endpoint bound with
`createInsecure`, and the STOMP leg the Node consumer holds to the same broker.

The gRPC endpoint is the sharper of the two. **It went through three proposals
unresolved** — it reached no model, hence no cause, hence no request — while the
unguided ablation secured it anyway. That is a difference no gate could see
while the detector could not see the channel either.

### The record that goes with it

`refactorings/` holds ten proposal folders and the probes. Each folder carries
the request, the constraints, the skill as it was at the time, the model excerpt
the proposal was given, the patch, the notes and the verification log. The logs
are **append-only**: `rc1` reads `VERIFIED`, then `GATES PASSED`, then
`REPAIR PARTIAL` as the verdict vocabulary was corrected under it, and every
re-verification is kept rather than overwritten.

| Record | Final verdict |
|---|---|
| `2026-10-13-rc1-customercore` | REPAIR PARTIAL |
| `2026-10-13-rc2-activemq-broker` | NOT VERIFIED |
| `2026-10-14-rc2-on-rc1-activemq-broker` | none — superseded, kept for provenance |
| `2026-10-20-ablation-truncated` | none — the run was cut off |
| `2026-10-20-ablation-no-findings-no-skill` | REPAIR PARTIAL |
| `2026-10-20-rc2b-activemq-broker` | REPAIR COMPLETE |
| `2026-10-20-rc3-rc2-on-rc1` | REPAIR COMPLETE |
| `2026-10-21-ablation-facts-withheld` | REPAIR COMPLETE |
| `2026-10-21-rc4-grpc-riskmanagement` | REPAIR COMPLETE |
| `2026-10-22-rc5-monitoring` | REPAIR COMPLETE |

Five documents state what those runs mean, and each is written so a reader can
check the claim rather than take it:

| | |
|---|---|
| `docs/experiment-protocol.md` | all ten generation runs **including the three not reported**, the thirty verification entries, the environment, and the seven defects found in the measuring apparatus itself |
| `docs/channel-inventory-lakeside-mutual.md` | every communication path of the system at `622632f`, enumerated from the sources **without consulting the reconstruction**: fourteen in scope, ten carried by the models, and the four that are not are all monitoring |
| `docs/monitoring-regression.md` | resolving the Customer Core's connector breaks the monitoring scrape, and **no finding reports it in either direction**; found through the declared-loss field, quantified by a runtime test, repaired by rc5 |
| `docs/contribution-delta.md` | what this adds that the predecessor workflow could not express, in numbers |
| `docs/ablation-coverage-plan.md` | the single-variable design the ablation runs follow |

## Evidence

```text
ruff          All checks passed!
ruff format   141 files already formatted
mypy          Success: no issues found in 58 source files
pytest        168 passed in 0.50s
```

`tests/test_node_transport.py` adds **12 checks** that each state one rule, and
`tests/fixtures/node-service-transport/` is a golden fixture whose expected model
was written by hand:

```text
a server that binds insecurely states plaintext
a server that requires a client certificate states it
tls without the third argument is not mutual
a source that binds no port leaves the transport unresolved
a connection without an ssl option is plaintext
a connection with an ssl option is protected
a broker address of a protected scheme is enough
a source that opens no connection leaves the transport unresolved
a secured grpc endpoint does not protect a plaintext queue
an ssl option too far from the connection is not read
the first source that states the transport decides
a bracket in an argument does not end it
```

The last four are the ones that make name-based reading defensible: an `ssl`
option outside `MESSAGING_WINDOW` of the connection it is supposed to belong to
is **not** read, and a secured endpoint does not launder a plaintext queue on
the same service.

Detection re-run live against the generated baseline models, with the deployment
compared as well:

```text
5 model(s) read.
11 finding(s), 0 protected, 0 encrypted but not mutually authenticated,
             0 not decidable from the models.
…
2 deployment node(s) deploy no reconstructed microservice, so no channel of
  theirs was judged:
    `SpringBootAdmin` — infrastructure node, eclipse-temurin:21-jre
    `Proxy` — infrastructure node, nginx
```

### Four things deliberately not claimed

- **A name reached through an alias or assembled at runtime is not seen**, and
  is reported `UNRESOLVED` rather than `plaintext`. Absence of a TLS call is not
  evidence of its absence in the program.
- **`valueSource` is a path, and it stays out of the generated models.** The
  reconstruction records the path it was given, which is absolute for a real
  run, and a generated model has to be identical on every machine. The evidence
  stays in the database where a finding can look it up.
- **A credential is never reported**, only that one is configured.
- **No TLS-positive path exists in either sample system.** Eleven services
  across Lakeside Mutual and park-and-charge, every one a plaintext main
  connector, so the `tls` and `clientAuth: need` branches are reachable only
  through the fixture.

### Why one pull request

The code change alone puts a fact into the database that **no technology model
declares**, and an undeclared aspect is dropped silently and by design — so on
its own it changes no generated model and no finding count. The eleven findings,
the four causes and every measurement in the five documents exist only with
LEMMA's `feat/node-communication-aspects` merged beside it. Splitting them would
leave one branch with a fact nothing reads and the other with a declaration for
a fact nothing produces.

## Merge Danger

**Door:** two-way. One new module, two plugins extended, one fixture, one test
file, and documents.

**Blast Radius:** Node services, and the lint configuration

- **The Node plugin only runs when `Node` is in the selection**, and it
  reconstructs no microservice of its own — it attaches to what another plugin
  produced. No Spring or Java path is reached.
- **`pyproject.toml` excludes `refactorings/` from ruff and the formatter.**
  Those files are recorded verbatim, including a patch's own trailing
  whitespace; formatting them would destroy the record. It is an exclusion of a
  directory that contains no importable code.
- **`CLAUDE.md` gained the Node plugin's description** in the architecture list.
- Nothing in `mrf/modules/` changed, so the persistence mapping and the model
  contract are untouched.

Two things are worth stating rather than implying:

- **The transport of a channel is read from whichever source states it first.**
  A service that binds two endpoints with different credentials in two files is
  not represented; the one test that covers the ordering asserts the rule rather
  than defending it as correct for every program.
- **`docs/experiment-protocol.md` carries a `TODO(author)`-shaped gap in its
  companion record** (`saner2027-evidence/5-execution-and-interventions.md`):
  whether any run was interrupted and resumed, and whether a patch was
  hand-edited after capture, is the author's to confirm. The protocol states
  what was observed; it does not claim that nobody touched anything.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
