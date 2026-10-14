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

**Superseded below: this proposal is now VERIFIED on all four gates.** The
start gate could only skip while Lakeside Mutual's container images could not
be built; once its Dockerfiles were moved off the withdrawn
`openjdk:21-slim-buster`, the gate ran and passed.
## Verification, 2026-10-14T11:32:16Z

**PARTIAL** — 3 passed, 0 failed, 1 skipped.

- PASS clean: the patch applies to a clean checkout and the build is green
- PASS inplace: the build is green once key material exists
- PASS smell: findings fell from 9 to 0
- SKIP starts: the system does not come up unpatched either (docker.io/library/openjdk:21-slim-buster: not found), so this gate cannot attribute anything to the patch; see /var/folders/5q/g6s6_hd16xd2v6nr_5x4d3qc0000gn/T/lemma-control.2Q7XzMtkib

A skipped gate is not a passed one: PARTIAL means the refactoring has
not been shown to resolve the smell, only that nothing checked
contradicts it.


---

## Verification, final — all four gates

Measured against `fix/container-base-images`, the commit that makes the sample
system buildable at all, with the two refactoring commits rebased onto it:

```
baseline: 9 finding(s) before the patch
PASS  clean    the patch applies to a clean checkout and the build is green
PASS  inplace  the build is green once key material exists
PASS  smell    findings fell from 9 to 0
PASS  starts   the system comes up with the patch applied

VERIFIED — 4 passed, 0 failed, 0 skipped
```

**The first full VERIFIED verdict in this work.** The smell is resolved and the
system still runs.

### Checked directly, not taken from the gate

`docker compose up --wait` proves health checks passed, which is not the same
as proving the TLS path is exercised. Probed against the running system:

| Probe | Result | What it shows |
|---|---|---|
| `http://localhost:8110` | 400 | the connector speaks TLS; plaintext gets Tomcat's Bad Request |
| `https://` with a client certificate | 401 | the handshake completed - 401 is API-key auth, above the transport |
| `https://` **without** one | refused | **this is what makes it mutual** rather than merely encrypted |
| `policy-management` -> CustomerCore | 200 | real data through the channel |
| `customer-management` -> CustomerCore | 200 | same, via Feign |

The broker's own log:

```
Connector stomp+ssl://…:61613?transport.needClientAuth=true started
Connector ssl://…:61616?transport.needClientAuth=true started
```

Both connectors TLS, both demanding a client certificate, no plaintext
connector bound. The Node consumer logs `consume PolicyEvent messages over
TLS` and then falls quiet.

### Two readings that are not clean

`customer-self-service` returned **401** where the other two callers returned
200. That endpoint has its own user-authentication layer, so this is very
probably not a transport failure - but it was not isolated, and is recorded as
unexplained rather than dismissed.

The Node consumer logged `ECONNREFUSED` bursts at startup, all timestamped
before the broker's connectors began listening. `stompit`'s failover recovered
and it is quiet now, so this is a **pre-existing start-ordering weakness** of
the sample - `depends_on` does not wait for the broker to bind - rather than
anything the refactoring introduced.
