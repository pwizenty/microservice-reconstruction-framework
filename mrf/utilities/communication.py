"""Constants and vocabulary for reconstructing service-to-service communication.

Holds the Spring names a client call is recognised by and the values a
reconstructed fact may take. The values are the vocabulary of meta-data entries
rather than concepts of the architecture model, so they live here and not in
:mod:`mrf.modules` - see ADR-0009.
"""

from enum import Enum

# Meta-data names the facts are reported under
SERVICE_CALL = "ServiceCall"
"""Meta-data name of a single detected call to another service."""

SERVICE_CALL_ENDPOINT = "ServiceCallEndpoint"
"""Meta-data name of one endpoint of another service that a client declares.

Separate from :data:`SERVICE_CALL`, which reports the call and its transport: a
client may address several endpoints of the same service, and each is a
dependency of its own.
"""

SERVICE_COMMUNICATION_TRANSPORT = "ServiceCommunicationTransport"
"""Meta-data name of the transport a service uses for its calls.

Equal to the name of the service aspect a technology model of the LEMMA side
declares, because that is how a reconstructed annotation becomes an aspect.
"""

SERVER_ENDPOINT = "ServerEndpoint"
"""Meta-data name of a port a service itself answers on.

One entry per connector rather than one per service: Spring configures a main
connector and, where ``management.server.port`` is set, a second one, and the
two may differ in whether they use TLS. The task document asked for an
``additionalPlaintextPort`` field on a single record; a record per connector
says the same thing, generalises to a third connector, and needs no field whose
meaning depends on another record's.
"""

CONNECTOR = "connector"
"""Key naming which connector an endpoint belongs to."""

PORT = "port"
PROTOCOL = "protocol"
TLS_ENABLED = "tlsEnabled"
CLIENT_AUTH = "clientAuth"
VALUE_SOURCE = "valueSource"

MAIN_CONNECTOR = "server"
MANAGEMENT_CONNECTOR = "management"

SERVER_PORT = "server.port"
SERVER_SSL_PREFIX = "server.ssl."
MANAGEMENT_PORT = "management.server.port"
MANAGEMENT_SSL_PREFIX = "management.server.ssl."

SSL_ENABLED = "enabled"
SSL_CLIENT_AUTH = "client-auth"
SSL_KEY_STORE = "key-store"
SSL_BUNDLE = "bundle"
"""Spring property names under a connector's ``ssl.`` prefix.

``key-store`` and ``bundle`` matter because Spring switches TLS on when either
is configured: ``server.ssl.enabled`` defaults to true, so a key store without
it is still a TLS connector.
"""

DEFAULT_HTTP_PORT = "8080"
"""Port Spring listens on when nothing configures one."""

MESSAGE_CHANNEL = "MessageChannel"
"""Meta-data name of a queue a service produces to or consumes from.

A fact of its own beside :data:`SERVICE_CALL`, because the evidence of a
messaging channel is a queue and a broker rather than a verb and a path, and
because the refactoring differs: mutual TLS secures a call, a broker's ``ssl://``
secures a queue.
"""

ROLE = "role"
QUEUE = "queue"
BROKER = "broker"
BROKER_ADDRESS = "brokerAddress"
DEFAULTED = "defaulted"

ROLE_PRODUCER = "producer"
ROLE_CONSUMER = "consumer"

JMS_TEMPLATE = "JmsTemplate"
"""Type whose presence makes a class a producer."""

JMS_SEND_METHODS = ["convertAndSend", "send"]
"""Methods of a ``JmsTemplate`` whose first argument is the destination."""

JMS_LISTENER = "JmsListener"
JMS_LISTENER_DESTINATION = "destination"

VALUE_ANNOTATION = "Value"
"""Annotation whose single element holds the placeholder of a field."""

ACTIVEMQ_BROKER_URL = "spring.activemq.broker-url"
"""Property Spring reads a broker URL from."""

BROKER_SERVICE = "BrokerService"
ADD_CONNECTOR = "addConnector"
"""An embedded broker and the method that gives it a connector.

Lakeside Mutual configures no broker URL at all: policy-management-backend runs
the broker itself and adds its connectors from properties, so a client's
transport is only readable from the broker's own configuration.
"""

ACTIVEMQ = "activemq"
DEFAULT_BROKER_URL = "tcp://localhost:61616"
"""Broker URL ActiveMQ connects to when nothing configures one."""

