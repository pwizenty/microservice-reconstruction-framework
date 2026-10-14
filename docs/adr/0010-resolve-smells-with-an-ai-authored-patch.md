# ADR-0010: Resolve security smells with an AI-authored patch, outside the reproducible path

- Status: Accepted
- Date: 2026-10-13
- Deciders: Philip Wizenty
- Supersedes: –

## Context and problem statement
ADR-0009 set out the pipeline this project builds: MRF reconstructs architecture
information, the LEMMA Model Extractor derives LEMMA models from it, LEMMA
validation rules report smells, **and the findings become refactorings**. The
first three steps exist. Smell **Non-Secured Service-to-Service
Communications** (Ponce et al., JSS 2022, §3.7 - see `docs/security-smells.md`)
is detected two ways, in the model editor and from the command line, over one
shared rule (`ChannelVerdict` in `de.fhdo.lemma.servicedsl.smells.validation`).
On Lakeside Mutual it reports **9 findings** across 5 microservices.

The fourth step is open: what it means to *resolve* such a finding. The obvious
reading - an Eclipse quickfix that edits the model until the warning goes away -
is the one option that must be rejected, and the reason is ADR-0009's own
division of labour. MRF reconstructs *facts*; LEMMA *decides* the smell. A
quickfix that rewrites a reconstructed fact (`scheme = "http"` to `"https"`,
`tlsEnabled = false` to `true`) does not secure anything. It makes the model
stop describing the system: the warning disappears, the vulnerability remains,
and a true finding has been converted into a false negative inside our own
reconstruction.

Two measured facts make that worse than it first appears.

- **A generated model cannot hold a manual edit.** All three write methods of
  `ReconstructionModelWriter` use plain `Files.write`, whose default is
  `CREATE + TRUNCATE_EXISTING + WRITE`. There is no existence check, no merge,
  no prompt, no protected region and no `@generated` marker. An edited model is
  silently truncated on the next run.
- **The refactoring the literature prescribes is not a model change at all.**
  Ponce et al. suggest *Use Mutual TLS* for §3.7. Mutual TLS is realised in
  Spring properties (`server.ssl.*`, `client-auth`), in an ActiveMQ connector
  (`tcp://` to `ssl://`, `stomp://` to `stomp+ssl://`), and in key and trust
  stores. The LEMMA Service DSL has no notion of transport security to express
  it with: `spring.technology` declares the protocols `rest`, `soap` and
  `amqp`, and none of them distinguishes TLS.

So resolution has to act on the *source system* that was reconstructed, not on
the reconstruction of it. That raises the question this ADR answers: by what
means, and how is the result known to be correct?

The refactoring is not a template substitution. It spans both ends of every
channel, three technologies in one system (Spring REST, ActiveMQ OpenWire from
Java, STOMP from a Node client using `stompit`), and it needs PKI material that
no generator can invent. Lakeside Mutual's 9 findings reduce to **2 root
causes**: `CustomerCore`'s single plaintext connector explains the 3 synchronous
findings, and one embedded ActiveMQ broker with two plaintext connectors
explains the 6 asynchronous ones.

## Decision drivers
- **Reproducibility.** `CLAUDE.md` opens with "Research software (FH Dortmund) -
  results must be reproducible." A language model is not reproducible.
- **The model must keep describing the system.** ADR-0009's fact/decision split
  is void the moment a fact may be edited to silence a finding.
- **The toolchain must be able to check its own output.** A resolution that
  cannot be measured is an assertion, not a result.
- **The refactoring is technology-specific and cross-cutting**, so a template
  generator would need one template per technology pair plus PKI handling.
- **A thesis contribution needs a defensible evaluation**, which means the
  claim "the smell was resolved" has to rest on evidence the tool produces.

## Considered options
1. Edit the reconstructed model until the warning clears
2. Transform into a separate to-be model, deterministically
3. Generate the source change from hand-written templates, deterministically
4. **Have an AI author a patch against the sources, and verify it by
   re-reconstructing**
5. Keep status quo: detect only, resolve by hand

## Decision
Chosen option: **"Have an AI author a patch against the sources, and verify it
by re-reconstructing"**, because it is the only option that both leaves the
reconstruction honest and produces a claim the toolchain can check.

The decision has four parts, and the fourth is what makes the first three
admissible:

1. **The quickfix proposes; it never applies.** A finding's resolution is a
   patch produced in a throwaway `git worktree` of the source repository at
   `HEAD`. The user's working tree is never written to, and no LEMMA model is
   edited - so the model never stops describing the system.
2. **Instruction is layered.** Invariant constraints go in the system prompt;
   the refactoring procedure for one smell goes in a versioned *skill*
   (`resolve-non-secured-communication`, citing §3.7), shipped in the LEMMA
   bundle that invokes it; only the finding itself varies per call. Nothing
   load-bearing depends on the skill being obeyed, because a skill is
   instruction and not enforcement.
3. **Resolution is application-level only.** A service-mesh refactoring is
   excluded *because the toolchain cannot see it*: reading
   `kubernetes/manifests` is backlog item A4 and unimplemented, so a mesh
   change would leave the finding count unmoved and success
   indistinguishable from failure. This is a consequence of the verification
   requirement, not a preference.
