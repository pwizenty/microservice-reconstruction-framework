"""Tests for reading a Node service's transport from its sources.

The shapes below are those of Lakeside Mutual's ``risk-management-server``,
before and after the two patches that were measured against it: the unpatched
service binds its gRPC port with ``createInsecure`` and connects to the broker
without an ``ssl`` option, one patch secures the queue and leaves the gRPC
endpoint, and one secures both. A detection that cannot tell those three apart
cannot tell the proposals apart either.

Nothing here touches MongoDB.
"""

from mrf.plugins.service.node.javascript import (
    call_arguments,
    grpc_server_transport,
    messaging_transport,
)
from mrf.utilities.communication import Transport
from mrf.utilities.node import CLIENT_AUTH_REQUIRED, MESSAGING_WINDOW

PLAINTEXT_QUEUE = """
const stompit = require('stompit')

function consume() {
  const mq_config = nconf.get('activemq')
  const connectOptions = {
    host: mq_config.host,
    port: mq_config.port,
    connectHeaders: { login: mq_config.username, passcode: mq_config.password },
  }
  const connectFailover = new stompit.ConnectFailover([connectOptions])
  return new stompit.ChannelFactory(connectFailover)
}
"""

SECURED_QUEUE = """
const stompit = require('stompit')

function brokerConnectOptions(mq_config) {
  return {
    host: mq_config.host,
    port: mq_config.port,
    ssl: true,
    ca: [fs.readFileSync(resolve(mq_config.caFile))],
    key: fs.readFileSync(resolve(mq_config.keyFile)),
    cert: fs.readFileSync(resolve(mq_config.certFile)),
  }
}

const connectFailover = new stompit.ConnectFailover([brokerConnectOptions(cfg)])
"""

INSECURE_GRPC = """
server.bindAsync(
  `${grpc_config.host}:${grpc_config.port}`,
  grpc.ServerCredentials.createInsecure(),
  () => server.start()
)
"""

MUTUAL_GRPC = """
const serverCredentials = grpc.ServerCredentials.createSsl(
  tlsMaterial.ca,
  [{ private_key: tlsMaterial.key, cert_chain: tlsMaterial.cert }],
  true
)
server.bindAsync(`${grpc_config.host}:${grpc_config.port}`, serverCredentials)
"""

ENCRYPTED_GRPC = """
const serverCredentials = grpc.ServerCredentials.createSsl(
  tlsMaterial.ca,
  [{ private_key: tlsMaterial.key, cert_chain: tlsMaterial.cert }]
)
"""


def test_a_server_that_binds_insecurely_states_plaintext():
    evidence = grpc_server_transport({"index.js": INSECURE_GRPC})

    assert evidence.transport == Transport.PLAINTEXT.value
    assert evidence.client_auth is None
    assert evidence.value_source == "index.js"


def test_a_server_that_requires_a_client_certificate_states_it():
    evidence = grpc_server_transport({"index.js": MUTUAL_GRPC})

    assert evidence.transport == Transport.TLS.value
    assert evidence.client_auth == CLIENT_AUTH_REQUIRED


def test_tls_without_the_third_argument_is_not_mutual():
    """Encrypted, and the peers are not authenticated.

    The distinction is the reason the paper's refactoring is *mutual* TLS: a
    connector that only encrypts resolves the confidentiality half of the smell
    and leaves §3.8 Unauthenticated traffic.
    """
    evidence = grpc_server_transport({"index.js": ENCRYPTED_GRPC})

    assert evidence.transport == Transport.TLS.value
    assert evidence.client_auth is None


def test_a_source_that_binds_no_port_leaves_the_transport_unresolved():
    evidence = grpc_server_transport({"index.js": "module.exports = {}\n"})

    assert evidence.transport == Transport.UNRESOLVED.value
    assert evidence.value_source is None


def test_a_connection_without_an_ssl_option_is_plaintext():
    evidence = messaging_transport({"index.js": PLAINTEXT_QUEUE})

    assert evidence.transport == Transport.PLAINTEXT.value
    assert evidence.value_source == "index.js"


def test_a_connection_with_an_ssl_option_is_protected():
    evidence = messaging_transport({"index.js": SECURED_QUEUE})

    assert evidence.transport == Transport.TLS.value


def test_a_broker_address_of_a_protected_scheme_is_enough():
    source = """
    const client = mqtt.connect('mqtt+ssl://broker:8883')
    """

    assert messaging_transport({"index.js": source}).transport == Transport.TLS.value


def test_a_source_that_opens_no_connection_leaves_the_transport_unresolved():
    evidence = messaging_transport({"index.js": "const stompit = require('stompit')"})

    assert evidence.transport == Transport.UNRESOLVED.value
    assert evidence.value_source is None


def test_a_secured_grpc_endpoint_does_not_protect_a_plaintext_queue():
    """The two channels of one service are judged one by one.

    This is the service Lakeside Mutual's own patches disagree about: one of
    them secured the queue and left the gRPC endpoint. A transport read from
    anywhere in the file would have reported both as protected, and the
    difference between the proposals would have disappeared.
    """
    source = MUTUAL_GRPC + PLAINTEXT_QUEUE

    assert grpc_server_transport({"index.js": source}).transport == Transport.TLS.value
    assert (
        messaging_transport({"index.js": source}).transport == Transport.PLAINTEXT.value
    )


def test_an_ssl_option_too_far_from_the_connection_is_not_read():
    """The window is a heuristic, and it is honest about what it misses."""
    source = (
        PLAINTEXT_QUEUE
        + "\n" * (MESSAGING_WINDOW + 5)
        + "const elsewhere = { ssl: true }\n"
    )

    assert (
        messaging_transport({"index.js": source}).transport == Transport.PLAINTEXT.value
    )


def test_the_first_source_that_states_the_transport_decides():
    sources = {"b.js": INSECURE_GRPC, "a.js": MUTUAL_GRPC}

    evidence = grpc_server_transport(sources)

    assert evidence.value_source == "a.js"


def test_a_bracket_in_an_argument_does_not_end_it():
    arguments = call_arguments("(ca, [{ key: k, cert: c }], true)", 1)

    assert [argument.strip() for argument in arguments] == [
        "ca",
        "[{ key: k, cert: c }]",
        "true",
    ]
