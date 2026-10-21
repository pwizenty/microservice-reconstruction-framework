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
