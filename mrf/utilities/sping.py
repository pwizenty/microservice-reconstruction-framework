"""Module with a summary of static variables."""

# Spring annotations
CONTEXT_ANNOTATION = "SpringBootApplication"
ENTITY_ANNOTATION = "Entity"
ID_ANNOTATIONS = ["Id", "EmbeddedId"]
SPRING_BOOT_APPLICATION = "SpringBootApplication"
REST_CONTROLLER = "RestController"
REST_OPERATIONS = [
    "GetMapping",
    "PostMapping",
    "PutMapping",
    "PatchMapping",
    "DeleteMapping",
]
"""Annotations that make a method an operation of a REST interface.

Each of them is declared as a service aspect for operations by the technology
model the reconstruction is read with, so the annotation is carried over under
its own name.
"""

REQUEST_MAPPING = "RequestMapping"
"""Annotation that gives a controller or a method its path.

It is no service aspect of the technology model: a path is an endpoint address
in LEMMA rather than an aspect, so this annotation contributes an address and
nothing else.
"""

MAPPING_PATH_ELEMENTS = ["value", "path"]
"""Elements of a mapping annotation that hold its path.

Spring accepts both, and ``value`` is also the element of the shorthand
``@RequestMapping("/customers")``.
"""

OPERATION_ANNOTATIONS = ["PreAuthorize"]
"""Further annotations of a REST operation that are declared as service aspects.

Separate from :data:`REST_OPERATIONS` because these carry element values that
the aspect declares as properties, where a mapping annotation carries a path.
"""

PARAMETER_ANNOTATIONS = [
    "PathVariable",
    "RequestBody",
    "RequestParam",
    "Valid",
]
"""Annotations of a parameter that are declared as service aspects.

The technology model declares each of them for parameters, three of them with a
selector on the exchange pattern, which holds because Spring writes all four on
an incoming parameter.
"""

ENDPOINT = "Endpoint"
"""Meta-data name under which the reconstruction reports an endpoint.

An endpoint is no annotation, so it is reported under a name of its own rather
than under the name of the annotation its address was read from. Its address is
relative to the endpoint of the element above it, as it is in Spring and in
LEMMA alike.
"""

ENDPOINT_ADDRESS = "address"
"""Key under which an :data:`ENDPOINT` holds its address."""
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
