# Paper notes: detecting and resolving a microservice security smell

Working notes for writing this up. Everything here is measured in this
repository pair unless marked otherwise; the figures are from 2026-10-14 and
each one says what produced it, so a claim can be re-checked rather than
taken.

TODO(author): framing, related work, and which of the limitations in §6 are
worth stating as future work rather than as threats to validity.

## 1. The pipeline

Four steps, in two repositories. The first three are deterministic; only the
fourth involves a language model.

```text
source code
  │  MRF  (Python, mrf/plugins/*)                         reconstruct FACTS
  ▼
MongoDB  (mrf: context, microservice, operation)
  │  LEMMA Model Extractor (de.fhdo.lemma.reconstruction)  generate MODELS
  ▼
LEMMA models  (*.data, *.services, *.operation)
  │  ChannelVerdict + RootCause                            DECIDE the smell
  ├─────────────► editor warning   (NonSecuredCommunicationValidator)
  └─────────────► CLI report       (tools/detect-smells.sh)
                       │
                       │  skill + claude CLI in a git worktree              PROPOSE
                       ▼
                  patch.diff  (applied nowhere)
                       │  tools/verify-refactoring.sh                        VERIFY
                       ▼
                  VERIFIED / PARTIAL / NOT VERIFIED
```

The division of labour is the architecture's load-bearing idea and predates
this work: **MRF reconstructs facts, LEMMA decides the smell** (ADR-0009). No
reconstructed field is named `insecure`, and no severity exists in MRF's
output. A fact is a port, a scheme, a `clientAuth` value; whether that
constitutes a smell is a rule over the models.

## 2. The smell

**Non-Secured Service-to-Service Communications**, §3.7 of

> Ponce, Soldani, Astudillo, Brogi: *Smells and refactorings for microservices
> security: A multivocal literature review.* Journal of Systems and Software
> 192 (2022) 111393. DOI 10.1016/j.jss.2022.111393

Chosen out of the paper's ten smells because it is the one with the most
studies behind it (32) and the only one both halves of which the toolchain
already reconstructed. The paper's full taxonomy, with each smell's
refactoring and what it would need from the reconstruction, is in
`security-smells.md`.

The decisive clause is quoted rather than paraphrased throughout: the smell
holds whenever two microservices interact without a secure channel, *even if
they are within the same network*. That sentence is what makes a plaintext
call between two containers on one Docker network a finding rather than an
acceptable shortcut.

The prescribed refactoring is **Use Mutual TLS** — mutual rather than plain
TLS, because it also authenticates the peers.

## 3. Key design decisions, and why

### One rule, two detection paths

`ChannelVerdict` takes plain strings and returns an outcome: no model, no EMF,
no Xtext. The editor's validator reads resolved cross-references inside
Eclipse; the command line reads a graph built from parse trees, because
**cross-model references do not resolve outside a running Xtext** (measured:
`proxy=true, name=null`). Both arrive at the same function with the same
facts.

The alternative — two detectors agreeing by review — was rejected because they
had already started to drift: the CLI detector had grown its own mutuality
reasoning as an evidence string while the validator had none. Consolidating it
into the shared rule was part of this work.

### Five outcomes, not two

| Outcome | Meaning |
|---|---|
| `SMELL` | the models show the channel unprotected |
| `PROTECTED` | mutually authenticated TLS |
| `PROTECTED_NOT_MUTUAL` | encrypted, peers not authenticated |
| `UNDECIDED` | the models do not say |
| `NOT_APPLICABLE` | not a channel between two microservices of this system |

`UNDECIDED` exists so a report cannot flatter a system: a system that does not
smell and a system whose facts were never reconstructed must not look alike.

`PROTECTED_NOT_MUTUAL` was added because the rule originally judged transport
alone, so TLS without client authentication read as fully protected — and a
verifier built on that would certify a weaker refactoring than the paper
cites. It is deliberately **not** a finding: plain TLS does secure the channel,
which is what §3.7 is about. It is where §3.8 *Unauthenticated traffic* begins,
and it is the hook for detecting that smell from facts already reconstructed.

`clientAuth=want` counts as not mutual: it requests a certificate and then
serves the request without one. An absent value is Spring's `none`, and the
reconstruction records absence rather than defaulting it.

### Findings are grouped by root cause

A finding names a channel; a channel is rarely the thing to fix. On Lakeside
Mutual **nine findings reduce to two causes**, and a cause is the unit a
refactoring acts on, because mutual TLS has to reach both ends of every
channel it covers at once. A call is keyed by its *callee*, not its caller:
three services calling one plaintext connector are one repair.

### The model is never edited

