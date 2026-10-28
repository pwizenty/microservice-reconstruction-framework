# Verification: rc2-activemq-broker

**Partial, and it found a defect.** The verification step of ADR-0010 does not
exist yet (step 6), so nothing here shows the smell is resolved. What it does
show is that the patch is right in the respect that matters most for this root
cause, and wrong in one that no other check would have caught.

## Checked independently of the proposal

| Check | Result |
|---|---|
| Patch applies to a clean checkout of the target | ✅ 12 files, `git apply --check` on a fresh worktree |
| **No plaintext broker address remains anywhere** | ✅ zero matches for `tcp://` or `stomp://` across properties, Java, JSON, YAML and JS |
| Both connectors converted, not supplemented | ✅ `stomp+ssl://…:61613` and `ssl://…:61616` |
| Mutual, not merely TLS | ✅ `transport.needClientAuth=true` on both |
| Node client presents a certificate | ✅ `ssl:true` with `ca`, `key`, `cert`; no `rejectUnauthorized:false` |
| No `.services` / `.data` / `.operation` edited | ✅ none |
| No weakened verification | ✅ none |
| Key material not committed | ✅ generated, gitignored, absent from `git status` |
| Suite passes in the worktree | ✅ `policy-management-backend`: 19 tests, 0 failures |
| **Suite passes on a clean checkout** | ❌ **fails** - see below |

The converted-not-supplemented result is the important one. `broker_of` takes
the *least protected* connector, so an `ssl://` connector added beside the
existing `tcp://` one would have cleared nothing while looking correct. Both
plaintext connectors are gone.

## The defect

Applying the patch to a fresh worktree and building, without generating any key
material first:

```text
RiskManagementMessageProducerTests -- Tests run: 2, Errors: 2
  java.io.FileNotFoundException: ../certs/policy-management-backend.p12
BUILD FAILURE
```

The patch points the embedded test broker at a PKCS#12 store on disk, so the
suite only passes in a tree where `generate_certificates.sh` has already run.

This is a regression in build ergonomics, and the two proposals of step 2
disagree about it: `rc1` built its `SSLContext` inside `@Profile("default")`
beans *deliberately*, to keep `./mvnw test` green with no key material present.
`rc2` did the opposite and disclosed the dependency in `notes.md` ("run that
script before running the tests") without recognising it as a regression.

Neither the proposal's own notes nor any constraint check caught it. It is
invisible from inside the worktree, because the certificates are already there.
Only applying the patch to a clean checkout and building found it.

**Both halves of the toolchain were corrected rather than the patch:**
- the skill gained it as a pitfall *and* a done-criterion (lemma `d9db83bc`)
- the plan split verification's build gate in two, so "builds in the working
  tree" and "builds on a clean checkout" are separate conditions (lemma
  `50e1b008`)

The patch itself is left as it was produced. It is the record of what the skill
yielded on 2026-10-13, and re-running it against the corrected skill is a
better test of the correction than editing the artefact would be.

## Claimed by the proposal, not independently re-run

Recorded as claims: the other services' suites, a live mutual-TLS handshake to
the broker, and a Node client consuming over `stomp+ssl`. See `notes.md`.

## Not verified

- **Docker Compose was not brought up**, so the mount paths - `/certs` for the
  two Java services, `/usr/src/certs` for the Node service - are reasoned about
  rather than observed.
- **The Kubernetes manifests** were left untouched, as in `rc1`, so they now
  disagree with the application about the broker transport too.

---

Below is appended by `tools/verify-refactoring.sh`, not written by hand.
Gates 3 and 4 were skipped in this run: they need Docker, MongoDB and a full
MRF reconstruction, so the build gates were isolated first.

## Verification, 2026-10-14T07:51:17Z

**NOT VERIFIED** — 1 passed, 1 failed, 2 skipped.

- PASS inplace: the build is green once key material exists
- FAIL clean: the build fails on a clean checkout with no generated key material: FAILED: policy-management-backend see /var/folders/5q/g6s6_hd16xd2v6nr_5x4d3qc0000gn/T/lemma-clean-build.NftA3q552v
- SKIP smell: not measured
- SKIP starts: asked to skip

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.
