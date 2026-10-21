
## Verification, 2026-10-20T11:56:25Z

**VERIFIED** — 4 passed, 0 failed, 0 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 3
- PASS starts: the system comes up with the patch applied

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.

## Verification, 2026-10-21T06:17:58Z

**GATES PASSED** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 15 file(s), +411/-21 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 4, and the addressed cause broker:activemq:tcp has none left
- PASS starts: the system comes up with the patch applied, and reports no unreachable peer the unpatched system does not report too

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.

## Verification, 2026-10-21T15:51:40Z

**GATES PASSED** — 4 passed, 0 failed, 0 skipped.

Extent of the patch: 15 file(s), +411/-21 line(s). Not a gate - no number of files is the
right one - but the claim that model-level input bounds a refactoring
is a claim about extent, so it is counted rather than recalled.

Declared losses: none. A peer this patch can no longer
reach, as the start gate measured it against the unpatched system.
Reported rather than folded into the verdict, because a patch that
loses a monitoring scrape and declares it is not the same result as
one that loses nothing, and both pass the four gates.

Test coverage lost: That fixture now uses the in-VM transport (vm://...?create=false) instead: the broker is named, kept non-persistent, and reached without opening a network socke. Read from REFACTORING-NOTES.md,
not detected - a proposal that declares nothing reads "none
declared", which is a statement about the notes.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 11 to 4, and the addressed cause broker:activemq:tcp has none left
- PASS starts: the system comes up with the patch applied, and reports no unreachable peer the unpatched system does not report too

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it. GATES PASSED means every gate passed, which is not
the same as the application being secure: the gates cover this smell
and this deployment only.
