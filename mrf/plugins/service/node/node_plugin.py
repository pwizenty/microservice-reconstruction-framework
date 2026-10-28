"""Node plugin reconstructing what a Node service serves and is configured for.

Reads the two structured files a Node service has - ``package.json``, which
names it and its dependencies, and its own configuration file, which holds the
addresses - and the transport of its channels from its sources, by name rather
than by parsing them (``javascript.py``). The addresses are configuration; which
of them is encrypted is decided in the code that opens the channel, so a
configuration alone leaves every transport unresolved.

What the facts are attached to is the microservice another plugin reconstructed
for the same service - the Protobuf plugin, for a service with a gRPC contract.
This plugin reconstructs no microservice of its own: a ``package.json`` says
that something is a Node project, not that it is a service of the architecture,
and the three frontends of Lakeside Mutual have one too.
"""

import json
import logging
from pathlib import PurePath

from mrf.modules.service import Microservice
from mrf.plugins.common.common_plugin import Data
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.plugins.service.node.javascript import (
    TransportEvidence,
    grpc_server_transport,
    messaging_transport,
)
from mrf.utilities.command_line import SourceFile
from mrf.utilities.communication import CLIENT_AUTH, VALUE_SOURCE, Transport
from mrf.utilities.node import (
    BROKER,
    CONFIG_JSON,
    CREDENTIALS,
    DEPENDENCIES_KEY,
    GRPC_DEPENDENCIES,
    GRPC_SECTIONS,
    GRPC_SERVER,
    HOST,
    JS_SUFFIX,
    MESSAGE_QUEUE,
    MESSAGING_SCHEMES,
    MESSAGING_SECTIONS,
    NODE_MODULES,
    PACKAGE_JSON,
    PASSWORD_KEYS,
    PORT,
    QUEUE,
    QUEUE_KEYS,
    SCHEME,
    SSL_CONFIG_KEY,
    TRANSPORT_SECURITY,
    UNRESOLVED,
    USER_KEYS,
)

logger = logging.getLogger(__name__)


