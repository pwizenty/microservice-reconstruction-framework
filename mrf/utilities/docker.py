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

INFRASTRUCTURE_NODE_NAMES = [
    "eureka",
    "zuul",
    "gateway",
    "spring-boot-admin",
    "config-server",
    "service-registry",
]
"""Compose service names reconstructed as infrastructure nodes rather than
containers.

Recognition is by name, which ADR-0008 records as a decision to revisit: an
image name or the absence of a reconstructed microservice would be the
alternatives. The absence of a microservice is deliberately *not* used, because
a frontend has none either and is not infrastructure.
"""