The smell is in the system; the model is a reconstruction of it. A quickfix
that rewrote `scheme = "http"` to `"https"` would secure nothing — it would
make the model stop describing the system, converting a true finding into a
false negative inside our own reconstruction. Two measured facts make it
worse: `ReconstructionModelWriter` uses plain `Files.write`
(`TRUNCATE_EXISTING`, no merge, no protected region), so such an edit is
silently destroyed on the next run; and the Service DSL has no concept of
transport security to express the fix with — `spring.technology` declares
`rest`, `soap` and `amqp`, none of which distinguishes TLS.

So resolution acts on the **sources**, and the model stays descriptive.
Recorded as **ADR-0010**, accepted 2026-10-13.

### Application-level only

A service-mesh refactoring is excluded *because the toolchain cannot see it*:
reading `kubernetes/manifests` is unimplemented (backlog A4), so a mesh change
would leave the finding count unmoved and make success indistinguishable from
failure. This is a consequence of the verification requirement, not a
preference about deployment.

## 4. The LLM step

### Three layers of instruction

| Layer | Mechanism | Varies | Enforced |
|---|---|---|---|
| Invariant constraints | `--append-system-prompt-file` | never | yes, and by verification |
| The refactoring procedure | a **skill** | once per smell | no — instruction only |
| The finding | stdin prompt | every call | n/a, it is data |

The split matters because a skill can be ignored. Nothing load-bearing depends
on it: the constraints repeat what must hold, `PatchGuard` checks the result,
and the verification step settles it.

The skill (`resolve-non-secured-communication`, in the LEMMA bundle that
invokes it) carries the procedure, per-technology recipes for Spring REST,
ActiveMQ OpenWire and STOMP from Node, a certificate script, and the
**pitfalls** — which are where the toolchain's own knowledge lives, being
things the paper cannot say:

- the **least protected connector wins**, so adding an `ssl://` connector
  beside an existing `tcp://` one clears nothing
- this broker has **two** plaintext connectors, not one
- TLS without client authentication is not mutual TLS
- the suite must still pass on a **clean checkout**, which is invisible from
  inside the worktree because the key material is already there

The last two were learned from proposals that got them wrong.

### Isolation

The proposer works in `git worktree add --detach … HEAD`. The worktree
materialises a commit, so it is a real buildable checkout the model may edit
freely, the user's working copy is never touched, and the patch is
automatically against a clean base. It also removes any need for the source
tree to be clean — uncommitted work simply is not present.

### Operational facts worth recording

- `--output-format json` buffers until exit, so a UI wanting progress must use
  `stream-json`; a proposal takes 13–25 minutes.
- **A hit usage limit returns `subtype: "success"` with `is_error: true`** and
  no edits. Testing `subtype` would file an empty patch as a success.
- The tool allowlist must include `bash` and `chmod`, or the model cannot run
  the script it just generated and ships it without the executable bit.

## 5. The validation gate

`tools/verify-refactoring.sh`. Four gates, all of which must pass; the verdict
is `VERIFIED`, `PARTIAL` or `NOT VERIFIED` with distinct exit codes (0/3/1).

| Gate | What it establishes |
|---|---|
| `clean` | the patch applies to a clean checkout and the build is green **with no generated key material** |
| `inplace` | the build is green once the material has been generated |
| `smell` | the finding count fell, against a baseline taken before |
| `starts` | the system still comes up (`docker compose up --build --wait`) |

**`clean` and `inplace` are separate on purpose**, and running them proved why.
The two proposals differ on exactly this axis and nothing else distinguishes
them: both build once certificates exist, only one builds for somebody who has
just applied the patch. A single build gate would have called them equal.

**Each gate that can be confounded has a baseline.** `smell` takes the count
before patching. `starts` runs an *unpatched control* on failure and
distinguishes "the system does not come up either way, so nothing can be
attributed" (SKIP) from "it comes up unpatched and not patched" (FAIL). That
control was added after the gate produced a false finding — see §6.

**A skipped gate is not a passed one.** `PARTIAL` means the refactoring has not
been shown to resolve the smell, only that nothing checked contradicts it.

## 6. Evaluation on Lakeside Mutual

Lakeside Mutual, commit `357ca2d`, Spring Boot 3.3.4 on Java 21, plus a Node
service. Reconstructed with all six plugins.

### What was reconstructed

| | |
|---|---|
| Microservices | 5 |
| Message channels | 11, over 6 queues, 0 unpaired |
| Channels over a protected transport | 0 |

### What was detected

| | |
|---|---|
| Findings | **9** |
| Root causes | **2** |
| Protected | 0 |
| Encrypted but not mutual | 0 |
| Undecidable | 0 |