4. **A proposal counts only when it is verified.** A separate, scriptable step
   applies the patch to a dedicated branch and re-runs the pipeline. Success
   requires all three of: the finding count dropped, the build green, and the
   system actually starts. The last is not ceremony - a patch that switches the
   broker to `ssl://` while leaving the Node `stompit` client on `stomp://`
   would clear six findings and leave the system unable to run.

Detection stays entirely deterministic. The AI sits strictly downstream of it.
The reproducible claim is therefore unchanged in substance - *9 findings on
Lakeside Mutual, every time* - and the AI's contribution is judged by whether
that number falls, not by whether it emits identical text twice.

Every proposal is recorded: the prompt, the system-prompt appendix, a verbatim
copy of the skill that produced it, the model ID and CLI version, the commit
SHAs of both repositories, the patch, and the before/after verification. The
refactoring is not reproducible; the record of it is auditable, and the skill
that encodes the procedure is versioned like any other source file.

Definition of done is expressed in MRF's own recognition rules, so that "the AI
believes it is finished" and "the toolchain measures it as finished" cannot
drift apart:

| Root cause | Done when MRF reconstructs |
|---|---|
| `CustomerCore`'s connector | every `ServerEndpoint` with `tlsEnabled = true` and `clientAuth = need`, and all three `ServiceCall` with `scheme = "https"` |
| the ActiveMQ broker | a connector scheme in `{ssl, stomp+ssl}` with **no plaintext connector remaining**, and clients' `broker-url` on `ssl://` |

The second row encodes a trap worth stating: `broker_of` takes the *least
protected* connector (`broker.py`), so adding an `ssl://` connector beside the
existing `tcp://` one clears nothing.

TODO(author): confirm that the thesis presents this as a contribution
("model-driven detection and AI-assisted resolution") rather than as tooling,
and decide whether comparing models is itself an evaluation dimension.

## Consequences
- Positive: the reconstruction stays truthful - no reconstructed fact is ever
  edited to silence a finding, and ADR-0009's split survives intact.
- Positive: resolution is measurable. A refactoring either moves the finding
  count or it does not, and the system either starts or it does not.
- Positive: the refactoring procedure becomes a reviewed, versioned artefact
  per smell rather than a prompt built at runtime, and the taxonomy's remaining
  nine smells gain an obvious shape to grow into.
- Positive: the worktree removes the need for a clean source tree, so a
  proposal can be produced while the sample system has uncommitted work.
- Negative: a new external dependency on the `claude` CLI, which must be
  installed and authenticated; the quickfix refuses when it is not.
- Negative: output is nondeterministic. Two runs on one finding yield two
  patches, and only the verification distinguishes a good one.
- Negative: verification needs Docker, MongoDB, a full MRF run and the sample
  system to come up - minutes of work, and the hardest part is mutual TLS
  between containers with generated development certificates.
- Negative: the record spans two repositories, since the skill lives in LEMMA
  and the artefacts in MRF. Mitigated by copying the skill into each artefact.
- Negative: a service mesh is out of scope until A4, so a system that secures
  its traffic by mesh would still be reported as smelling.
- Follow-up tasks: extend `ChannelVerdict` with a fifth outcome distinguishing
  TLS from *mutual* TLS, so the verifier cannot certify a weaker refactoring
  than §3.7 cites; re-anchor the warning per channel with an issue code;
  group findings by root cause; write the skill; build the verify script; add a
  TLS-positive fixture for the case where there is nothing to resolve.

## Pros and cons of the options
### 1. Edit the reconstructed model
- Good, because it is the cheapest possible change and the warning clears at once.
- Bad, because the model then contradicts the system it describes.
- Bad, because the edit is silently truncated by the next reconstruction.
- Bad, because it voids ADR-0009: a fact that may be rewritten to clear a
  finding is no longer a fact.

### 2. Deterministic to-be model
- Good, because it is reproducible and the as-is model stays untouched.
- Good, because architectural refactoring at model level is a recognised
  contribution shape.
- Bad, because the Service DSL cannot express transport security at all, so the
  target model would need new metamodel concepts before it could say anything.
- Bad, because it resolves nothing in the system; the smell is still there.

### 3. Deterministic template generator
- Good, because it is fully reproducible, needing no external service.
- Good, because the output is predictable and reviewable.
- Bad, because it needs one template per technology pair - Spring REST,
  OpenWire, STOMP from Node - and a fourth for PKI material, all for one smell.
- Bad, because it cannot adapt to how a given system is actually wired, which
  is precisely where the work is: locating the three callers of `CustomerCore`
  and the two connectors of an embedded broker.

### 4. AI-authored patch, verified by re-reconstruction (chosen)
- Good, because it acts where the smell is, leaving the reconstruction honest.
- Good, because the toolchain verifies its own output rather than asserting it.
- Good, because it adapts across technologies without a template per pair.
- Good, because the procedure is captured as a versioned skill, so what the AI
  was told is reviewable and citable.
- Bad, because it is nondeterministic and depends on an external CLI.
- Bad, because verification is expensive and needs the sample system to run.

### 5. Keep status quo
- Good, because detection already works and is reproducible.
- Good, because it adds no dependency and no nondeterminism.
- Bad, because ADR-0009 names refactoring as the pipeline's fourth step, and the
  pipeline would stop one step short of its stated purpose.
