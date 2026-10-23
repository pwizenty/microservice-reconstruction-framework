#!/usr/bin/env bash
# Why the no-certificate attempt is not delivered: read the broker's own log.
set -uo pipefail
SCRATCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TREE="${1:?a Lakeside Mutual checkout with the broker patch applied}"
CERTS="$TREE/risk-management-server/certs"
P="python3 -I $SCRATCH/probe-queue.py localhost 61613 $CERTS/ca.crt $CERTS/risk-management-server.crt.pem $CERTS/risk-management-server.key /queue/newpolicies"

cd "$TREE" || exit 1
bash generate-certificates.sh > /dev/null 2>&1 && echo "certs ok"
docker compose up -d --build --wait > /dev/null 2>&1 && echo "up ok" || echo "up FAILED"
for i in $(seq 1 24); do
    sleep 10
    recent="$(docker compose logs --since 10s risk-management-server 2>/dev/null)"
    grep -q "ECONNREFUSED" <<< "$recent" || { echo "quiet after $((i * 10))s"; break; }
done

MARK="$(date -u +%FT%TZ)"
echo "== mark $MARK"
echo "== TLS without a client certificate"
$P tls-nocert 1 2>&1 | sed 's/^/    /'
sleep 15
echo "== what the broker logged since the mark"
docker compose logs --since "$MARK" policy-management-backend 2>&1 \
    | grep -iE "ssl|tls|certificate|handshake|transport|refus|reject" | tail -20 | sed 's/^/    /'
echo "== consumer deliveries since the mark"
echo "    probe-tls-nocert: $(docker compose logs --since "$MARK" risk-management-server 2>/dev/null | grep -c 'probe-tls-nocert')"
docker compose down -v > /dev/null 2>&1 && echo "down"
echo "QUEUE PROBE 4 DONE"
