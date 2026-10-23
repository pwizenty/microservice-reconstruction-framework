# Runtime probes of the secured queue

What a gate cannot establish. The *starts* gate says the system comes up and
that no service reports an unreachable peer; it does not say that the channel
is secured, and a broker that accepts a frame it should refuse would pass it.
These probes ask the running system directly, over the same STOMP port the
services use, with no reconstruction rule involved — so they are evidence
independent of the detector that produced the finding.

Run against a Lakeside Mutual checkout with the broker patch applied
(`2026-10-20-rc2b-activemq-broker`, recorded here at `aed2cfb`):

```sh
./run-queue-probe.sh <checkout>          # the three cases in one container run
./run-queue-probe-nocert.sh <checkout>   # why the no-certificate case fails
```

`probe-queue.py` is the harness. Its last argument is the mode:

| mode | what it sends | expected |
|---|---|---|
| `tls` | STOMP over TLS with a client certificate | accepted, consumed |
| `tls-nocert` | the same without a client certificate | refused by the broker |
| `plaintext` | STOMP on the same port, no TLS | no frame back |

## What was measured, 2026-10-21

`three-cases.log` — one container run, all three cases, payloads tagged by mode
so the consumer's log says which arrived:

```
with a client certificate:  1     TLSv1.3, TLS_AES_256_GCM_SHA384, CONNECTED
TLS, no client certificate: 0
plaintext:                  0
```

`no-certificate-broker-log.log` — the same no-certificate case with the broker's
own log read afterwards, because a frame that does not arrive says nothing about
why:

```
Transport Connection to: tcp://…:51000 failed:
    (certificate_required) Empty client certificate chain
```

That is `transport.needClientAuth=true` demonstrated rather than read from
configuration. Note what the first log alone would have hidden: under TLS 1.3
the handshake itself completes, because the certificate is requested after it,
so "the handshake succeeded" is not evidence that the peer was authenticated.
Delivery is.