PLAINTEXT_BROKER_SCHEMES = ["tcp", "stomp", "amqp", "mqtt", "ws", "nio", "vm"]
TLS_BROKER_SCHEMES = [
    "ssl",
    "stomp+ssl",
    "amqps",
    "mqtt+ssl",
    "wss",
    "nio+ssl",
    "https",
]
"""Broker URL schemes, by whether they protect the channel.

ActiveMQ names its TLS transports with an ``ssl`` suffix, so the scheme of a
connector decides the transport of everything on it.
"""


# Keys of a ServiceCall entry
TARGET = "target"
TARGET_KIND = "targetKind"
SCHEME = "scheme"
TECHNOLOGY = "technology"
PROPERTY = "property"
RESOLVED_URL = "resolvedUrl"
PROFILE = "profile"
FILE = "file"
LINE = "line"
SNIPPET = "snippet"
ARTIFACT_TYPE = "artifactType"
TRANSPORT = "transport"
TARGET_QUALIFIED_NAME = "targetQualifiedName"
VERB = "verb"
PATH = "path"
METHOD = "method"

SNIPPET_LENGTH = 120
"""Characters of a line kept as the evidence of a fact."""


class Scheme(Enum):
    """Transport a single call uses, as read from its URL."""

    HTTP = "http"
    HTTPS = "https"
    UNRESOLVED = "UNRESOLVED"


class TargetKind(Enum):
    """What a call addresses.

    A target is a ``SERVICE`` when its host is one of the microservices the
    reconstruction found, and ``EXTERNAL`` otherwise. ``INFRASTRUCTURE`` is
    reserved for the later step that reads the deployment, where a node that is
    no microservice can be told from a third party.
    """

    SERVICE = "SERVICE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    EXTERNAL = "EXTERNAL"


class ArtifactType(Enum):
    """Kind of artifact a fact was read from."""

    SOURCE = "SOURCE"
    CONFIGURATION = "CONFIGURATION"
    DEPLOYMENT = "DEPLOYMENT"


class Transport(Enum):
    """Transport a service uses for its calls to other services of the system.

    An aggregation of the schemes of those calls, and no judgement about them:
    deciding the security smell additionally needs what the callee accepts and
    whether a service mesh protects the channel, which this phase does not
    reconstruct. ``MIXED`` and ``UNRESOLVED`` exist so the aggregation never has
    to guess.
    """

    PLAINTEXT = "plaintext"
    TLS = "tls"
    MIXED = "mixed"
    UNRESOLVED = "unresolved"


# Spring annotations and elements a call is recognised by
FEIGN_CLIENT = "FeignClient"
VALUE_ANNOTATION = "Value"
FEIGN_URL_ELEMENT = "url"
FEIGN_NAME_ELEMENT = "name"

CLIENT_TYPES = ["RestTemplate", "RestClient", "WebClient"]
"""Types whose use makes a class a client of another service.

A class that names none of them and carries no ``@FeignClient`` is not a call
site, however many URLs it holds - a constant with a URL in it is no call.
"""

# Configuration a placeholder is resolved against
APPLICATION_PROPERTIES = "application.properties"
APPLICATION_YAML_NAMES = ["application.yml", "application.yaml"]
APPLICATION_PREFIX = "application-"
PROPERTIES_SUFFIX = ".properties"
YAML_SUFFIXES = [".yml", ".yaml"]
MAIN_RESOURCES = "src/main/resources"

PLACEHOLDER_PREFIX = "${"
PLACEHOLDER_SUFFIX = "}"
PLACEHOLDER_DEFAULT_SEPARATOR = ":"

# Everything below is excluded from the reconstruction
TEST_PATH_PARTS = ["src/test", "src/it"]
TEST_CLASS_SUFFIXES = ["Test", "Tests", "IT", "ITCase"]
MOCK_TYPES = ["WireMock", "MockServer", "MockRestServiceServer", "Testcontainers"]
"""Types of a test double. A URL handed to one of them addresses no service."""

SCHEMA_HOSTS = [
    "www.w3.org",
    "w3.org",
    "www.springframework.org",
    "springframework.org",
    "maven.apache.org",
    "xmlns.jcp.org",
    "java.sun.com",
    "javaee.github.io",
    "jakarta.ee",
]
"""Hosts of XML namespaces and schemas. They are identifiers, not addresses."""

LOCAL_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"]
"""Hosts that name the machine itself rather than a service.

A call to one of them is a call within the system - Lakeside Mutual's services
address each other as ``http://localhost:8110`` outside a container - so the
target is resolved by its port instead, and the call is never ``EXTERNAL``.
"""
