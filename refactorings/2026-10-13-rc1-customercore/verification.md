# Verification: rc1-customercore

**Partial.** The verification step of ADR-0010 - re-reconstruct, re-detect,
confirm the system starts - does not exist yet (step 6 of
`../../lemma/docs/smell-resolution-plan.md`). What is recorded here is what
could be checked without it, so this is **not** evidence that the smell is
resolved. It is evidence that the patch is of the right shape and does not
violate the constraints.

## Checked independently of the proposal

| Check | Result |
|---|---|
| Patch applies to a clean checkout of the target | ✅ `git apply --check` on a fresh worktree |
| No `.services` / `.data` / `.operation` edited | ✅ none |
| No weakened verification | ✅ no `TrustAllStrategy`, `NoopHostnameVerifier`, `InsecureTrustManagerFactory`, `rejectUnauthorized:false` |
| Key material not committed | ✅ present on disk, matched by the new `.gitignore` rules, absent from `git status` |
| Server reconstructs as TLS | ✅ `server.ssl.enabled=true` with key store and trust store |
| Mutual, not merely TLS | ✅ `server.ssl.client-auth=need` |
| All callers on `https` | ✅ 4 of 4 `customercore.baseURL` values, including the test profile |
| Compiles and tests pass | ✅ `customer-core`: 26 tests, 0 failures, BUILD SUCCESS |

## Claimed by the proposal, not independently re-run

Recorded because they are checkable later, not because they are accepted:
test runs in the other three services (19, 12, 10), a live mutual-TLS handshake
against a started Customer Core, a handshake *without* a client certificate
being rejected with alert 40, and HTTP 200 from all three callers over mutual
TLS. See `notes.md`.

## Not verified, and known to be incomplete

- **`generate-certificates.sh` was never executed as a file.** The invocation's
  allowlist omitted `Bash(bash:*)` and `Bash(chmod:*)`, so every `keytool` and
  `openssl` call was run individually instead. The key material is real, but the
  script's own control flow is unrun and it carries no executable bit. **This is
  a defect in the invocation, not in the patch**; the allowlist was widened for
  the next proposal.
- **Docker Compose was not brought up**, so the volume mounts and the
  `https://customer-core:8110` addresses are reasoned about rather than observed.
- **The Kubernetes manifests now contradict the application.** Three still carry
  `CUSTOMERCORE_BASEURL=http://customer-core:8110`. Correctly left alone - MRF
  does not read manifests (backlog A4) - but the system is now inconsistent
  across deployment paths.
- **Spring Boot Admin can no longer scrape the Customer Core**, whose actuator
  endpoints are now behind mutual TLS while the admin server presents no client
  certificate.

## Worth noting

The patch changed `CUSTOMERCORE_BASEURL` in `docker-compose.yml`, which reaches
`customercore.baseURL` through Spring's relaxed binding. MRF does not resolve
relaxed binding yet (backlog **A3**), so this part of the patch is more complete
than the toolchain can currently verify.

---

Below is appended by `tools/verify-refactoring.sh`, not written by hand.
Gates 3 and 4 were skipped in this run: they need Docker, MongoDB and a full
MRF reconstruction, so the build gates were isolated first.

## Verification, 2026-10-14T07:50:19Z

**PARTIAL** — 2 passed, 0 failed, 2 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- SKIP smell: not measured
- SKIP starts: asked to skip

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.

---

The run below is the authoritative one: all four gates, with the start gate's
baseline control in place. An earlier run of the same patch reported the start
gate as FAIL and the verdict as NOT VERIFIED; that attribution was wrong. The
sample system's Dockerfiles name `openjdk:21-slim-buster`, which has been
withdrawn from Docker Hub, so a control worktree at HEAD with no patch applied
fails to build identically. The gate was measuring the registry.

**The reduction from 9 findings to 6 is the result this work exists to
produce**, and it is what was predicted: rc1 resolves the three synchronous
findings and leaves the six asynchronous ones, which are rc2's root cause.

