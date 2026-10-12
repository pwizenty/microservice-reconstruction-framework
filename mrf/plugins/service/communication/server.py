"""What a service itself answers on: its ports, and whether they use TLS.

The client half of the *Non-Secured Service-to-Service Communications* smell is
reconstructed by the detectors: the address a client calls and the scheme it
calls it with. This module reconstructs the other half - what the callee
accepts - from the service's own Spring configuration.

Facts only, as ADR-0009 requires. That a service answers on a plaintext port is
not yet the smell: whether the channel is protected by a service mesh is not
reconstructed here, and the decision belongs to the LEMMA validation.

Only the default configuration is read. A profile that configures a different
port or enables TLS is a separate fact per profile, which needs the active
profile from the deployment to be worth reporting - see
``docs/s2s-communication-plugin-plan.md`` §6.
"""

import logging
from dataclasses import dataclass

from mrf.plugins.service.communication.configuration import (
    ServiceConfiguration,
    is_placeholder,
)
from mrf.utilities.communication import (
    DEFAULT_HTTP_PORT,
    MAIN_CONNECTOR,
    MANAGEMENT_CONNECTOR,
    MANAGEMENT_PORT,
    MANAGEMENT_SSL_PREFIX,
    SERVER_PORT,
    SERVER_SSL_PREFIX,
    SSL_BUNDLE,
    SSL_CLIENT_AUTH,
    SSL_ENABLED,
    SSL_KEY_STORE,
    Scheme,
)

logger = logging.getLogger(__name__)

UNRESOLVED = "unresolved"
"""Shown for a port a placeholder states and nothing in the service resolves.

Distinct from a port that is simply not configured, which Spring answers with
:data:`DEFAULT_HTTP_PORT`: this one says the model names a port and the
reconstruction could not follow it.
"""


@dataclass
class ServerEndpoint:
    """One connector of a service.

    Attributes:
        connector: ``server`` or ``management``
        port: Port it listens on, :data:`UNRESOLVED` for an unresolvable
            placeholder
        protocol: ``https`` when it uses TLS, ``http`` otherwise
        tls_enabled: Whether TLS is configured for it
        client_auth: What it requires of a client certificate - ``none``,
            ``want`` or ``need`` - or ``None`` when nothing configures it
        value_source: File the port was read from, or ``None`` when no file
            states one
        defaulted: Whether the port is Spring's default rather than configured
    """

    connector: str
    port: str
    protocol: str
    tls_enabled: bool
    client_auth: str | None = None
    value_source: str | None = None
    defaulted: bool = False


def server_endpoints(configuration: ServiceConfiguration) -> list[ServerEndpoint]:
    """Reconstruct the connectors a service answers on.

    The main connector always exists - a Spring service listens on
    :data:`DEFAULT_HTTP_PORT` when nothing configures a port - so it is reported
    whether or not the configuration mentions it. A management connector is
    reported only where ``management.server.port`` configures one, because
    without it the management endpoints share the main port and are not a
    connector of their own.

    Args:
        configuration: Configuration of the service

    Returns:
        [ServerEndpoint]: The connectors, main one first
    """
    endpoints = [
        __endpoint(configuration, MAIN_CONNECTOR, SERVER_PORT, SERVER_SSL_PREFIX)
    ]
    # Without a port of its own the management endpoints share the main
    # connector, so there is no second connector to report.
    if configuration.properties.get(MANAGEMENT_PORT) is not None:
        endpoints.append(
            __endpoint(
                configuration,
                MANAGEMENT_CONNECTOR,
                MANAGEMENT_PORT,
                MANAGEMENT_SSL_PREFIX,
            )
        )
    return endpoints


def __endpoint(
    configuration: ServiceConfiguration,
    connector: str,
    port_property: str,
    ssl_prefix: str,
) -> ServerEndpoint:
    """Read one connector of a service."""
    configured = configuration.properties.get(port_property)
    port, defaulted = __port(configured, port_property, configuration)
    tls_enabled = __tls_enabled(configuration, ssl_prefix)
    return ServerEndpoint(
        connector=connector,
        port=port,
        protocol=(Scheme.HTTPS if tls_enabled else Scheme.HTTP).value,
        tls_enabled=tls_enabled,
        client_auth=configuration.properties.get(f"{ssl_prefix}{SSL_CLIENT_AUTH}"),
        value_source=configuration.origins.get(port_property),
        defaulted=defaulted,
    )


def __port(
    configured: str | None, port_property: str, configuration: ServiceConfiguration
) -> tuple[str, bool]:
    """The port of a connector, and whether it is Spring's default.

    A port is often a placeholder, which the service's own configuration may
    resolve. One it does not resolve is reported as unresolved rather than as
    the literal ``${…}``: the text of a placeholder is not a port.
    """
    if configured is None:
        return DEFAULT_HTTP_PORT, True
    if not is_placeholder(configured):
        return configured, False

    resolved, _, _ = configuration.resolve(configured)
    if resolved is None or is_placeholder(resolved):
        logger.debug(
            "%s of %s is the placeholder %s and the service does not resolve it.",
            port_property,
            configuration.module,
            configured,
        )
        return UNRESOLVED, False
    return resolved, False


def __tls_enabled(configuration: ServiceConfiguration, ssl_prefix: str) -> bool:
    """Whether TLS is configured for a connector.

    ``enabled`` decides when it is set. When it is not, a key store or an SSL
    bundle decides: Spring's ``enabled`` defaults to true, so a connector with a
    key store and no ``enabled`` is a TLS connector. Nothing at all means no TLS,
    which is the case every service of the sample systems is in.
    """
    enabled = configuration.properties.get(f"{ssl_prefix}{SSL_ENABLED}")
    if enabled is not None:
        return enabled.strip().lower() == "true"

    return any(
        configuration.properties.get(f"{ssl_prefix}{name}") is not None
        for name in (SSL_KEY_STORE, SSL_BUNDLE)
    )
