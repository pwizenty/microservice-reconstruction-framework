# The monitoring regression: a repair the detection could not see, and its repair

A record of one concrete case in which a finding count said nothing useful in
either direction, what it cost, and how it was eventually closed. It is the
sharpest evidence this work has for a claim it makes in general: resolving a
finding, preserving behaviour and protecting a channel are three different
outcomes.

## The problem

Lakeside Mutual's monitoring server polls the actuator endpoints of the four
Spring services. Root cause 1 of the smell is the Customer Core's plaintext
connector, and resolving it means requiring a client certificate **on that
connector** - which is the same connector the monitoring server scrapes. The
monitoring server holds no certificate, so the scrape stops working.

Three things made this hard to see.

1. **Detection cannot report it.** MRF skips the monitoring server as
   infrastructure (`INFRASTRUCTURE_TECHNOLOGIES`), so it has no service model.
   A channel needs two reconstructed ends to be judged, and this one has one.
   The relationship is one of the four the manual inventory lists and
   model-level detection does not cover - see
   `channel-inventory-lakeside-mutual.md`.
2. **The finding count is silent in both directions.** It does not fall when
   the relationship breaks and it does not rise. rc1 reads 11 → 8 either way.
3. **Registration keeps working**, which makes the system look healthy from
   the outside. The service registers *outward* to the admin server over
   plaintext HTTP on port 9000, and that direction was never changed. What
   fails is the poll back.

So a proposal can resolve every finding it was asked to resolve, pass four
gates, and leave a working relationship broken.

## How it was caught, in the order it happened

| | |
|---|---|
| The proposal declared it | rc1's `notes.md` predicted the monitoring failure as a consequence of `client-auth=need` |
| The start gate observed it | `certificate_unknown` and PKIX `unable to find valid certification path` in the admin server's log, absent from the control, 23 lines. This is what the declared-loss rule exists for |
| The verdict distinguished it | `REPAIR PARTIAL` rather than `REPAIR COMPLETE`: every gate passed and a declared peer is gone |
| A runtime test quantified it | Spring Boot Admin's own `/instances` API: four services registered, three UP, Customer Core `OFFLINE` |

The last step is what made it a number rather than a prediction, and it also
showed the loss survives the whole guided sequence: rc4 resolves the last
finding and the Customer Core is still `OFFLINE`.

## The repair

`refactorings/2026-10-22-rc5-monitoring`. **The first proposal of this work
whose input is not a finding.** There is no finding to quote, so the request
quotes the loss rc1 declared and the runtime measurement that confirmed it,
and it states the scope: the monitoring side of the channel, not the Customer
Core's connector, which is already correct.

What the proposal did:

- a `MonitoringTlsConfiguration` in the admin server, building the poll
  client's `SSLContext` from its own key store and the shared trust store;
- a certificate for the monitoring server from the same development authority,
  and the store mounted into its container;
- `SPRING_BOOT_ADMIN_CLIENT_INSTANCE_SERVICE_BASE_URL=https://customer-core:8110`,
  because the address a service registers has to be one its certificate
  covers;
- the three services still reached over plaintext are deliberately untouched.

Measured: `REPAIR COMPLETE`, 11 → 0, no declared loss, 9 files, +354/-3, 140
turns, 1053 s, \$8.07.

## What the three trees show

One run, three trees, the same checks:

| | Registered | UP | Customer Core | Plaintext actuator request |
|---|---|---|---|---|
| unpatched `622632f` | 4 | 4 | UP | 200 |
| rc1 + rc2 + rc4 | 4 | 3 | **OFFLINE** | 400 |
| + rc5 | 4 | **4** | **UP** | **400** |

The last column is the one that matters. The monitoring server is not let back
in through a hole: the connector still refuses plaintext, and the monitoring
server now presents a certificate like every other caller. gRPC, the queue and
the other five functional requests are identical in all three trees.

Full log and scripts: `saner2027-package-11/logs/sequence-tests/`.

## What this changes about the approach

**The assessment's output becomes the next request's input.** The declared-loss
field was added so a passing verdict could not hide a regression. Here it does
more than report: it is the only machine-readable statement that a repair is
needed, because no finding exists. A proposal chain driven by findings alone
could never have produced rc5.

**The finding count is not the measure of a repair.** rc5 leaves it at zero,
where it already was. Everything rc5 achieved is invisible to it.

## What is still open

- **Three monitoring relationships remain plaintext.** rc5 secured the one
  that was broken. The other three services are still polled over plaintext
  HTTP, and they are instances of the same smell that detection does not
  report. Nothing is broken there, which is exactly why nothing points at them.
- **Registration is still plaintext**, in all four cases: the services register
  outward to port 9000 over HTTP.
- **The general fix is reconstruction, not another proposal.** As long as the
  monitoring server has no service model, every channel it is part of is
  outside what detection can judge. Reconstructing infrastructure nodes as
  something the rule can see is the change that would close this class, rather
  than this instance.
