
## Verification, 2026-10-20T15:02:35Z

**GATES PASSED** — 4 passed, 0 failed, 0 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 0
- PASS starts: the system comes up with the patch applied

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

## Verification, 2026-10-21T06:22:16Z

**GATE FAILED** — 2 passed, 1 failed, 1 skipped.

Extent of the patch: 38 file(s), +1053/-45 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS smell: findings fell from 11 to 0
- FAIL starts: the system does not come up with the patch applied, though it does unpatched: see /var/folders/5q/g6s6_hd16xd2v6nr_5x4d3qc0000gn/T/lemma-start.tH7iUHS7zX
- SKIP inplace: no key-material command and none found in the patch, so this would only repeat the clean gate

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

### Note on the verification above, 2026-10-21

That `GATE FAILED` is the verification tool's doing, not the patch's. The script
looked for the certificate-generating script one directory deep, and this patch
ships `scripts/generate-certificates.sh`. So no key material was generated: the
`inplace` gate skipped for want of a command, and the system then could not come
up, with the Risk Management server stating the reason exactly —

```
Error: could not read the TLS key from /usr/src/app/certs/service.key.
Run scripts/generate-certificates.sh in the repository root to generate the
key material before starting
```

The `smell` gate is unaffected and stands: 11 findings before, 0 after. The
script now looks two levels deep, and the verification that follows is the one
to read.

## Verification, 2026-10-21T06:28:11Z

**GATES PASSED** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 38 file(s), +1053/-45 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 0
- PASS starts: the system comes up, and every peer it can no longer reach (spring-boot-admin-1 ) is declared in REFACTORING-NOTES.md

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

## Verification, 2026-10-21T16:39:29Z

**REPAIR PARTIAL** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 38 file(s), +1053/-45 line(s). Not a gate - no number of files is the
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
- PASS smell: findings fell from 11 to 0
- PASS starts: the system comes up, and every peer it can no longer reach (spring-boot-admin-1 ) is declared in REFACTORING-NOTES.md

A skipped gate is not a passed one: NOT MEASURED means the
refactoring has not been shown to resolve the smell, only that
nothing checked contradicts it. REPAIR PARTIAL means every gate
passed and a peer is nevertheless gone, declared in the notes.
REPAIR COMPLETE means every gate passed and nothing was lost, which
is still not the same as the application being secure: the gates
cover this smell, this deployment and the declared scope only.
