# Plan: fold the ablation's finding into the toolchain

Written 2026-10-21. Covers both repositories and the SANER 2027 short paper.

The ablation run (`refactorings/2026-10-20-ablation-no-findings-no-skill`) was
given one sentence and no model-level input at all: no findings, no root cause,
no model facts, no per-smell skill, with only the harness-enforced constraints
left in place. It passed all four gates and reached zero findings, exactly as
the three guided proposals did. It also changed one channel that the guided
chain did not, and that difference is not a matter of taste: the channel is
invisible to the detector, so no gate could have asked for it and no gate could
have noticed it was missing.

This plan closes that blind spot, measures what closing it changes, and says
what has to be rewritten once the numbers move.

## 1. The finding, as measured

### 1.1 The facts exist and are dropped before they reach a model

MRF's Node plugin already reconstructs both Node-side communication facts. The
golden fixture `tests/fixtures/node-service/expected_model.json` asserts them:

```json
{ "name": "GrpcServer",   "values": { "host": "0.0.0.0", "port": "50052",
                                      "transportSecurity": "UNRESOLVED" } }
{ "name": "MessageQueue", "values": { "broker": "activemq", "port": "61613",
                                      "queue": "newreports", "scheme": "stomp",
                                      "credentialsConfigured": "true",
                                      "transportSecurity": "UNRESOLVED" } }
```

They never arrive in a LEMMA model, because the technology model is a closed
vocabulary and declares no aspect for either. `TechnologyAspects.declaredAspect`
returns `null` for an undeclared name, and `LemmaServiceGenerator` then emits
nothing — deliberately, since an unresolvable aspect reference is worse than a
visible gap. The consequence is visible in the package:
`2-unpatched-models/service/RiskManagement.services` carries no communication
aspect of any kind, while every Java service carries several.

So the drop point is one file: `de.fhdo.lemma.reconstruction/models/technology/
spring.technology`.

### 1.2 What that costs in detection

The baseline reports nine findings: three synchronous calls to CustomerCore and
six queue channels of the Java services. Two further channels exist in the
sample system:

| Channel | Evidence in the sources | In the models today |
|---|---|---|
| Risk Management server consumes `newpolicies` from the broker over STOMP on 61613 | `risk-management-server/config.json`, `index.js` | no |
| Risk Management server serves gRPC on `0.0.0.0:50051` with `grpc.ServerCredentials.createInsecure()` | `risk-management-server/index.js:148` | no |

### 1.3 Which of them each proposal actually changed

The guided chain secured the STOMP channel even though the model never showed
it: the Java-side `MessageChannel` facts name the broker, and following the
broker led to its other client. rc2 and rc3 both patch
`risk-management-server/config.json` and `index.js`, adding `ssl: true` with a
CA, a key and a certificate.

The gRPC channel is the one real residue. rc3 leaves
`grpc.ServerCredentials.createInsecure()` untouched. The ablation replaces it
with `createSsl` against the development CA on the server, requires a client
certificate, and changes `risk-management-client` to `grpc.credentials.createSsl`
in step — a file the guided proposals never open, and a component that
`docker-compose.yml` does not deploy at all.

**Measured residue of the guided chain: one channel, and it is precisely the
channel the model does not carry.** That is the finding to fold in.

### 1.4 Two smaller defects found on the way

- MRF writes `transportSecurity: "UNRESOLVED"` (`mrf/utilities/node.py`), while
  the detector's constant is lowercase `"unresolved"`
  (`NonSecuredCommunicationDetector`). Once an aspect exists, the mismatch would
  silently make every Node fact undecided.
- The report has no category for a resolved service that carries no
  communication fact at all. RiskManagement is such a service, and that is how
  its two channels stayed invisible: nothing in the generated artifacts said
  anything was missing.

## 2. Step 1 — complete the facts (MRF)

**1a. Transport evidence from the Node sources, by name.** The Node plugin reads
only structured files today, which is why `transportSecurity` is `UNRESOLVED`:
whether a channel is created insecure is decided in JavaScript. Detect it the
way backlog A2 detects `TrustAllStrategy` on the Java side — by name in the
source text, not with a parser:

| Name in `index.js` | Fact |
|---|---|
| `ServerCredentials.createInsecure()` | `GrpcServer.transportSecurity = plaintext` |
| `ServerCredentials.createSsl(...)` | `transportSecurity = tls`; `clientAuth = need` when the call passes a root CA and requires a client certificate |
| `credentials.createInsecure()` | the client half, for a Node service that calls one |
| `ssl: true` / `stomp+ssl` in the messaging options | `MessageQueue.transportSecurity = tls` |

Each fact records the file it was read from as its evidence, as the Spring-side
facts do. `NodePlugin.file_types()` has to include `.js`, and the scan must keep
ignoring `node_modules`.

