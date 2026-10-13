"""The message broker a service talks to, and whether that channel is protected.

A broker URL's scheme decides the transport: ActiveMQ names its TLS transports
with an ``ssl`` suffix, so ``tcp://`` and ``stomp://`` are plaintext and
``ssl://`` and ``stomp+ssl://`` are not.

Where the URL comes from is the part that needed looking at rather than
assuming. Lakeside Mutual configures no broker URL at all: the
policy-management-backend runs the broker itself with
``BrokerService.addConnector(…)``, taking the connector addresses from its own
properties. A client of that broker therefore has no URL of its own, and its
transport is only readable from the broker's configuration - which is why this
module takes the configurations of every service rather than one.
"""

import logging
from dataclasses import dataclass

from mrf.plugins.service.communication.configuration import (
    ServiceConfiguration,
    is_placeholder,
)
from mrf.utilities.communication import (
    ACTIVEMQ,
    ACTIVEMQ_BROKER_URL,
    DEFAULT_BROKER_URL,
    PLAINTEXT_BROKER_SCHEMES,
    TLS_BROKER_SCHEMES,
    Transport,
)

logger = logging.getLogger(__name__)

CONNECTOR_PROPERTY_HINTS = ["brokerbindaddress", "brokerurl", "broker-url"]
"""Parts of a property name that holds a broker address.

An embedded broker takes its connectors from properties whose names the
application chooses - ``policymanagement.tcpBrokerBindAddress`` here - so the
name is matched rather than looked up.
"""


@dataclass
class Broker:
    """The broker a service's messages pass through.

    Attributes:
        url: Address the broker is reached at
        scheme: Scheme of that address
        transport: Whether the channel is protected
        defaulted: Whether the URL is the framework's default rather than
            configured
        value_source: File the address was read from, or ``None``
    """

    url: str
    scheme: str
    transport: Transport
    defaulted: bool = False
    value_source: str | None = None

    @property
    def name(self) -> str:
        """The broker technology, as far as the sources name it."""
        return ACTIVEMQ


def broker_of(
    configuration: ServiceConfiguration | None,
    configurations: dict[str, ServiceConfiguration],
) -> Broker:
    """Reconstruct the broker a service talks to.

    Read in the order the sources make available: the service's own broker URL,
    then the connectors of a broker embedded in any service of the system, then
    the framework's default.

    Args:
        configuration: Configuration of the service, or ``None``
        configurations: Configuration of every service of the system

    Returns:
        Broker: The broker, with its transport
    """
    own = __configured_url(configuration)
    if own is not None:
        url, source = own
        return __broker(url, source)

    embedded = __embedded_connector(configurations)
    if embedded is not None:
        url, source = embedded
        return __broker(url, source)

    logger.debug(
        "Nothing configures a broker URL, so %s is reported as the default.",
        DEFAULT_BROKER_URL,
    )
    return __broker(DEFAULT_BROKER_URL, None, defaulted=True)


def __configured_url(
    configuration: ServiceConfiguration | None,
) -> tuple[str, str | None] | None:
    """The broker URL a service configures for itself, if any."""
    if configuration is None:
        return None
    url = configuration.properties.get(ACTIVEMQ_BROKER_URL)
    if url is None:
        return None
    if is_placeholder(url):
        resolved, _, _ = configuration.resolve(url)
        if resolved is None or is_placeholder(resolved):
            return None
        url = resolved
    return url, configuration.origins.get(ACTIVEMQ_BROKER_URL)


def __embedded_connector(
    configurations: dict[str, ServiceConfiguration],
) -> tuple[str, str | None] | None:
    """A connector of a broker embedded in one of the system's services.

    The least protected connector wins: a broker that offers both a plaintext
    and a TLS connector accepts plaintext, and the channel is only as protected
    as what it accepts.
    """
    found: list[tuple[str, str | None]] = []
    for module in sorted(configurations):
        configuration = configurations[module]
        for name in sorted(configuration.properties):
            if not __names_a_connector(name):
                continue
            url = configuration.properties[name]
            if is_placeholder(url) or "://" not in url:
                continue
            found.append((url, configuration.origins.get(name)))

    if not found:
        return None
    plaintext = [
        entry
        for entry in found
        if __transport_of(__scheme_of(entry[0])) is Transport.PLAINTEXT
    ]
    return plaintext[0] if plaintext else found[0]


def __names_a_connector(property_name: str) -> bool:
    lowered = property_name.lower()
    return any(hint in lowered for hint in CONNECTOR_PROPERTY_HINTS)


def __broker(url: str, source: str | None, defaulted: bool = False) -> Broker:
    scheme = __scheme_of(url)
    return Broker(
        url=url,
        scheme=scheme,
        transport=__transport_of(scheme),
        defaulted=defaulted,
        value_source=source,
    )


def __scheme_of(url: str) -> str:
    scheme, separator, _ = url.partition("://")
    return scheme.strip().lower() if separator else ""


def __transport_of(scheme: str) -> Transport:
    if scheme in TLS_BROKER_SCHEMES:
        return Transport.TLS
    if scheme in PLAINTEXT_BROKER_SCHEMES:
        return Transport.PLAINTEXT
    return Transport.UNRESOLVED
