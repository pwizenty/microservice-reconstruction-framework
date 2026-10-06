"""Constants for reconstructing from the manifest and configuration of Node.

A Node service states its name and its dependencies in ``package.json``, which
is a standard, and its addresses in a configuration file of its own, which is
not: ``nconf`` reads whatever file it is pointed at, under whatever keys the
service chose. The sections and keys below are the ones observed in the sample
systems; a shape not named here yields nothing rather than a guess.
"""

PACKAGE_JSON = "package.json"
CONFIG_JSON = "config.json"
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

Whether a channel is encrypted is decided in the code that opens it, which this
step does not read. Absence of a TLS section is not evidence of plaintext, so it
is reported as unresolved rather than guessed; see docs/node-plugin-plan.md §5.
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
