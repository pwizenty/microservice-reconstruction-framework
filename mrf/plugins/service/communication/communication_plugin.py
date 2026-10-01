"""Plugin reconstructing how a service calls the other services of a system.

Reads the client technologies of a service for the addresses they call, and
reports per service which transport those calls use. The facts are meta-data on
the reconstructed microservices, see ADR-0009.

The plugin collects facts and makes no judgement about them. Whether a link is
the security smell *Non-Secured Service-to-Service Communications* additionally
depends on what the callee accepts and on whether a service mesh protects the
channel, neither of which is reconstructed here; the decision belongs to the
LEMMA validation.
"""

import logging
from pathlib import PurePath

from mrf.modules.service import Microservice
from mrf.plugins.common.common_plugin import Data, JavaClassArtifact
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.plugins.service.communication.configuration import (
    ServiceConfiguration,
    module_of,
    read_configurations,
)
from mrf.plugins.service.communication.detectors import (
    DETECTORS,
    DetectionContext,
    ServiceCall,
)
from mrf.utilities.command_line import SourceFile
from mrf.utilities.communication import (
    ARTIFACT_TYPE,
    FILE,
    LINE,
    LOCAL_HOSTS,
    PROFILE,
    PROPERTY,
    RESOLVED_URL,
    SCHEME,
    SERVICE_CALL,
    SERVICE_COMMUNICATION_TRANSPORT,
    SNIPPET,
    TARGET,
    TARGET_KIND,
    TECHNOLOGY,
    TEST_CLASS_SUFFIXES,
    TEST_PATH_PARTS,
    TRANSPORT,
    Scheme,
    TargetKind,
    Transport,
)
from mrf.utilities.java_utils import get_class_from_tree, get_class_name, load_classes

logger = logging.getLogger(__name__)


