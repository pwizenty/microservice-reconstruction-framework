"""Docker plugin reconstructing operation nodes.

Analyses a Docker Compose specification for the nodes of a system and the
dependencies between them, and the Dockerfile of a node for the environment it
runs on. See ADR-0008 for what is reconstructed and what is deliberately left
to LEMMA.
"""

import json
import logging
import os
from pathlib import PurePath

import yaml

from mrf.modules.operation import DeployedService, NodeType, OperationNode
from mrf.modules.service import Microservice
from mrf.plugins.common.common_plugin import Data
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.docker import (
    APPLICATION_PROPERTIES,
    COMPOSE_BUILD_KEY,
    COMPOSE_CONTEXT_KEY,
    COMPOSE_DEPENDS_ON_KEY,
    COMPOSE_FILE_NAMES,
    COMPOSE_SERVICE,
    COMPOSE_SERVICES_KEY,
    CONFIG_JSON,
    CONFIG_PORT_KEY,
    CONFIG_PORT_SECTIONS,
    CONFIGURATION_PROPERTIES,
    CONTAINER_SUFFIX,
    DOCKERFILE_FROM,
    DOCKERFILE_NAME,
    INFRASTRUCTURE_NODE_NAMES,
    MAIN_RESOURCES,
    NODE_MODULES,
    PACKAGE_JSON,
    PACKAGE_NAME_KEY,
    SERVICE_PROPERTIES,
)

logger = logging.getLogger(__name__)


