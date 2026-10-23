#!/usr/bin/env bash
# The third broker case: TLS without a client certificate, against the same
# connector the mutual-TLS probe uses. Positive and negative controls run in
# the same container run so the three results are comparable.
set -uo pipefail
SCRATCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TREE="${1:?a Lakeside Mutual checkout with the broker patch applied}"
CERTS="$TREE/risk-management-server/certs"
P="python3 -I $SCRATCH/probe-queue.py localhost 61613 $CERTS/ca.crt $CERTS/risk-management-server.crt.pem $CERTS/risk-management-server.key /queue/newpolicies"

cd "$TREE" || exit 1
echo "== tree: $(git log --oneline -1)"
bash generate-certificates.sh > /dev/null 2>&1 && echo "certs ok"

echo "== compose up"
docker compose up -d --build --wait > /dev/null 2>&1 && echo "up ok" || echo "up FAILED"

echo "== waiting until the consumer stops reporting refused connections"
for i in $(seq 1 24); do
    sleep 10
    recent="$(docker compose logs --since 10s risk-management-server 2>/dev/null)"
    if ! grep -q "ECONNREFUSED" <<< "$recent"; then
        echo "quiet after $((i * 10))s"
        break
    fi
done

echo "== readiness, and the positive case: TLS with a client certificate"
$P tls 12 2>&1 | sed 's/^/    /'

echo "== the new case: TLS without a client certificate"
$P tls-nocert 3 2>&1 | sed 's/^/    /'

echo "== negative control: plaintext STOMP on the same port"
$P plaintext 1 2>&1 | tail -2 | sed 's/^/    /'

echo "== which attempt reached the consumer?"
sleep 20
docker compose logs --tail 200 risk-management-server 2>&1 \
    | grep -E "An event has been consumed|originator" | sed 's/^/    /'
echo "    --- counts"
echo "    with a client certificate: $(docker compose logs --tail 400 risk-management-server 2>/dev/null | grep -c '"probe-tls"')"
echo "    TLS, no client certificate: $(docker compose logs --tail 400 risk-management-server 2>/dev/null | grep -c 'probe-tls-nocert')"
echo "    plaintext:                 $(docker compose logs --tail 400 risk-management-server 2>/dev/null | grep -c 'probe-plaintext')"

echo "== tear down"
docker compose down -v > /dev/null 2>&1 && echo "down"
echo "QUEUE PROBE 3 DONE"