## Verification, 2026-10-14T07:50:19Z

**PARTIAL** — 2 passed, 0 failed, 2 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- SKIP smell: not measured
- SKIP starts: asked to skip

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.

## Verification, 2026-10-14T08:00:59Z

**PARTIAL** — 3 passed, 0 failed, 1 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 6
- SKIP starts: the system does not come up unpatched either (docker.io/library/openjdk:21-slim-buster: not found), so this gate cannot attribute anything to the patch; see /var/folders/5q/g6s6_hd16xd2v6nr_5x4d3qc0000gn/T/lemma-control.TPJ54OgSP8

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.

## Verification, 2026-10-20T11:36:13Z

**VERIFIED** — 4 passed, 0 failed, 0 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 6
- PASS starts: the system comes up with the patch applied

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.

## Verification, 2026-10-20T12:58:52Z

**VERIFIED** — 4 passed, 0 failed, 0 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 6, and the addressed cause endpoint:CustomerCore has none left
- PASS starts: the system comes up with the patch applied

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.

## Verification, 2026-10-21T06:11:04Z

**PARTIAL** — 3 passed, 0 failed, 1 skipped.

Extent of the patch: 17 file(s), +559/-18 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 8, and the addressed cause endpoint:CustomerCore has none left
- SKIP starts: the system comes up, and risk-management-server-1 spring-boot-admin-1  reports an unreachable peer (certificate_unknown Connection error to ECONNREFUSED SSLException SSLHandshakeException unable to find valid certification path ) - which the unpatched system reports too (Connection error to ECONNREFUSED ), so this gate cannot attribute it to the patch; see /var/folders/5q/g6s6_hd16xd2v6nr_5x4d3qc0000gn/T/lemma-start.nxVSIJvUfD.settled

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

## Verification, 2026-10-21T06:24:32Z

**GATES PASSED** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 17 file(s), +559/-18 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 8, and the addressed cause endpoint:CustomerCore has none left
- PASS starts: the system comes up, and every peer it can no longer reach (spring-boot-admin-1 ) is declared in REFACTORING-NOTES.md

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

## Verification, 2026-10-21T15:53:58Z

**GATES PASSED** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 17 file(s), +559/-18 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

Declared losses: spring-boot-admin-1 (declared). A peer this patch can no longer
reach, as the start gate measured it against the unpatched system.
Reported rather than folded into the verdict, because a patch that
loses a monitoring scrape and declares it is not the same result as
one that loses nothing, and both pass the four gates.

Test coverage lost: none declared. Read from REFACTORING-NOTES.md,
not detected - a proposal that declares nothing reads "none
declared", which is a statement about the notes.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 8, and the addressed cause endpoint:CustomerCore has none left
- PASS starts: the system comes up, and every peer it can no longer reach (spring-boot-admin-1 ) is declared in REFACTORING-NOTES.md

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

## Verification, 2026-10-21T16:32:02Z

**REPAIR PARTIAL** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 17 file(s), +559/-18 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

Declared losses: spring-boot-admin-1 (declared). A peer this patch can no longer
reach, as the start gate measured it against the unpatched system.
Reported rather than folded into the verdict, because a patch that
loses a monitoring scrape and declares it is not the same result as
one that loses nothing, and both pass the four gates.

Test coverage lost: none declared. Read from REFACTORING-NOTES.md,
not detected - a proposal that declares nothing reads "none
declared", which is a statement about the notes.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 8, and the addressed cause endpoint:CustomerCore has none left
- PASS starts: the system comes up, and every peer it can no longer reach (spring-boot-admin-1 ) is declared in REFACTORING-NOTES.md

A skipped gate is not a passed one: NOT MEASURED means the
refactoring has not been shown to resolve the smell, only that
nothing checked contradicts it. REPAIR PARTIAL means every gate
passed and a peer is nevertheless gone, declared in the notes.
REPAIR COMPLETE means every gate passed and nothing was lost, which
is still not the same as the application being secure: the gates
cover this smell, this deployment and the declared scope only.