The two causes: `CustomerCore`'s single plaintext connector explains the 3
synchronous findings; one embedded ActiveMQ broker, reached over `tcp://`,
explains the 6 asynchronous ones. The editor and the CLI agree, by
construction.

Checked that these are not mesh false positives: `kubernetes/manifests`
contains no mesh, no TLS and no ingress.

### What was proposed and verified

| | rc1 CustomerCore | rc2 ActiveMQ broker |
|---|---|---|
| Turns / duration / cost | 144 / 25 min / $10.62 | 100 / 13 min / $6.55 |
| Patch | 17 files, +652 −18 | 12 files |
| Constraints violated | none | none |
| Mutual, not merely TLS | `client-auth=need` | `needClientAuth=true`, both connectors |
| gate `clean` | **PASS** | **FAIL** |
| gate `inplace` | PASS | PASS |
| gate `smell` | **PASS — 9 → 6** | not run |
| gate `starts` | SKIP (see below) | not run |
| Verdict | **PARTIAL** | **NOT VERIFIED** |

**The 9 → 6 reduction is the central result.** It is the predicted number, not
merely movement: rc1 resolves the three synchronous findings and leaves the six
asynchronous ones, which are rc2's cause. The chain closes — patch,
re-reconstruct, re-detect, measured reduction.

Two qualitative results worth reporting:

- rc1 handled **Spring relaxed binding** (`CUSTOMERCORE_BASEURL` in
  `docker-compose.yml` reaching `customercore.baseURL`), which MRF does not
  resolve (backlog A3). The patch was therefore *more complete than the
  toolchain could verify*.
- rc2 converted **both** plaintext broker connectors rather than supplementing
  them — the pitfall most likely to yield a patch that clears findings while
  changing nothing — and refactored the Node `stompit` client, which holds no
  finding of its own but would have broken.

### A false finding the gate produced, and its cause

An earlier run reported rc1 as `NOT VERIFIED` because the system did not come
up. A control worktree at `HEAD` **with no patch** fails identically:
`openjdk:21-slim-buster: not found` — the sample system's Dockerfiles name a
base image withdrawn from Docker Hub. The gate was measuring the registry and
attributing the result to the refactoring. `smell` had a baseline from the
start; `starts` did not, which is exactly what allowed it. Fixed, and recorded
as backlog E5.

This is worth reporting rather than hiding: it is an instance of the general
hazard that an automated verifier can produce confident wrong attributions, and
the mitigation is that every gate needs a control.

### Reproducibility

Detection is deterministic and reproducible: *9 findings on Lakeside Mutual,
every time*. Resolution is not, and is explicitly outside the reproducible
path. Every proposal is recorded instead, under `refactorings/<date>-<cause>/`:
the prompt, the constraints, **a verbatim copy of the skill that produced it**,
the patch, the model ID and CLI version, both repositories' commit SHAs, and
the verification result. The skill is copied rather than referenced so a record
can be read without checking out two repositories at the right revisions.

### Test coverage

| | |
|---|---|
| MRF | 150 tests, ruff and mypy clean |
| Smell detection and machinery | 106 checks |
| Service / operation diagram | 96 / 60 checks |
| Model generation regression | 16 models across 4 systems, compared as text |

The suites are mutation-tested rather than trusted. Two tests in this work were
found to be unable to fail — one compared `0 == 0` because every finding in its
fixture shared a single cause, the other crashed instead of failing and so hid
every later check. Both are recorded in the commits that fixed them.

## 7. Known limitations

**Corpus.** Neither sample system configures TLS anywhere — 11 services across
Lakeside Mutual and park-and-charge, every one a plaintext main connector. So
every TLS-positive and mutual-TLS path is exercised only by a fixture
(`secured.services`), which exists precisely because "the detector found
nothing" and "the detector is broken" would otherwise be indistinguishable.

**No full `VERIFIED` verdict exists.** The `starts` gate can only skip until
Lakeside Mutual's Dockerfiles leave the withdrawn base image, so no refactoring
in this work has been shown to leave a *running* system. The strongest claim
available is rc1's `PARTIAL`.

**One patch at a time.** The verify loop has only ever seen a single proposal.
rc1 and rc2 were produced independently against the same commit and **do not
compose**: they overlap in five files and each invents its own CA and
certificate script. Proposals for a second cause must be generated against a
tree where the first is already applied. (A run doing exactly that is in
progress at the time of writing; its result is not in these notes.)

**The quickfix is unexercised.** It compiles against the real Xtext and Eclipse
APIs, but has never run in a live Eclipse: that the entry appears under
`Ctrl+1`, that issue data arrives in the order the validator writes it, and
that the background job reports as intended are all unverified.

