"""Constants for reconstructing from the manifest and configuration of Node.

A Node service states its name and its dependencies in ``package.json``, which
is a standard, and its addresses in a configuration file of its own, which is
not: ``nconf`` reads whatever file it is pointed at, under whatever keys the
service chose. The sections and keys below are the ones observed in the sample
systems; a shape not named here yields nothing rather than a guess.
"""

import re

PACKAGE_JSON = "package.json"
CONFIG_JSON = "config.json"
JS_SUFFIX = ".js"
NODE_MODULES = "node_modules"

DEPENDENCIES_KEY = "dependencies"
NAME_KEY = "name"

# Meta-data names
GRPC_SERVER = "GrpcServer"
"""Meta-data name of the gRPC endpoint a service serves."""

MESSAGE_QUEUE = "MessageQueue"
"""Meta-data name of a message queue a service is configured for."""

# Keys of those entries
HOST = "host"
PORT = "port"
QUEUE = "queue"
BROKER = "broker"
SCHEME = "scheme"
CREDENTIALS = "credentialsConfigured"
TRANSPORT_SECURITY = "transportSecurity"

UNRESOLVED = "UNRESOLVED"
"""Value of a fact the configuration alone does not state.

The scheme a messaging library speaks is the one such fact: a dependency that is
not in :data:`MESSAGING_SCHEMES` says nothing about the wire protocol, and a
guess is worse than a gap; see docs/node-plugin-plan.md §5.

The transport of a channel is no longer one of them. It is decided in the code
that opens the channel, which ``javascript.py`` reads by name, and it is stated
in the words of :class:`mrf.utilities.communication.Transport` - whose own
unresolved value is lower case, because that is what the detection compares
against.
"""

GRPC_SECTIONS = ["grpc", "gRPC"]
"""Sections of a configuration that address a gRPC endpoint."""

MESSAGING_SECTIONS = ["activemq", "amqp", "rabbitmq", "kafka", "mqtt", "stomp"]
"""Sections of a configuration that address a message broker."""

QUEUE_KEYS = ["queueName", "queue", "destination", "topic"]
"""Keys that name the queue or topic a service is configured for."""

USER_KEYS = ["username", "user", "login"]
PASSWORD_KEYS = ["password", "passcode", "secret"]

GRPC_DEPENDENCIES = ["@grpc/grpc-js", "grpc", "@grpc/proto-loader"]
"""Dependencies whose presence makes a service a gRPC peer."""

MESSAGING_SCHEMES = {
    "stompit": "stomp",
    "stompjs": "stomp",
    "@stomp/stompjs": "stomp",
    "amqplib": "amqp",
    "amqp-connection-manager": "amqp",
    "kafkajs": "kafka",
    "node-rdkafka": "kafka",
    "mqtt": "mqtt",
}
"""Scheme a messaging dependency speaks.

The library decides the wire protocol, which the configuration does not state: a
broker reached on port 61613 is addressed over STOMP because ``stompit`` is what
addresses it.
"""


# Names a channel's transport is read by, in the sources of a Node service.
# API of the libraries rather than a grammar: a call to one of them is the
# evidence. See mrf/plugins/service/node/javascript.py.

INSECURE_GRPC_SERVER = re.compile(r"ServerCredentials\s*\.\s*createInsecure\s*\(")
"""How a gRPC server states that it binds its port without TLS."""

SECURE_GRPC_SERVER = re.compile(r"ServerCredentials\s*\.\s*createSsl\s*\(")
"""How a gRPC server states that it binds its port with TLS."""

GRPC_CLIENT_AUTH_ARGUMENT = "true"
"""Third argument of ``createSsl`` that makes a client certificate required.

``createSsl(rootCerts, keyCertPairs, checkClientCertificate)`` requires and
verifies a client certificate only where it is given, and that is the half of
the refactoring mutual TLS adds over plain TLS.
"""

CLIENT_AUTH_REQUIRED = "need"
"""What a required client certificate is called, as ``ServerEndpoint`` calls it."""

SSL_OPTION = re.compile(r"""['\"]?ssl['\"]?\s*:\s*true""")
"""How a connection option asks a messaging library for TLS."""

MESSAGING_ANCHOR = re.compile(
    r"ConnectFailover|createConnection\s*\(|new\s+Kafka\s*\(|\bconnect\s*\("
)
"""Calls with which a messaging library opens a connection.

The anchor of the window the transport is read in. Matching the import of the
library instead would put the window around the whole file, and a file that
opens two channels would report the transport of one of them for both.
"""

MESSAGING_WINDOW = 30
"""Lines read on either side of the call that opens a connection.

Wide enough for the connection options of the libraries observed so far, and a
heuristic rather than a scope: options built further away than this are not
seen, and are reported as unresolved rather than as plaintext.
"""

TLS_URL_SCHEMES = ["ssl://", "stomp+ssl", "amqps://", "mqtt+ssl", "wss://"]
"""Schemes of a broker address that protect the channel on their own."""

SSL_CONFIG_KEY = "ssl"
"""Key with which a configuration states that a connection uses TLS.

``nconf`` reads a configuration that has no schema, so this is a convention of
the service rather than of a library: the key exists where the code that opens
the channel reads it from the configuration instead of hard-coding it.
"""
