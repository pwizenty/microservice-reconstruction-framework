"""Tests for the reconstruction of what a service itself answers on.

Neither sample system available here configures TLS at all - Lakeside Mutual
sets only ``server.port`` on five services, park-and-charge only ``server.port``
in YAML on three - so every TLS-positive case is covered by a fixture
configuration rather than by real code. The plaintext case, which is the one the
security smell turns on, is covered by both.

Nothing here touches MongoDB.
"""

import pytest
from mrf.plugins.service.communication.configuration import ServiceConfiguration
from mrf.plugins.service.communication.server import UNRESOLVED, server_endpoints
from mrf.utilities.communication import (
    DEFAULT_HTTP_PORT,
    MAIN_CONNECTOR,
    MANAGEMENT_CONNECTOR,
)


def configuration(**properties: str) -> ServiceConfiguration:
    """A service configured with these properties, all from one file."""
    return ServiceConfiguration(
        module="service",
        properties=dict(properties),
        origins={
            name: "service/src/main/resources/application.properties"
            for name in properties
        },
    )


class TestMainConnector:
    """The connector every Spring service has."""

    def test_a_configured_port_is_reported_with_its_source(self) -> None:
        endpoints = server_endpoints(configuration(**{"server.port": "8110"}))

        assert len(endpoints) == 1
        assert endpoints[0].connector == MAIN_CONNECTOR
        assert endpoints[0].port == "8110"
        assert endpoints[0].protocol == "http"
        assert endpoints[0].tls_enabled is False
        assert endpoints[0].defaulted is False
        assert endpoints[0].value_source is not None

    def test_an_unconfigured_port_is_springs_default_and_says_so(self) -> None:
        """A service that configures nothing still listens, on 8080.

        Reported as defaulted rather than silently: a reader has to be able to
        tell a port the sources state from one the framework supplies.
        """
        endpoints = server_endpoints(configuration())

        assert endpoints[0].port == DEFAULT_HTTP_PORT
        assert endpoints[0].defaulted is True
        assert endpoints[0].value_source is None

    def test_a_placeholder_is_resolved_against_the_service(self) -> None:
        endpoints = server_endpoints(
            configuration(**{"server.port": "${app.port}", "app.port": "9443"})
        )

        assert endpoints[0].port == "9443"

    def test_an_unresolvable_placeholder_is_not_reported_as_a_port(self) -> None:
        """The text of a placeholder is not a port.

        Catches ``${PORT}`` being written into the facts as though it were one.
        """
        endpoints = server_endpoints(configuration(**{"server.port": "${PORT}"}))

        assert endpoints[0].port == UNRESOLVED

    def test_a_placeholder_default_is_used_when_nothing_resolves_it(self) -> None:
        endpoints = server_endpoints(configuration(**{"server.port": "${PORT:8443}"}))

        assert endpoints[0].port == "8443"


class TestTls:
    """Whether a connector uses TLS. No sample system configures any."""

    def test_enabled_true_is_tls(self) -> None:
        endpoints = server_endpoints(
            configuration(**{"server.port": "8443", "server.ssl.enabled": "true"})
        )

        assert endpoints[0].tls_enabled is True
        assert endpoints[0].protocol == "https"

    def test_enabled_false_is_not_tls_even_with_a_key_store(self) -> None:
        """An explicit ``false`` decides over the presence of a key store.

        Catches a key store being read as proof of TLS: a configuration can
        carry one and switch the connector off.
        """
        endpoints = server_endpoints(
            configuration(
                **{
                    "server.ssl.enabled": "false",
                    "server.ssl.key-store": "classpath:keystore.p12",
                }
            )
        )

        assert endpoints[0].tls_enabled is False
        assert endpoints[0].protocol == "http"

    @pytest.mark.parametrize("name", ["key-store", "bundle"])
    def test_a_key_store_or_bundle_without_enabled_is_tls(self, name: str) -> None:
        """Spring's ``server.ssl.enabled`` defaults to true.

        So a connector configured with a key store and no ``enabled`` is a TLS
        connector. Catches requiring ``enabled`` to be present, which would
        report a TLS service as plaintext.
        """
        endpoints = server_endpoints(
            configuration(**{f"server.ssl.{name}": "whatever"})
        )

        assert endpoints[0].tls_enabled is True

    def test_nothing_configured_is_not_tls(self) -> None:
        assert server_endpoints(configuration())[0].tls_enabled is False

    def test_client_auth_is_reported_as_configured(self) -> None:
        endpoints = server_endpoints(
            configuration(
                **{"server.ssl.enabled": "true", "server.ssl.client-auth": "need"}
            )
        )

        assert endpoints[0].client_auth == "need"

    def test_client_auth_is_absent_rather_than_guessed(self) -> None:
        """Nothing configured means nothing reported.

        Catches a default of ``none`` being invented: Spring's default is indeed
        none, but a fact the sources do not state is not a fact.
        """
        assert server_endpoints(configuration())[0].client_auth is None


class TestManagementConnector:
    """The second connector, and why it is a record of its own."""

    def test_it_is_reported_only_when_it_has_a_port(self) -> None:
        """Without its own port the management endpoints share the main one."""
        assert len(server_endpoints(configuration(**{"server.port": "8110"}))) == 1

    def test_a_plaintext_management_port_beside_a_tls_main_port(self) -> None:
        """The case the task document called ``additionalPlaintextPort``.

        Two records rather than a field: each says which connector it is and
        whether it uses TLS, which generalises and needs no field whose meaning
        depends on another record's.
        """
        endpoints = server_endpoints(
            configuration(
                **{
                    "server.port": "8443",
                    "server.ssl.enabled": "true",
                    "management.server.port": "9001",
                }
            )
        )

        assert [e.connector for e in endpoints] == [
            MAIN_CONNECTOR,
            MANAGEMENT_CONNECTOR,
        ]
        assert endpoints[0].tls_enabled is True
        assert endpoints[1].tls_enabled is False
        assert endpoints[1].port == "9001"

    def test_its_own_ssl_settings_are_read_from_its_own_prefix(self) -> None:
        """Catches the management connector inheriting the main connector's TLS.

        They are configured separately, so a TLS main port does not make the
        management port a TLS one.
        """
        endpoints = server_endpoints(
            configuration(
                **{
                    "server.port": "8443",
                    "server.ssl.enabled": "true",
                    "management.server.port": "9001",
                    "management.server.ssl.enabled": "true",
                    "management.server.ssl.client-auth": "want",
                }
            )
        )

        assert endpoints[1].tls_enabled is True
        assert endpoints[1].client_auth == "want"