**Facts not reconstructed**, each capping what the rule can decide:

| | |
|---|---|
| A3 | Spring relaxed binding, so an environment-variable override is not followed |
| A4 | Kubernetes manifests, so a mesh is invisible — and mesh-secured traffic would be a false positive |
| A6 | per-profile configuration, so a system secured only in one profile is misjudged |
| A8b | gRPC clients and Kafka, so those channels are not seen at all |

**The finding count is a lower bound.** Nine is what the models state; absent
facts can only hide channels, never invent them.

**Mutuality is not assessable for a queue.** A `MessageChannel` carries no
client-authentication fact, so a TLS broker is reported `PROTECTED` without a
claim about mutuality. Deciding it would need the broker's address, with its
`transport.needClientAuth` option, reconstructed into the model.

**Two brokers of one technology collapse.** A queue's cause is keyed by broker
technology and scheme, which is all the model carries, so two distinct ActiveMQ
brokers reached the same way would group as one cause. Lakeside Mutual has one.

**Cost.** A proposal costs $6–11 and 13–25 minutes at the model used. That is
material if the method is to be applied to many smells or many systems.

**Generality.** One smell of ten, one system, one technology stack. The skill
mechanism is designed to generalise — one skill per smell, named after the
action and citing its section — but nine of the ten remain unwritten because
their detection does not exist.

## 8. Where the artefacts are

Named artefacts, with the repository and path each lives at. Useful for a
reproducibility statement, and necessary here because the work spans two
repositories.

| Artefact | Repository | Path |
|---|---|---|
| The smell taxonomy | MRF | `docs/security-smells.md` |
| The decision | MRF | `docs/adr/0010-resolve-smells-with-an-ai-authored-patch.md` |
| The implementation plan | LEMMA | `docs/smell-resolution-plan.md` |
| The shared rule | LEMMA | `de.fhdo.lemma.servicedsl.smells.validation/…/ChannelVerdict.xtend` |
| Root-cause grouping | LEMMA | `…/smells/validation/RootCause.xtend` |
| The editor warning | LEMMA | `…/smells/validation/NonSecuredCommunicationValidator.xtend` |
| The quickfix | LEMMA | `de.fhdo.lemma.servicedsl.ui/…/quickfix/ServiceDslQuickfixProvider.xtend` |
| The skill | LEMMA | `de.fhdo.lemma.servicedsl.smells/refactoring-plugin/skills/resolve-non-secured-communication/` |
| The proposer and its seam | LEMMA | `de.fhdo.lemma.servicedsl.smells/…/smells/refactoring/` |
| Detection from the shell | LEMMA | `de.fhdo.lemma.servicedsl.smells/tools/detect-smells.sh` |
| The validation gate | LEMMA | `de.fhdo.lemma.servicedsl.smells/tools/verify-refactoring.sh` |
| The clean-verdict fixture | LEMMA | `de.fhdo.lemma.servicedsl.smells/test/fixtures/secured.services` |
| The aspects a model carries | LEMMA | `de.fhdo.lemma.reconstruction/models/technology/spring.technology` |
| Server-side facts | MRF | `mrf/plugins/service/communication/server.py` |
| Broker and transport facts | MRF | `mrf/plugins/service/communication/broker.py` |
| Asynchronous link detection | MRF | `mrf/plugins/service/communication/detectors/jms.py` |
| Proposal records | MRF | `refactorings/<date>-<cause>/` |

**Caveat at the time of writing:** most of the LEMMA artefacts are on feature
branches not yet merged to `dev` — the rule and grouping on
`feat/smell-verdict-and-grouping`, the machinery, gate and fixture on
`feat/refactoring-machinery`, the skill on `feat/resolve-smell-skill`. Paths
are given as they will read once merged. A reader checking out `dev` today
finds detection but not resolution.

### The chain, as commands

```console
$ docker start mrf-mongo
$ uv run mrf -r -p Java Spring Communication Docker Protobuf Node -t <system>
$ de.fhdo.lemma.reconstruction/tools/reconstruct.sh --target <models>
$ de.fhdo.lemma.servicedsl.smells/tools/detect-smells.sh <models> --report smells.md
$ de.fhdo.lemma.servicedsl.smells/tools/verify-refactoring.sh \
      --proposal refactorings/<date>-<cause> --source <system> \
      --models <models> --mrf <mrf-repo>
```

`-r` matters: MRF upserts on `qualified_name` and never clears its target, so
without it a stale document survives a run that no longer produces it. All six
plugins matter too — dropping `Node` leaves the Node consumer unpaired.
