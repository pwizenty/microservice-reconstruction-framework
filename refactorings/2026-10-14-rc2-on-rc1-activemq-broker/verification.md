# Verification: rc2-on-rc1-activemq-broker

Produced by `tools/verify-refactoring.sh`. This is the **combined** result:
the patch carries both root causes, because this proposal was produced against
a tree where root cause 1 was already resolved.

**Findings fell from 9 to 0.** The smell is resolved for the whole system, as
measured by re-reconstructing the patched sources and re-running detection.

It also passes the clean-checkout gate that `rc2` standalone failed. The test
broker now uses ActiveMQ's in-VM transport, which has no network connector and
therefore needs no certificates, with `create=false` so the test fails rather
than silently connecting to an auto-created empty broker.

That is a trade-off and not a free win: `rc2` standalone pointed its test
broker at a real `ssl://` connector and so genuinely exercised a mutual-TLS
handshake, which this one does not. The skill's clean-checkout criterion bought
build ergonomics at the cost of transport coverage in that test.

The start gate can only skip: Lakeside Mutual's Dockerfiles name
`openjdk:21-slim-buster`, withdrawn from Docker Hub, so the system does not
come up patched or unpatched (backlog E5).
## Verification, 2026-10-14T11:32:16Z

**PARTIAL** — 3 passed, 0 failed, 1 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 0
- SKIP starts: the system does not come up unpatched either (docker.io/library/openjdk:21-slim-buster: not found), so this gate cannot attribute anything to the patch; see /var/folders/5q/g6s6_hd16xd2v6nr_5x4d3qc0000gn/T/lemma-control.2Q7XzMtkib

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.