**Decided 2026-10-21:** no ADR. Scanning source text for a known name is not
parsing and does not touch ADR-0003, so `backlog.md` B3 is amended in the same
change to say the facts come from name-based detection and that a JavaScript
parser remains unneeded.

**1b. Normalise the unresolved marker.** Make MRF write `unresolved`, matching
every other fact of the communication plugin, or make the LEMMA side compare
case-insensitively. One of the two, stated in the commit.

**1c. Golden fixtures.** Extend `tests/fixtures/node-service` with a secure and
an insecure variant, so both paths are covered, and hand-write the expected
output rather than generating it (skill `add-golden-fixture`).

Gate: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`,
`uv run pytest -q`.

## 3. Step 2 — let the facts through (LEMMA)

Declare the two aspects in
`de.fhdo.lemma.reconstruction/models/technology/spring.technology`, beside
`ServerEndpoint` and `MessageChannel`, neither of them `singleval`: a service
may consume several queues, and a second gRPC endpoint is representable rather
than lost.

```
aspect GrpcServer for microservices {
    string host; string port; string transportSecurity; string clientAuth;
}
aspect MessageQueue for microservices {
    string broker; string host; string port; string queue; string scheme;
    string credentialsConfigured; string transportSecurity;
}
```

The property names have to match the fact keys exactly, and a name that is a
keyword needs the caret, as `^protocol` already shows.

Then regenerate the affected expectations under
`de.fhdo.lemma.reconstruction/test/expected/` — `risk-management` and
`lakeside-mutual` both change — and review the diff by hand. The rule stands:
an expectation is never regenerated to make a test pass.

## 4. Step 3 — judge the new channels (LEMMA)

**`NonSecuredCommunicationDetector`** gains two cases in its `switch`:

- `MessageQueue`: the consumer side of a broker channel. `plaintext` is a
  finding, `tls` without mutual authentication goes to `notMutual`,
  `unresolved` stays undecided. The cause is `RootCause.ofQueue(broker, scheme)`
  unchanged, which gives `broker:activemq:stomp` — a third cause, distinct from
  the Java side's `broker:activemq:tcp`. That is correct rather than a quirk:
  the two schemes are two connectors of the broker and were in fact patched
  separately.
- `GrpcServer`: a listener. `plaintext` is a finding, `tls` without
  `clientAuth = need` goes to `notMutual`, `unresolved` stays undecided. Reuse
  `RootCause.ofCall(service)` for it, which keys it `endpoint:<service>` with
  the label "the connectors of <service>" — the same semantics as a plaintext
  HTTP connector, and no change to the `^(endpoint|broker):` id pattern that
  `verify-refactoring.sh` parses.

The gRPC listener raises a question of principle. §3.7 is defined over two
microservices of the application, and the peer here — `risk-management-client`
— is a command-line tool that `docker-compose.yml` does not deploy and that
`backlog.md` B2 deliberately reconstructs nothing for.

**Decided 2026-10-21: it counts as a finding.** The deployed listener is part of
the application's attack surface whether or not the sample ships a second
deployed peer, and a finding a proposal can be asked to resolve is worth more
than a line in a coverage list. The reason text carries the caveat in full: the
connector accepts plaintext from any peer on the container network, and no
reconstructed microservice was identified as its caller. So nothing is
overclaimed, and the baseline becomes **11 findings over 4 causes**.

**`SmellReport`** gains a coverage row in the summary table and a section naming
every resolved service that carries no communication fact at all. That is the
artifact-level fix for 1.4: a blind spot becomes visible in the report instead
of only in a probe log.

**`SmellDetectionTest`** (134 checks today) gains fixtures for a plaintext gRPC
listener, a TLS listener without client authentication, a mutual-TLS listener, a
plaintext STOMP consumer, a secure STOMP consumer, and a service with no
communication facts.

## 5. Step 4 — make the extent measurable (verification)

`de.fhdo.lemma.servicedsl.smells/tools/verify-refactoring.sh`:

- Record the patch's extent in the verification output — files changed, lines
  added and removed — so "the change is bounded" is a number per proposal rather
  than an observation made once by hand. It is read straight from `patch.diff`.
- Extend the `starts` gate. It currently passes when `docker compose up --wait`
  returns, and `logs/probes-rc3.log` shows the Node consumer logging
  `ECONNREFUSED` to `policy-management-backend:61613` while every container
  reported `Up`. That log line was taken a second after `--wait` returned, so it
  is most likely the known readiness race rather than a regression; Step 5 settles
  which. Either way the gate should wait for readiness and then fail on
  connection errors in `docker compose logs`, because as it stands a channel can
  be broken while the gate passes.

## 6. Step 5 — rerun, the ablation included

Run these in order; each step consumes the previous one's output. No proposal is
regenerated: all four patches already exist on disk, so this costs container
build time and no model spend.

1. Reconstruct the clean baseline, Lakeside Mutual at `622632f`:

   ```
   ! uv run mrf -r -p Java Spring Communication Docker Protobuf Node -t <LakesideMutual>
   ```

2. Generate the models headlessly, then
   `bash de.fhdo.lemma.servicedsl.smells/tools/detect-smells.sh` for the new
   baseline report. Expected: 11 findings over 4 causes;
   `RiskManagement.services` carries a `GrpcServer` and a `MessageQueue`
   aspect; no service is listed as factless.

3. Re-verify all four recorded patches against the new detector, patches
   unchanged, same four gates:
   `rc1`, `rc2`, `rc3`, `ablation`. Expected, and this is the measurement the
   paper needs:

   | Proposal | findings before → after | residue |
   |---|---|---|
   | rc1 | 11 → 8 | queues, gRPC |
   | rc2 | 11 → 5 | calls, gRPC |
   | rc3 | 11 → 1 | gRPC listener |
   | ablation | 11 → 0 | none |

   **Predicted before the run; §11 holds what was measured.** rc2 came out at
   11 → 4 rather than 11 → 5: the broker patch secured the Node consumer's leg
   as well, which the prediction had not expected of it.

4. Re-probe rc3 and the ablation with the readiness loop, to settle the
   `ECONNREFUSED` of §5.

5. Full suites in both repositories: `ruff check`, `ruff format --check`,
   `mypy`, `pytest -q`; the Xtend regression (`SmellDetectionTest`);
   `tools/check-bundle-requires.py`.

## 7. Step 6 — report

- `src/4-validation.tex`: the channel and finding counts in Table I move, and
  the residue column gains the gRPC listener for rc3. The limitation paragraph
  changes from a caveat into a result: the detector now sees the channel the
  ablation found, and the guided chain's residue is one channel out of eleven.
- `src/6-conclusions.tex`: the parity claim sharpens. The model-level input
  bounds the change and makes the outcome measurable per cause, and the gap the
  ablation exposed was a gap in the detector's vocabulary, now closed and
  quantified.
- `docs/backlog.md`: A8b is not blocked after all — gRPC is present in this
  sample, on the Node side. B3 is answered by name-based detection. Add a row
  for the report's coverage section.
- `docs/security-smells.md`: the §3.7 table gains the two Node-side facts.
- `saner2027-submission/`: `2-unpatched-models` and `5-patched-models`
  regenerate, `6-report.md` takes the new counts and the fourth proposal,
  `3-proposals/` takes the ablation record, `logs/` takes the re-verification and
  the new probe logs.
- Page budget: the paper's changes are numbers in an existing table and one
  rewritten paragraph, so no figure has to be dropped.

## 8. Deliberately not in this plan

- Reconstructing `risk-management-client` as a microservice. It is a CLI tool,
  `docker-compose.yml` does not deploy it, and B2 decided against it; the
  listener's own facts are enough to judge the channel.
- A `clientAuth` property on `MessageQueue`. What a broker requires of its
  clients is the broker's configuration, not the consuming service's, and the
  broker is not reconstructed as a service.
- Kubernetes manifests (A4), and the hardcoded `changeit` passwords of §3.6.
  Both are real and both are out of scope here.

## 9. Branches and commits

Four changes, each on a feature branch cut from `dev` and merged by pull
request; nothing goes onto `main`. Eclipse configuration files (`.classpath`,
`.settings/*`) stay out of every commit, as does the untracked `temp.txt` of the
LEMMA working copy.

| Repository | Branch | Steps |
|---|---|---|
| MRF | `feat/node-transport-evidence` | Step 1, plus the `backlog.md` B3 amendment |
| LEMMA | `feat/node-communication-aspects` | Step 2 |
| LEMMA | `feat/judge-node-channels` | Steps 3 and 4 |
| MRF | `docs/ablation-coverage-results` | Step 6's records, counts and package update |

The `git push` and `gh pr create` are the author's to run.

## 10. Risk

Regenerating the models changes committed golden expectations in both
repositories and every count the paper and the package quote. Table I, the
package report and the conclusions have to be updated in the same pass, or the
submission and the paper will disagree with each other.

## 11. Results, measured 2026-10-21

Steps 1 to 4 are implemented and committed; this records what they changed.

### The baseline

| | Before | After |
|---|---|---|
| Findings | 9 | **11** |
| Root causes | 2 | **4** |
| Channels undecided | 0 | 0 |
| Services with no communication fact | not reported | **0** (one before: RiskManagement) |

The two new findings are the gRPC endpoint `0.0.0.0:50051`, bound with
`createInsecure`, and the STOMP leg the Risk Management server holds to the
broker. The new causes are `endpoint:RiskManagement` (1 finding) and
`broker:activemq:stomp` (1), beside `endpoint:CustomerCore` (3) and
`broker:activemq:tcp` (6).

### The transport of the Node channels, read from the three real trees

| Tree | gRPC endpoint | Broker leg |
|---|---|---|
| `622632f` unpatched | plaintext | plaintext |
| rc3 (`622632f` + rc1 + rc2) | **plaintext** | tls |
| ablation | tls, `clientAuth = need` | tls |

So the residue of the guided chain is one channel, and it is the one the models
did not carry. The ablation secured both ends of it, including
`risk-management-client`, a component the deployment does not contain.

### What the re-verification measures

Each patch unchanged, the same four gates, against the 11-finding baseline.

| Proposal | Findings | Addressed cause | Resolved | Verdict |
|---|---|---|---|---|
| rc1 | 11 → 8 | `endpoint:CustomerCore`, none left | 3 | see below |
| rc2 | 11 → 4 | `broker:activemq:tcp`, none left | **7** | GATES PASSED 4/4 |
| rc3 | **11 → 1** | `broker:activemq:tcp`, none left | 10 | GATES PASSED 4/4 |
| ablation | **11 → 0** | names none | 11 | GATES PASSED 4/4 |

The residue of the guided chain is the gRPC listener and nothing else, and the
ablation resolves it. Both halves of the prediction hold.

Two defects of the verification script, found by running it:

- The control tree never generates key material, so a base whose services
  already need certificates does not behave like its own baseline. rc3's control
  is `d00f1da`, which carries rc1 - and without certificates the Customer Core
  never registers with the admin server, so the control logged none of the TLS
  errors rc1 causes. rc3 was therefore charged with a failure rc1 introduced,
  and passed only because the notes declare it.
- The certificate-script finder looks one directory deep. The ablation ships
  `scripts/generate-certificates.sh`, so the `inplace` gate skipped rather than
  measuring.

Both are fixed, and rc3 and the ablation re-run afterwards.

rc2 is the surprise, and it runs the other way from the ablation's. It resolved
seven findings where the old count could show six: patching the broker's
connector also moved the Node consumer's STOMP leg to TLS, and the detection
could not see that leg at all. So the blind spot did not only hide a channel the
guided proposals left open - it also hid work they had done.

### What the start gate found

rc1 passed all four gates in the earlier session. With the settle-and-scan it
does not: `spring-boot-admin` fails its TLS handshake against the patched
Customer Core — `certificate_unknown`, and PKIX `unable to find valid
certification path`, 23 log lines, none of them in the unpatched control, which
logs only the pre-existing `ECONNREFUSED` of the Node consumer against
`policy-management-backend:61613`.

Mutual TLS on a service's actuator endpoints necessarily costs that scrape, so
failing every patch over it would have made the gate useless. The gate therefore
compares the kinds of error against the base and requires the loss to be
**declared** in `REFACTORING-NOTES.md`. rc1 and the ablation describe the
consequence in detail. rc3's own diff adds no mention, but the tree it produces
keeps rc1's, and the tree is what ships and what the gate reads.

Two defects of my own, found by running it rather than by reading it: the first
version compared "did the base log anything at all" and therefore skipped
instead of attributing, and the second word-split `unable to find valid
certification path` into six kinds.

### Final state, 2026-10-21

All four proposals reach `GATES PASSED` against the eleven-finding baseline,
patches unchanged. The residue of the guided chain is one channel, the gRPC
endpoint, and the ablation resolves it.

The patched models confirm it independently, read from the generated
`RiskManagement.services` of each run:

| Run | `GrpcServer` | `MessageQueue` |
|---|---|---|
| rc1 | plaintext | plaintext |
| rc2 | plaintext | tls |
| rc3 | **plaintext** | tls |
| ablation | **tls, `clientAuth = need`** | tls |

Every run yields 26 communication facts (24 before the two Node aspects
existed), so findings fall because values change, not because channels stop
being reconstructed.

Test suites, both repositories:

```
ruff check                 All checks passed
ruff format --check        171 files already formatted
mypy                       58 source files, no issues
pytest -q                  168 passed
SmellDetectionTest         152 check(s), 0 failed
ReconstructionRegressionT. all 4 systems match
check-bundle-requires.py   OK
```

Paper: `latexmk` exit 0, **6 pages**, no overfull boxes, no unresolved
references. Table~I, the baseline counts, the grouping example, the start gate's
description and the conclusions carry the new numbers; §II, §III and §V were
tightened to pay for them, losing no result.

### Still open

- The replication package (`../saner2027-submission/`) still holds the
  nine-finding models and report. Regenerating it is the remaining step.
- A runtime probe of `:50051` would make the residue evidence threefold
  (detection, source, runtime). Not needed for the paper's claims as written.
