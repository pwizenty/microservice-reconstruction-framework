# Experiment protocol

Every generation run of this work, in order, including the three that are not
reported; every verification run and why there are several per proposal; the
environment; the defects found in the measuring apparatus itself; and a
consolidated view of what the evidence does and does not establish.

Written so that a reader can tell a measurement from a claim without reading
the code.

## 1. How a proposal is produced

Identical for every run below unless the row says otherwise.

1. A worktree is created from a named base commit of the sample system. The
   patch is never applied to the original checkout.
2. The request has three layers: `constraints.md` as an appended system prompt,
   a smell-specific skill, and the finding with its evidence quoted from the
   reconstructed models. All three are kept verbatim in the record.
3. The model runs through the Claude Code CLI with a tool whitelist
   (`Read, Edit, Write, Grep, Glob, TodoWrite`, and `Bash` restricted to
   `./mvnw`, `keytool`, `openssl`, `bash`, `chmod`, `npm`, `node`,
   `git diff`), `--permission-mode acceptEdits`, inside the worktree.
4. The result is captured as `git diff --cached --binary` into `patch.diff`,
   and the session record into `result.json`.
5. The proposal is verified by `verify-refactoring.sh`, which measures against
   a baseline taken before patching, and the verdict is appended to
   `verification.md`.

**The generation runs used this CLI harness, not the Eclipse quick fix.** The
quick fix assembles the same three layers and additionally calls `PatchGuard`
before anything acts on the patch (`ProposeRefactoringJob.xtend:68`); the
harness does not. Running the guard over the seven recorded patches afterwards
gives six clean results and one hit on rc3, which is a **false positive**: the
string `rejectUnauthorized: false` appears twice in explanatory prose, once in
`REFACTORING-NOTES.md` and once in a source comment that says there is
deliberately no such setting. A textual check of added lines cannot tell code
from a comment about code.

## 2. Generation runs, in order

| Date | Run | Base | Input | CLI | Turns | Duration | Cost | Outcome |
|---|---|---|---|---|---|---|---|---|
| 10-13 | **rc1** `rc1-customercore` | `357ca2d`, reassessed on `622632f` | finding, cause `endpoint:CustomerCore`, skill | 2.1.286 | 144 | 1 495 s | \$10.62 | reported |
| 10-13 | rc2, first attempt | `357ca2d` | finding, cause `broker:activemq:tcp`, skill | 2.1.286 | 100 | — | \$6.55 | **NOT VERIFIED**: the clean gate failed, its tests required generated key material. Superseded by rc2b, kept for provenance |
| 10-14 | rc2-on-rc1, first attempt | `357ca2d` | as above, on rc1 | — | 135 | — | \$11.89 | superseded: generated without the intended skill. Kept for provenance |
| 10-20 | **rc2** `rc2b-activemq-broker` | `622632f` | finding, cause `broker:activemq:tcp`, skill | 2.1.292 | 153 | 1 042 s | \$11.60 | reported |
| 10-20 | **rc3** `rc3-rc2-on-rc1` | `d00f1da` | as above, on rc1 | 2.1.292 | 162 | 1 250 s | \$12.64 | reported |
| 10-20 | generic, first attempt | `622632f` | one sentence, no findings, no skill | 2.1.292 | 114 | 1 027 s | \$8.03 | **truncated** by an account spend limit, `is_error=True`, 21 tool denials. Not evidence |
| 10-20 | **generic** `ablation-no-findings-no-skill` | `622632f` | one sentence, no findings, no skill | 2.1.292 | 294 | 2 064 s | \$27.60 | reported |
| 10-21 | **facts-held** `ablation-facts-withheld` | `622632f` | skill, constraints, named callee; **aspect values withheld** | 2.1.292 | 215 | 1 499 s | \$18.03 | reported |
| 10-21 | **rc4** `rc4-grpc-riskmanagement` | `aed2cfb` | finding, cause `endpoint:RiskManagement`, skill with a gRPC recipe added first | 2.1.292 | 90 | 503 s | \$4.12 | reported |
| 10-22 | **rc5** `rc5-monitoring` | `be2fe7f` | **no finding**: a declared peer loss and a runtime measurement | 2.1.292 | 140 | 1 053 s | \$8.07 | not in the paper |

Ten runs, seven recorded as patches, six reported in the paper, one (rc5)
measured afterwards. **No run was repeated under identical conditions**, so
nothing here supports a statement about variability between runs of the same
request.

## 3. Verification runs

Thirty verification entries across the records, between 2026-10-14 and
2026-10-22. A proposal has several because the measuring apparatus changed, not
because the patch did:

| Why a re-run happened | When |
|---|---|
| gates were added — the start gate did not exist at first | 10-14 |
| the verdict vocabulary was renamed `VERIFIED` → `GATES PASSED` | 10-20 |
| the detection was extended to the Node channels, raising the baseline from nine findings to eleven; **all proposals were re-verified against the final detector** | 10-21 |
| the verdict was split into `REPAIR COMPLETE` and `REPAIR PARTIAL`, so a declared peer loss stops reading like no loss | 10-21 |
| the coverage field was corrected to read the patch's own notes instead of the tree's | 10-22, rc4 only |

The numbers the paper reports are the **final** entry of each record. Earlier
entries are kept because a verification record is append-only: deleting a
measurement would misreport what was run.

## 4. Environment