class CommunicationPlugin(Plugin):
    """Reconstructs the outgoing calls of the services of a system."""

    def __init__(self) -> None:
        self.java_classes: list[JavaClassArtifact] = []
        self.configurations: dict[str, ServiceConfiguration] = {}
        # Calls that were found, by the module of the calling service.
        self.calls: dict[str, list[ServiceCall]] = {}

    def file_types(self) -> list[str]:
        """Return the file suffixes this plugin analyses.

        Returns:
            [str]: Java sources, and the configuration a placeholder is
            resolved against
        """
        return [".java", ".properties", ".yml", ".yaml"]

    def execute_reconstruction(
        self, source_files: list[SourceFile]
    ) -> dict[str, list[ServiceCall]]:
        """Reconstruct the calls the analysed system's services make.

        Which of the targets are services of the system is not decided here:
        that needs the reconstructed microservices, so call :meth:`assign_to`
        with them afterwards.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            dict[str, [ServiceCall]]: The calls that were found, by the module
            directory of the calling service
        """
        self.configurations = read_configurations(source_files)
        self.java_classes.extend(
            load_classes(self.__without_test_code(source_files), [".java"])
        )

        for java_class in self.java_classes:
            module = module_of(java_class.path)
            if module is None:
                continue
            context = DetectionContext(
                path=java_class.path,
                lines=(java_class.tree and []) or [],
                configuration=self.configurations.get(module),
            )
            context.lines = self.__lines_of(java_class.path, source_files)
            clazz = get_class_from_tree(java_class.tree)
            if self.__is_test_class(get_class_name(clazz)):
                continue
            for detector in DETECTORS:
                for call in detector.detect(clazz, java_class.tree, context):
                    self.calls.setdefault(module, []).append(call)

        return self.calls

    def assign_to(self, microservices: list[Microservice]) -> list[Microservice]:
        """Attach the reconstructed calls to the microservices that make them.

        A microservice belongs to the module the call was found in. Each call
        becomes one meta-data entry, and the transport of the calls to other
        services of the system becomes one more, which the LEMMA side turns
        into a service aspect.

        Args:
            microservices ([Microservice]): Reconstructed microservices

        Returns:
            [Microservice]: The microservices, with their calls assigned
        """
        if not microservices:
            logger.warning(
                "No microservice was reconstructed, so no call can be assigned "
                "to one. The communication phase needs the service phase; run "
                "the Spring plugin alongside it."
            )
            return microservices

        targets = self.__known_targets(microservices)
        for microservice in microservices:
            module = module_of(microservice.origin_file)
            if module is None:
                continue
            calls = self.__deduplicate(self.calls.get(module, []))
            if not calls:
                continue

            internal: list[Scheme] = []
            for call in calls:
                kind, target = self.__resolve_target(call, targets)
                microservice.data.append(self.__to_data(call, kind, target))
                if kind is not TargetKind.EXTERNAL:
                    internal.append(call.scheme)

            if internal:
                transport = Data(SERVICE_COMMUNICATION_TRANSPORT)
                transport.values = {TRANSPORT: self.__transport(internal).value}
                microservice.data.append(transport)

        return microservices

    def __known_targets(self, microservices: list[Microservice]) -> dict[str, str]:
        """Collect the names and ports the system's own services answer under.

        A client addresses a service by its name - a Compose service name, an
        application name or a Eureka service id - or, outside a container, as a
        port of the local machine. Both are collected so a target can be told
        from a third party.
        """
        targets: dict[str, str] = {}
        for microservice in microservices:
            module = module_of(microservice.origin_file)
            targets[self.__normalise(microservice.name)] = microservice.name
            configuration = self.configurations.get(module or "")
            if configuration is None:
                continue
            if configuration.application_name is not None:
                targets[self.__normalise(configuration.application_name)] = (
                    microservice.name
                )
            if configuration.server_port is not None:
                targets[f"port:{configuration.server_port}"] = microservice.name
        return targets

    def __resolve_target(
        self, call: ServiceCall, targets: dict[str, str]
    ) -> tuple[TargetKind, str]:
        """Decide what a call addresses, and name it.

        A target that is one of the system's own services is reported under the
        name the reconstruction knows it by, so a consumer need not match
        spellings a second time. The address the sources state stays in the
        ``resolvedUrl`` of the fact and in its evidence.

        Args:
            call: The reconstructed call
            targets: Names and ports the system's own services answer under

        Returns:
            The kind of the target and the name to report it under
        """
        known = targets.get(self.__normalise(call.target))
        if known is not None:
            return TargetKind.SERVICE, known

        if call.target.lower() in LOCAL_HOSTS:
            # The service addresses the machine itself, as Lakeside Mutual's
            # services do outside a container. Only the port says which service
            # answers there.
            if call.port is not None:
                answering = targets.get(f"port:{call.port}")
                if answering is not None:
                    return TargetKind.SERVICE, answering
            return TargetKind.EXTERNAL, self.__local_name(call)

        return TargetKind.EXTERNAL, call.target

    def __to_data(self, call: ServiceCall, kind: TargetKind, target: str) -> Data:
        values = {
            TARGET: target,
            TARGET_KIND: kind.value,
            SCHEME: call.scheme.value,
            TECHNOLOGY: call.technology,
            FILE: call.evidence.file,
            LINE: str(call.evidence.line),
            ARTIFACT_TYPE: call.evidence.artifact_type.value,
            SNIPPET: call.evidence.snippet,
        }
        if call.property_name is not None:
            values[PROPERTY] = call.property_name
        if call.resolved_url is not None:
            values[RESOLVED_URL] = call.resolved_url
        if call.profile is not None:
            values[PROFILE] = call.profile

        data = Data(SERVICE_CALL)
        data.values = values
        return data

    def __local_name(self, call: ServiceCall) -> str:
        """Name a local address no known service answers, by its port."""
        if call.port is not None:
            return f"{call.target}:{call.port}"
        return call.target

    def __transport(self, schemes: list[Scheme]) -> Transport:
        """Aggregate the schemes of a service's internal calls.

        An aggregation, not a judgement: ``MIXED`` and ``UNRESOLVED`` say what
        was found where a single value would have to be invented.
        """
        distinct = set(schemes)
        if Scheme.HTTP in distinct and Scheme.HTTPS in distinct:
            return Transport.MIXED
        if Scheme.HTTP in distinct:
            # A plaintext call stays the reported transport even beside a call
            # whose own transport could not be determined.
            return Transport.PLAINTEXT
        if Scheme.UNRESOLVED in distinct:
            # Not TLS: one call of unknown transport is enough to make the
            # transport of the service unknown, and reporting it as encrypted
            # would claim something the sources do not state.
            return Transport.UNRESOLVED
        return Transport.TLS

    def __deduplicate(self, calls: list[ServiceCall]) -> list[ServiceCall]:
        """Keep one call per address, and sort them so a run is repeatable."""
        unique: dict[tuple[str, str, str | None, str | None], ServiceCall] = {}
        for call in sorted(
            calls, key=lambda c: (c.evidence.file, c.evidence.line, c.target)
        ):
            key = (
                call.target,
                call.scheme.value,
                call.resolved_url,
                call.property_name,
            )
            unique.setdefault(key, call)
        return sorted(
            unique.values(),
            key=lambda c: (c.target, c.technology, c.evidence.file, c.evidence.line),
        )

    def __without_test_code(self, source_files: list[SourceFile]) -> list[SourceFile]:
        return [f for f in source_files if not self.__is_test_path(f.path)]

    def __is_test_path(self, path: str) -> bool:
        posix = PurePath(path).as_posix()
        return any(part in posix for part in TEST_PATH_PARTS)

    def __is_test_class(self, name: str) -> bool:
        return any(name.endswith(suffix) for suffix in TEST_CLASS_SUFFIXES)

    def __lines_of(self, path: str, source_files: list[SourceFile]) -> list[str]:
        source_file = next((f for f in source_files if f.path == path), None)
        if source_file is None or source_file.file is None:
            return []
        return source_file.file.splitlines()

    def __normalise(self, name: str) -> str:
        """Reduce a name to what a comparison can rely on.

        ``customer-core``, ``CustomerCore`` and ``customercore`` are the same
        service under three spellings, and a client uses whichever the
        configuration gives it.
        """
        return "".join(c for c in name.lower() if c.isalnum())
