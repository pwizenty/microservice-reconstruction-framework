"""Constants of the Docker artifacts the operation phase reads."""

COMPOSE_FILE_NAMES = ["docker-compose.yml", "docker-compose.yaml"]
"""File names a Docker Compose specification may have."""

DOCKERFILE_NAME = "Dockerfile"
"""File name of a Dockerfile."""

COMPOSE_SERVICES_KEY = "services"
COMPOSE_BUILD_KEY = "build"
COMPOSE_CONTEXT_KEY = "context"
COMPOSE_IMAGE_KEY = "image"
COMPOSE_DEPENDS_ON_KEY = "depends_on"

DOCKERFILE_FROM = "FROM"
"""Instruction naming the base image a container runs on."""

CONTAINER_SUFFIX = "Container"
"""Appended to the name of a container node, as LEMMA's examples do."""

COMPOSE_SERVICE = "ComposeService"
"""Meta-data name holding the service name of the Compose specification."""

APPLICATION_PROPERTIES = "application.properties"
"""File name of the Spring configuration of a service."""

MAIN_RESOURCES = "src/main/resources"
"""Folder the configuration of a service is read from.

A service also has a configuration below ``src/test/resources``, which
configures its tests rather than its deployment.
"""

SERVICE_PROPERTIES = "ServiceProperties"
"""Meta-data name holding the deployment configuration of a node."""

CONFIGURATION_PROPERTIES = {
    "spring.application.name": "springApplicationName",
    "server.port": "serverPort",
}
"""Properties read from the Spring configuration, by the name a LEMMA
technology model declares them under.

The reconstruction reports a value under the name the technology model uses, so
that an operation model can assign it without translating anything. See the
technology models of the LEMMA reconstruction bundle.
"""

INFRASTRUCTURE_NODE_NAMES = [
    "eureka",
    "zuul",
    "gateway",
    "spring-boot-admin",
    "config-server",
    "service-registry",
    "proxy",
    "nginx",
]
"""Compose service names reconstructed as infrastructure nodes rather than
containers.

Recognition is by name, which ADR-0008 records as a decision to revisit: an
image name or the absence of a reconstructed microservice would be the
alternatives. The absence of a microservice is deliberately *not* used, because
a frontend has none either and is not infrastructure.
"""
