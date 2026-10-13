"""Tests for the reconstruction of asynchronous service-to-service links.

The broker of every sample system available here is plaintext - Lakeside Mutual
runs an embedded ActiveMQ whose connectors are ``tcp://`` and ``stomp://``, and
``spring.activemq.broker-url`` is set nowhere - so every TLS case is a fixture
configuration rather than real code, as it is for the server endpoints.

Nothing here touches MongoDB.
"""

import pytest
from mrf.plugins.service.communication.broker import broker_of
from mrf.plugins.service.communication.configuration import ServiceConfiguration
from mrf.utilities.communication import DEFAULT_BROKER_URL, Transport


def configuration(module: str = "service", **properties: str) -> ServiceConfiguration:
    return ServiceConfiguration(
        module=module,
        properties=dict(properties),
        origins={name: f"{module}/application.properties" for name in properties},
    )


class TestBrokerResolution:
    """Where the broker URL comes from, in the order the sources offer it."""

    def test_the_service_own_broker_url_wins(self) -> None:
        broker = broker_of(
            configuration(**{"spring.activemq.broker-url": "ssl://broker:61617"}), {}
        )

        assert broker.url == "ssl://broker:61617"
        assert broker.transport is Transport.TLS
        assert broker.defaulted is False
        assert broker.value_source is not None

    def test_an_embedded_brokers_connector_is_used_when_the_service_has_no_url(
        self,
    ) -> None:
        """Lakeside Mutual's case, and the reason this takes every configuration.

        No service configures a broker URL: one of them *is* the broker and adds
        its connectors from its own properties. Catches reading only the
        service's own configuration, which reports every client as unresolved.
        """
        broker = broker_of(
            configuration("client"),
            {
                "broker": configuration(
                    "broker",
                    **{
                        "policymanagement.stompBrokerBindAddress": "stomp://0.0.0.0:61613",
                        "policymanagement.tcpBrokerBindAddress": "tcp://0.0.0.0:61616",
                    },
                )
            },
        )

        assert broker.transport is Transport.PLAINTEXT
        assert broker.url.startswith(("tcp://", "stomp://"))
        assert broker.defaulted is False

    def test_the_framework_default_is_used_last_and_says_so(self) -> None:
        """Catches a missing broker being reported as unresolved.

        ActiveMQ connects to tcp://localhost:61616 when nothing says otherwise,
        so the channel is plaintext - but a reader has to be able to tell that
        from a URL the sources state.
        """
        broker = broker_of(configuration(), {})

        assert broker.url == DEFAULT_BROKER_URL
        assert broker.transport is Transport.PLAINTEXT
        assert broker.defaulted is True
        assert broker.value_source is None

    @pytest.mark.parametrize(
        ("url", "transport"),
        [
            ("tcp://broker:61616", Transport.PLAINTEXT),
            ("stomp://broker:61613", Transport.PLAINTEXT),
            ("ssl://broker:61617", Transport.TLS),
            ("stomp+ssl://broker:61614", Transport.TLS),
            ("failover://broker:61616", Transport.UNRESOLVED),
        ],
    )
    def test_the_scheme_decides_the_transport(
        self, url: str, transport: Transport
    ) -> None:
        """ActiveMQ names its TLS transports with an ssl suffix.

        A scheme that is neither is unresolved rather than assumed plaintext:
        failover:// hides the transport of the URLs behind it.
        """
        broker = broker_of(configuration(**{"spring.activemq.broker-url": url}), {})

        assert broker.transport is transport

    def test_a_broker_offering_both_is_reported_as_the_least_protected(self) -> None:
        """A broker that accepts plaintext accepts plaintext.

        A conservative reading: the channel is only as protected as what the
        broker accepts, and a client that configures no URL of its own uses the
        plaintext default. It can over-report where a client does use the TLS
        connector, which no sample system does.
        """
        broker = broker_of(
            configuration("client"),
            {
                "broker": configuration(
                    "broker",
                    **{
                        "a.sslBrokerBindAddress": "ssl://0.0.0.0:61617",
                        "b.tcpBrokerBindAddress": "tcp://0.0.0.0:61616",
                    },
                )
            },
        )

        assert broker.transport is Transport.PLAINTEXT

    def test_a_placeholder_nothing_resolves_falls_through(self) -> None:
        broker = broker_of(
            configuration(**{"spring.activemq.broker-url": "${BROKER_URL}"}), {}
        )

        assert broker.defaulted is True
