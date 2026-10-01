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

SERVICE_COMMUNICATION_TRANSPORT = "ServiceCommunicationTransport"
"""Meta-data name of the transport a service uses for its calls.

Equal to the name of the service aspect a technology model of the LEMMA side
declares, because that is how a reconstructed annotation becomes an aspect.
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