class NodePlugin(Plugin):
    """Reconstructs the endpoints and queues a Node service is configured for."""

    def __init__(self) -> None:
        # What was read, by the directory of the service it was read from.
        self.manifests: dict[str, dict] = {}
        self.configurations: dict[str, dict] = {}
        # Sources, by their own path: which service they belong to is decided
        # with the manifests, in assign_to.
        self.sources: dict[str, str] = {}

    def file_types(self) -> list[str]:
        """Return the file suffixes this plugin analyses.

        Returns:
            [str]: The suffix of a manifest and of a configuration, and that of
            the sources the transport of a channel is read from
        """
        return [".json", JS_SUFFIX]

    def execute_reconstruction(self, source_files: list[SourceFile]) -> dict[str, dict]:
        """Read the manifest and the configuration of every Node service.

        Which microservice they belong to is not decided here: that needs the
        microservices of the other plugins of this phase, so call
        :meth:`assign_to` with them afterwards.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            dict[str, dict]: The manifest of each service, by its directory
        """
        for source_file in self.__json_files(source_files, PACKAGE_JSON):
            directory = str(PurePath(source_file.path).parent)
            self.manifests[directory] = self.__read(source_file)

        for source_file in self.__json_files(source_files, CONFIG_JSON):
            directory = str(PurePath(source_file.path).parent)
            self.configurations[directory] = self.__read(source_file)

        for source_file in self.__sources(source_files):
            self.sources[source_file.path] = source_file.file or ""

        return self.manifests

    def assign_to(self, microservices: list[Microservice]) -> list[Microservice]:
        """Attach what was read to the microservices it describes.

        A microservice belongs to a Node service when the artifact it was
        reconstructed from lies in the service's directory - a proto file beside
        the manifest, say. A directory with no microservice is left alone, which
        is what keeps a frontend out of the model: it has a manifest and no
        service was reconstructed for it.

        Args:
            microservices ([Microservice]): Reconstructed microservices

        Returns:
            [Microservice]: The microservices, with their facts assigned
        """
        for directory in sorted(self.manifests):
            manifest = self.manifests[directory]
            configuration = self.configurations.get(directory, {})
            dependencies = self.__dependencies(manifest)

            for microservice in microservices:
                if not self.__belongs_to(microservice.origin_file, directory):
                    continue
                microservice.data.extend(
                    self.__facts(configuration, dependencies, directory)
                )

        return microservices

    def __facts(
        self, configuration: dict, dependencies: set[str], directory: str
    ) -> list[Data]:
        """Build the facts a service's configuration and sources state."""
        facts: list[Data] = []
        sources = self.__sources_of(directory)

        grpc = self.__section(configuration, GRPC_SECTIONS)
        if grpc is not None and dependencies & set(GRPC_DEPENDENCIES):
            data = Data(GRPC_SERVER)
            data.values = self.__address(grpc)
            self.__add_transport(data.values, grpc_server_transport(sources))
            facts.append(data)
        elif grpc is not None:
            logger.debug(
                "%s configures a gRPC endpoint but depends on no gRPC library.",
                directory,
            )

        for section_name in MESSAGING_SECTIONS:
            section = configuration.get(section_name)
            if not isinstance(section, dict):
                continue
            data = Data(MESSAGE_QUEUE)
            values = self.__address(section)
            values[BROKER] = section_name
            queue = self.__first(section, QUEUE_KEYS)
            if queue is not None:
                values[QUEUE] = queue
            values[SCHEME] = self.__scheme(dependencies)
            values[CREDENTIALS] = str(self.__has_credentials(section)).lower()
            # A credential is never reported, only that one is configured: the
            # architecture information is that the broker is authenticated, and
            # the value is a secret.
            self.__add_transport(
                values, self.__messaging_transport(sources, section, directory)
            )
            data.values = values
            facts.append(data)

        return facts

    def __add_transport(
        self, values: dict[str, str], evidence: TransportEvidence
    ) -> None:
        """Add what was read about a channel's transport to a fact.

        The transport is always stated, unresolved included, so that a channel
        whose sources were not read and a channel that is protected do not look
        alike. What is only stated where it was read is the client certificate
        and the file the evidence comes from.

        Args:
            values (dict[str, str]): Values of the fact, extended in place
            evidence (TransportEvidence): What the sources state
        """
        values[TRANSPORT_SECURITY] = evidence.transport
        if evidence.client_auth is not None:
            values[CLIENT_AUTH] = evidence.client_auth
        if evidence.value_source is not None:
            values[VALUE_SOURCE] = evidence.value_source

    def __messaging_transport(
        self, sources: dict[str, str], section: dict, directory: str
    ) -> TransportEvidence:
        """Read the transport of a broker connection, sources before settings.

        The sources decide, because they are what opens the channel. A service
        that reads the decision from its own configuration instead - an ``ssl``
        key the code passes on - is the one case where the settings state it,
        and then the configuration is the evidence.

        Args:
            sources (dict[str, str]): Contents of the service's sources, by path
            section (dict): The section that addresses the broker
            directory (str): Directory of the service, for the evidence

        Returns:
            TransportEvidence: What the service states
        """
        evidence = messaging_transport(sources)
        if evidence.transport != Transport.UNRESOLVED.value:
            return evidence
        if section.get(SSL_CONFIG_KEY) is True:
            return TransportEvidence(
                Transport.TLS.value,
                None,
                str(PurePath(directory) / CONFIG_JSON),
            )
        return evidence

    def __sources_of(self, directory: str) -> dict[str, str]:
        """Return the contents of the sources of one service, by path."""
        return {
            path: content
            for path, content in self.sources.items()
            if self.__belongs_to(path, directory)
        }

    def __address(self, section: dict) -> dict[str, str]:
        """Read the host and the port a section addresses."""
        values: dict[str, str] = {}
        host = section.get(HOST)
        if isinstance(host, str) and host:
            values[HOST] = host
        port = section.get(PORT)
        if isinstance(port, int | str) and str(port):
            values[PORT] = str(port)
        return values

    def __scheme(self, dependencies: set[str]) -> str:
        """Return the scheme a service's messaging dependency speaks."""
        for dependency, scheme in MESSAGING_SCHEMES.items():
            if dependency in dependencies:
                return scheme
        return UNRESOLVED

    def __has_credentials(self, section: dict) -> bool:
        """Check whether a section configures a user and a password."""
        return (
            self.__first(section, USER_KEYS) is not None
            and self.__first(section, PASSWORD_KEYS) is not None
        )

    def __first(self, section: dict, keys: list[str]) -> str | None:
        """Return the value of the first of the keys the section holds."""
        for key in keys:
            value = section.get(key)
            if isinstance(value, int | str) and str(value):
                return str(value)
        return None

    def __section(self, configuration: dict, names: list[str]) -> dict | None:
        """Return the first of the named sections the configuration holds."""
        for name in names:
            section = configuration.get(name)
            if isinstance(section, dict):
                return section
        return None

    def __dependencies(self, manifest: dict) -> set[str]:
        """Return the names of a manifest's dependencies."""
        dependencies = manifest.get(DEPENDENCIES_KEY)
        return set(dependencies) if isinstance(dependencies, dict) else set()

    def __belongs_to(self, origin_file: str, directory: str) -> bool:
        """Check whether an artifact lies in a service's directory."""
        return PurePath(origin_file).is_relative_to(PurePath(directory))

    def __json_files(
        self, source_files: list[SourceFile], name: str
    ) -> list[SourceFile]:
        """Return the files of a name, outside the installed dependencies."""
        return sorted(
            (
                f
                for f in source_files
                if f.file is not None
                and PurePath(f.path).name == name
                and NODE_MODULES not in PurePath(f.path).parts
            ),
            key=lambda f: f.path,
        )

    def __sources(self, source_files: list[SourceFile]) -> list[SourceFile]:
        """Return the sources of the system, outside the installed dependencies.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            [SourceFile]: The JavaScript sources, in a stable order
        """
        return sorted(
            (
                f
                for f in source_files
                if f.file is not None
                and f.suffix == JS_SUFFIX
                and NODE_MODULES not in PurePath(f.path).parts
            ),
            key=lambda f: f.path,
        )

    def __read(self, source_file: SourceFile) -> dict:
        """Read a JSON file, or nothing when it cannot be read."""
        try:
            content = json.loads(source_file.file or "")
        except json.JSONDecodeError:
            logger.warning("Skipping %s, it is no valid JSON.", source_file.path)
            return {}
        return content if isinstance(content, dict) else {}