class DockerPlugin(Plugin):
    """Reconstructs operation nodes from Docker artifacts."""

    def __init__(self) -> None:
        self.nodes: list[OperationNode] = []
        # Build directory of each node, kept to resolve the microservices a
        # container deploys once they are known.
        self.build_directories: dict[str, str] = {}
        # Compose specification each node was reconstructed from.
        self.defining_files: dict[str, str] = {}

    def file_types(self) -> list[str]:
        """Return the file suffixes this plugin analyses.

        Returns:
            [str]: Suffixes of Compose specifications, and the empty suffix of
            a Dockerfile.
        """
        return [".yml", ".yaml", ".properties", ""]

    def execute_reconstruction(
        self, source_files: list[SourceFile]
    ) -> list[OperationNode]:
        """Reconstruct the operation nodes of the analysed system.

        The microservices a container deploys are not assigned here: they are
        the result of the service phase. Call :meth:`assign_deployed_services`
        with them afterwards.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            [OperationNode]: Reconstructed operation nodes
        """
        compose_files = [
            f
            for f in source_files
            if f.file is not None and PurePath(f.path).name in COMPOSE_FILE_NAMES
        ]
        if not compose_files:
            logger.warning(
                "No Docker Compose specification found, no operation node "
                "is reconstructed. The operation phase reads the system's root."
            )
            return self.nodes

        # A system may hold several specifications - Lakeside Mutual has one
        # per deployment variant. The one closest to the root describes the
        # system itself, the deeper ones are alternatives for it, so the
        # shallowest wins and the others only add nodes it does not define.
        compose_files.sort(key=lambda f: (len(PurePath(f.path).parts), f.path))
        for compose_file in compose_files:
            self.__reconstruct_compose_file(compose_file, source_files)
        return self.nodes

    def assign_deployed_services(
        self, microservices: list[Microservice]
    ) -> list[OperationNode]:
        """Assign the microservices the reconstructed containers deploy.

        A microservice belongs to a container when the artifact it was
        reconstructed from lies below the build directory of the container's
        Compose service.

        Args:
            microservices ([Microservice]): Reconstructed microservices

        Returns:
            [OperationNode]: The nodes, with their deployed services assigned
        """
        for node in self.nodes:
            if node.node_type is not NodeType.CONTAINER:
                continue
            directory = self.build_directories.get(node.name)
            if directory is None:
                continue
            for microservice in microservices:
                if self.__lies_below(microservice.origin_file, directory):
                    node.deployed_services.append(
                        DeployedService(microservice.name, microservice.qualified_name)
                    )
        return self.nodes

    def __reconstruct_compose_file(
        self, compose_file: SourceFile, source_files: list[SourceFile]
    ) -> None:
        try:
            specification = yaml.safe_load(compose_file.file)
        except yaml.YAMLError:
            logger.warning("Skipping %s, it is no valid YAML.", compose_file.path)
            return
        if not isinstance(specification, dict):
            logger.warning("Skipping %s, it holds no mapping.", compose_file.path)
            return

        services = specification.get(COMPOSE_SERVICES_KEY) or {}
        compose_directory = str(PurePath(compose_file.path).parent)

        for service_name, service in services.items():
            service = service or {}
            node = self.__reconstruct_node(service_name, service)
            if any(existing.name == node.name for existing in self.nodes):
                logger.debug(
                    "%s already defines the node %s, %s is ignored for it.",
                    self.defining_files.get(node.name),
                    node.name,
                    compose_file.path,
                )
                continue
            self.defining_files[node.name] = compose_file.path
            directory = self.__build_directory(compose_directory, service)
            if directory is not None:
                self.build_directories[node.name] = directory
                node.operation_environment = self.__find_operation_environment(
                    directory, source_files
                )
                self.__assign_configuration(node, directory, source_files)
            node.origin_file = compose_file.path
            self.nodes.append(node)

    def __reconstruct_node(self, service_name: str, service: dict) -> OperationNode:
        node_type = (
            NodeType.INFRASTRUCTURE
            if self.__is_infrastructure(service_name)
            else NodeType.CONTAINER
        )
        name = self.__node_name(service_name, node_type)
        node = OperationNode(name, name, node_type)
        node.depends_on.extend(self.__depends_on(service))

        data = Data(COMPOSE_SERVICE)
        data.values = {"Name": service_name}
        node.data.append(data)
        return node

    def __is_infrastructure(self, service_name: str) -> bool:
        return any(n in service_name.lower() for n in INFRASTRUCTURE_NODE_NAMES)

    def __node_name(self, service_name: str, node_type: NodeType) -> str:
        parts = [p for p in service_name.replace("_", "-").split("-") if p]
        name = "".join(p[:1].upper() + p[1:] for p in parts)
        if node_type is NodeType.CONTAINER:
            return name + CONTAINER_SUFFIX
        return name

    def __depends_on(self, service: dict) -> list[str]:
        depends_on = service.get(COMPOSE_DEPENDS_ON_KEY) or []
        # Compose allows both a list of service names and a mapping of them to
        # conditions.
        names = list(depends_on) if not isinstance(depends_on, str) else [depends_on]
        return [
            self.__node_name(
                name,
                NodeType.INFRASTRUCTURE
                if self.__is_infrastructure(name)
                else NodeType.CONTAINER,
            )
            for name in names
        ]

    def __build_directory(self, compose_directory: str, service: dict) -> str | None:
        build = service.get(COMPOSE_BUILD_KEY)
        if isinstance(build, dict):
            build = build.get(COMPOSE_CONTEXT_KEY)
        if not isinstance(build, str):
            return None
        # A specification below the root reaches its build contexts through
        # "..", and is_relative_to compares lexically, so the path has to be
        # normalised before anything is matched against it.
        return os.path.normpath(str(PurePath(compose_directory) / build))

    def __find_operation_environment(
        self, directory: str, source_files: list[SourceFile]
    ) -> str | None:
        dockerfile = next(
            (
                f
                for f in source_files
                if f.file is not None
                and PurePath(f.path).name == DOCKERFILE_NAME
                and self.__lies_below(f.path, directory)
            ),
            None,
        )
        if dockerfile is None:
            return None
        return self.__base_image(dockerfile.file)

    def __assign_configuration(
        self, node: OperationNode, directory: str, source_files: list[SourceFile]
    ) -> None:
        """Read the deployment configuration of a node from its service.

        Reports the values under the names a LEMMA technology model declares
        them with, so that an operation model assigns them without translating
        anything.
        """
        configuration = next(
            (
                f
                for f in source_files
                if f.file is not None
                and PurePath(f.path).name == APPLICATION_PROPERTIES
                and self.__lies_below(f.path, directory)
                and MAIN_RESOURCES in PurePath(f.path).as_posix()
            ),
            None,
        )
        if configuration is None:
            logger.debug("No %s below %s", APPLICATION_PROPERTIES, directory)
            values = self.__read_node_configuration(directory, source_files)
        else:
            values = self.__read_properties(configuration.file)

        if not values:
            return

        data = Data(SERVICE_PROPERTIES)
        data.values = values
        node.data.append(data)

    def __read_node_configuration(
        self, directory: str, source_files: list[SourceFile]
    ) -> dict[str, str]:
        """Read the deployment configuration of a service that is not Spring.

        A node a container deploys has to be configured whatever it is written
        in: the technology model marks the application name and the port as
        mandatory of every container that deploys a service, so a service with
        no Spring configuration would otherwise be reconstructed into a
        container the Operation DSL rejects.

        A Node service states its name in its ``package.json`` and the port it
        listens on in its own configuration file. The names reported are the
        ones the technology model declares, exactly as for a Spring service -
        they belong to the model rather than to Spring.

        Args:
            directory (str): Build directory of the container
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            dict[str, str]: The configuration, empty when the service states
                none
        """
        values: dict[str, str] = {}

        manifest = self.__configuration_file(PACKAGE_JSON, directory, source_files)
        if manifest is not None:
            name = self.__read_json(manifest).get(PACKAGE_NAME_KEY)
            if isinstance(name, str) and name:
                values[CONFIGURATION_PROPERTIES["spring.application.name"]] = name

        configuration = self.__configuration_file(CONFIG_JSON, directory, source_files)
        if configuration is not None:
            port = self.__read_port(self.__read_json(configuration))
            if port is not None:
                values[CONFIGURATION_PROPERTIES["server.port"]] = port

        return values

    def __configuration_file(
        self, name: str, directory: str, source_files: list[SourceFile]
    ) -> SourceFile | None:
        """Find a configuration file of a service, nearest to its root first.

        A dependency of a Node service brings a ``package.json`` of its own, so
        the shallowest one below the build directory is the service's.
        """
        candidates = sorted(
            (
                f
                for f in source_files
                if f.file is not None
                and PurePath(f.path).name == name
                and self.__lies_below(f.path, directory)
                and NODE_MODULES not in PurePath(f.path).parts
            ),
            key=lambda f: (len(PurePath(f.path).parts), f.path),
        )
        return candidates[0] if candidates else None

    def __read_json(self, source_file: SourceFile) -> dict:
        """Read a JSON configuration, or nothing when it cannot be read."""
        try:
            content = json.loads(source_file.file or "")
        except json.JSONDecodeError:
            logger.warning("Skipping %s, it is no valid JSON.", source_file.path)
            return {}
        return content if isinstance(content, dict) else {}

    def __read_port(self, configuration: dict) -> str | None:
        """Read the port a Node service listens on, or ``None``."""
        for section in CONFIG_PORT_SECTIONS:
            values = configuration.get(section)
            if not isinstance(values, dict):
                continue
            port = values.get(CONFIG_PORT_KEY)
            if isinstance(port, int | str) and str(port):
                return str(port)
        return None

    def __read_properties(self, configuration: str) -> dict[str, str]:
        """Read the configured properties, by their name in a technology model."""
        values: dict[str, str] = {}
        for line in configuration.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "!")) or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            name = CONFIGURATION_PROPERTIES.get(key.strip())
            if name is not None:
                values[name] = value.strip()
        return values

    def __base_image(self, dockerfile: str) -> str | None:
        for line in dockerfile.splitlines():
            stripped = line.strip()
            if not stripped.upper().startswith(DOCKERFILE_FROM + " "):
                continue
            # "FROM <image> [AS <stage>]" - a multi stage build names several,
            # the first one is the environment the build starts from.
            parts = stripped.split()
            if len(parts) >= 2:
                return parts[1]
        return None

    def __lies_below(self, path: str, directory: str) -> bool:
        return PurePath(path).is_relative_to(PurePath(directory))