| | |
|---|---|
| MRF | `7a7293d`, branch `feat/node-transport-evidence` |
| LEMMA | `454f03a4`, branch `feat/detection-coverage-report` |
| Model | `claude-opus-5` |
| CLI | 2.1.286 for rc1 and the two first attempts, 2.1.292 afterwards |
| Docker | 29.8.2 |
| Sample | upstream `357ca2d`, evaluated on `622632f` (container base image replaced) |
| Machine | one developer machine, macOS; every run sequential |

## 5. Defects found in the measuring apparatus

Recorded because each one invalidated a measurement before it was fixed, and a
protocol that hides them is not a protocol.

| Defect | Effect | Fixed |
|---|---|---|
| The start gate compared *whether* the base logged anything, not *what* | rc1's real breakage was masked | error kinds compared as sets |
| Word splitting broke multi-word error kinds | one kind became six | kinds stored one per line |
| The control tree generated no key material | rc3 was charged with rc1's breakage | material generated for the control too |
| The certificate script was found only one directory deep | one ablation's `inplace` gate skipped and `starts` failed | lookup to two levels |
| The probe harness used `timeout`, absent on macOS | the 10-20 rc3 probe produced no usable output | probes rewritten and re-run 10-22 |
| The coverage field read the tree's notes | rc4 inherited rc2's declaration | reads the patch's added lines |
| A probe used identical payloads for both arms | the negative control was inconclusive | payloads tagged per mode |

## 6. The evidence, consolidated

### Model level — what detection reports

| Tree | Findings | Verdict |
|---|---|---|
| unpatched `622632f` | **11** over four causes | — |
| rc1 | 8 | repair partial, monitoring declared lost |
| rc2 | 4 | repair complete |
| rc3 (rc2 on rc1) | 1 | repair complete |
| rc4 (on rc3) | **0** | repair complete |
| generic | **0** | repair partial, monitoring declared lost |
| facts-held | 8 | repair complete |
| rc5 (on rc4) | 0 | repair complete |

*Does not establish:* that every interaction survived, nor that an unreported
channel is secure. Four monitoring relationships are outside model-level
detection entirely.

### Transport level — what the probes show

| Channel | Evidence | Result |
|---|---|---|
| Customer Core connector | HTTP probes on rc3 | plaintext 400; TLS without a client certificate aborted at the handshake; with one, an application answer |
| ActiveMQ, STOMP | tagged events, three modes | with a certificate `CONNECTED` and one event consumed; without, and in plaintext, nothing delivered; the broker logs `certificate_required` |
| gRPC endpoint | three credential modes after rc4 | mutual TLS returns the report; TLS without a client certificate and plaintext are refused |
| Broker connectors | the broker's own log | `ssl://` and `stomp+ssl://` with `transport.needClientAuth=true`, no plaintext connector |
| All three protocols | a client certificate from a second authority no service trusts, 10-22 | refused everywhere: REST `curl exit 56` after the server requests a certificate, the broker logs `(certificate_unknown) PKIX path building failed` and delivers nothing, gRPC drops the connection |
| All three protocols | a server addressed under a name its certificate does not carry, 10-22 | refused everywhere: REST `curl exit 60`, the Python client reports `Hostname mismatch, certificate is not valid for 'not-the-broker.example'`, the gRPC channel never becomes ready |

The negative cases needed a second certificate authority, which the assessment
until then did not have, and a name outside the certificates - every one of
which carries `dns:<service>, dns:localhost, ip:127.0.0.1`, so neither
`localhost` nor the loopback address can serve as a mismatching name.
`curl --resolve`, Python's `server_hostname` and gRPC's
`ssl_target_name_override` supply one without changing anything in the system
under test. Each case ran with the valid call as its control in the same
container run.

*Does not establish:* the reason for two of the six refusals. gRPC reports
`UNAVAILABLE` for the untrusted issuer, the same class as for plaintext, and
reports only a deadline for the name mismatch, so both are attributable to the
changed variable through the control rather than read from the message. The
probe's positive queue case still disables name matching while keeping CA
verification. Nothing is established about paths not probed.

### Functional level — what the sequence tests show

| | unpatched | rc1+rc2+rc4 | + rc5 |
|---|---|---|---|
| Monitoring, services UP | 4 of 4 | **3 of 4** | 4 of 4 |
| Five business and health requests | 200 | 200 | 200 |
| Plaintext actuator on the Customer Core | 200 | 400 | 400 |
| gRPC business call | works, plaintext | works, mutual TLS | works, mutual TLS |
| Queue consumer | consuming | consuming over TLS | consuming over TLS |

Two further results, measured 10-22 on the repaired tree after the table above:

| | |
|---|---|
| A business event from the **application's own** producer | one `POST /policies` makes the policy management backend call the Customer Core over the secured connector and emit an `UpdatePolicyEvent` through the secured broker. The Node consumer received it and all eight compared fields matched - the marker in three places, the customer id, three amounts and the currency. **Measured twice**, with different markers and policy ids, which makes it the only repeated condition of this work |
| The self-service call to the Customer Core | `GET /cities/8001` is whitelisted in the self-service backend and served by `CustomerCoreRemoteProxy`, so it crosses the secured connector and returns `Zürich` through it. `/customers` does not: it stops at the API-key check, which is why that interaction had no functional evidence before |

*Does not establish:* behaviour behind the API key and the bearer token, which
no request here reaches; five of the six queues, which stay covered at
connector level only; and one run per tree on one machine.

### What no level establishes

The gates cover one smell, one deployment and the checked paths. A finding
count is a statement about the reconstructed models. Review effort was never
measured. No condition was repeated. The comparison proposals differ in more
than one variable, so they bound claims rather than support them.
