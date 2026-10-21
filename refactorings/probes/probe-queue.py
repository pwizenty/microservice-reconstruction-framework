"""Send one business event through the broker's TLS connector, with a client certificate.

Retries the handshake rather than assuming readiness: the broker is embedded in
a Spring service, so its connectors bind some time after the container reports
healthy, and a probe fired too early measures the clock rather than the channel.
"""

import json
import socket
import ssl
import sys
import time

host, port, ca, cert, key, destination, mode = (
    sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5],
    sys.argv[6], sys.argv[7],
)
attempts = int(sys.argv[8]) if len(sys.argv) > 8 else 1

# The payload names the transport it was sent over, so the consumer's log says
# which attempt reached the queue and which did not.
event = {
    "originator": f"probe-{mode}",
    "policyId": f"probe-policy-{mode}",
    "date": "2026-10-21T10:00:00.000+0000",
}
frames = (
    "CONNECT\naccept-version:1.1\nhost:/\nlogin:queueuser\npasscode:secret\n\n\x00"
    f"SEND\ndestination:{destination}\ncontent-type:application/json\n\n"
    f"{json.dumps(event)}\x00"
    "DISCONNECT\n\n\x00"
)


def once():
    raw = socket.create_connection((host, port), timeout=20)
    try:
        if mode == "plaintext":
            sock = raw
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(ca)
            # Mode "tls-nocert" omits the client certificate on purpose: it is the
            # negative control for transport.needClientAuth=true, so the broker is
            # expected to abort the handshake rather than answer CONNECTED.
            if mode != "tls-nocert":
                context.load_cert_chain(cert, key)
            # The broker's certificate names the service, not localhost, so the
            # probe verifies issuer and chain - what the channel's protection
            # rests on - and not the name it was reached by.
            context.check_hostname = False
            sock = context.wrap_socket(raw)
            peer = dict(x[0] for x in sock.getpeercert()["subject"])
            print(f"tls {sock.version()}, cipher {sock.cipher()[0]}, "
                  f"peer CN {peer.get('commonName')}")
        sock.sendall(frames.encode())
        sock.settimeout(5)
        try:
            answer = sock.recv(4096).decode(errors="replace")
        except (TimeoutError, OSError):
            answer = ""
        first = answer.splitlines()[0] if answer.strip() else "(no frame back)"
        print(f"broker answered: {first}")
        print("SENT")
        return True
    finally:
        raw.close()


for attempt in range(1, attempts + 1):
    try:
        once()
        break
    except Exception as error:
        print(f"attempt {attempt}/{attempts}: {type(error).__name__}: {error}")
        if attempt == attempts:
            print("GAVE UP")
        else:
            time.sleep(10)
