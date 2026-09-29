"""Module with a summary of static variables."""

# Spring annotations
CONTEXT_ANNOTATION = "SpringBootApplication"
ENTITY_ANNOTATION = "Entity"
ID_ANNOTATIONS = ["Id", "EmbeddedId"]
SPRING_BOOT_APPLICATION = "SpringBootApplication"
REST_CONTROLLER = "RestController"
REST_OPERATIONS = ["PostMapping", "PutMapping", "GetMapping", "DeleteMapping"]
# Application class string
APPLICATION_CLASS = "Application"
CONTROLLER_CLASS = "Controller"
SERVICE_STRING = "Service"
# Spring infrastructure exclude list
INFRASTRUCTURE_TECHNOLOGIES = ["eureka", "zuul"]
"""Names of Spring infrastructure a microservice may be called after.

Kept for infrastructure that carries no annotation of its own. Matching a name
is a weak signal, so the annotations below are preferred where they exist.
"""

INFRASTRUCTURE_ANNOTATIONS = [
    "EnableAdminServer",
    "EnableEurekaServer",
    "EnableZuulProxy",
    "EnableConfigServer",
    "EnableDiscoveryServer",
]
"""Annotations that turn a Spring Boot application into infrastructure.

Such an application runs the system rather than being part of its domain, so
it is no bounded context and no microservice. The operation phase reconstructs
it as an infrastructure node, see ADR-0008.
"""
