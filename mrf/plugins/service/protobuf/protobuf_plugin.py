"""Protobuf plugin reconstructing the microservice a gRPC contract describes.

Analyses the ``service`` and ``rpc`` declarations of a ``.proto`` file. A proto
file states what a Java controller states through annotations, and in one place:
the service, its operations, and the type of each operation's parameter and
result. The structures those types refer to are reconstructed by the plugin of
the domain phase, into the context of the same service.

An rpc declared with ``stream`` on either side exchanges a sequence rather than
one value, which is asynchronous communication; everything else is synchronous.
"""

import logging
from pathlib import PurePath

from mrf.modules.domain_data import ClassType, ComplexType, PrimitiveType
from mrf.modules.service import (
    MICROSERVICE_FUNCTIONAL,
    MICROSERVICE_PUBLIC,
    CommunicationType,
    ExchangePattern,
    Interface,
    Microservice,
    Operation,
    Parameter,
)
from mrf.plugins.common.common_plugin import Data
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.proto_utils import (
    PROTO_SUFFIX,
    ProtoFile,
    ProtoParseError,
    ProtoRpc,
    parse_proto_file,
    primitive_of,
)
from mrf.utilities.protobuf import (
    PROTO_ADDRESS,
    PROTO_RPC,
    PROTO_SERVICE,
    STREAM,
    qualified_context_name,
    referable_types,
)

logger = logging.getLogger(__name__)


class ProtobufServicePlugin(Plugin):
    """Reconstructs the microservice and interface a proto file describes."""

    def __init__(self) -> None:
        self.microservices: list[Microservice] = []

    def file_types(self) -> list[str]:
        """Return the file suffixes this plugin analyses.

        Returns:
            [str]: The suffix of a Protocol Buffers file
        """
        return [PROTO_SUFFIX]

    def execute_reconstruction(
        self, source_files: list[SourceFile]
    ) -> list[Microservice]:
        """Reconstruct the microservices the analysed system's proto files declare.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            [Microservice]: Reconstructed microservices, one per service a proto
            file declares
        """
        for source_file in self.__proto_files(source_files):
            proto = self.__parse(source_file)
            if proto is None:
                continue
            self.microservices.extend(self.__reconstruct(proto, source_file))
        return self.microservices

    def __proto_files(self, source_files: list[SourceFile]) -> list[SourceFile]:
        """Return the proto files of the system, in a stable order."""
        return sorted(
            (
                f
                for f in source_files
                if f.file is not None
                and PurePath(f.path).suffix == PROTO_SUFFIX
                and "node_modules" not in PurePath(f.path).parts
            ),
            key=lambda f: f.path,
        )

    def __parse(self, source_file: SourceFile) -> ProtoFile | None:
        """Parse a proto file, or skip it with a warning."""
        try:
            return parse_proto_file(source_file.file or "")
        except ProtoParseError as error:
            logger.warning(
                "Skipping %s, it cannot be read as proto3: %s. The "
                "reconstruction is incomplete.",
                source_file.path,
                error,
            )
            return None

    def __reconstruct(
        self, proto: ProtoFile, source_file: SourceFile
    ) -> list[Microservice]:
        """Reconstruct one microservice per service the file declares."""
        declared = referable_types(
            [m.name for m in proto.messages], [e.name for e in proto.enums]
        )

        microservices: list[Microservice] = []
        for service in proto.services:
            qualified_name = qualified_context_name(
                proto.package, service.name, source_file.path
            )
            microservice = Microservice(qualified_name, service.name, source_file.path)
            microservice.data.append(Data(MICROSERVICE_PUBLIC))
            microservice.data.append(Data(MICROSERVICE_FUNCTIONAL))

            interface = Interface(f"{qualified_name}.{service.name}", service.name)
            # A gRPC service is addressed by its fully qualified name rather
            # than by a path. Reported under a name of its own and not as an
            # Endpoint: see PROTO_SERVICE for why that would state something
            # false about the protocol.
            address = Data(PROTO_SERVICE)
            address.values = {PROTO_ADDRESS: qualified_name}
            interface.data.append(address)

            for rpc in service.rpcs:
                interface.operations.append(
                    self.__reconstruct_operation(rpc, qualified_name, declared)
                )

            microservice.interfaces.append(interface)
            microservices.append(microservice)
        return microservices

    def __reconstruct_operation(
        self, rpc: ProtoRpc, qualified_name: str, declared: dict[str, str]
    ) -> Operation:
        """Reconstruct an rpc as an operation with its two parameters."""
        operation = Operation(rpc.name)
        data = Data(PROTO_RPC)
        values = {}
        if rpc.request_stream or rpc.response_stream:
            values[STREAM] = " ".join(
                side
                for side, streaming in (
                    ("request", rpc.request_stream),
                    ("response", rpc.response_stream),
                )
                if streaming
            )
        data.values = values
        operation.data.append(data)

        operation.parameters.append(
            self.__reconstruct_parameter(
                rpc.request_type,
                ExchangePattern.IN,
                rpc.request_stream,
                qualified_name,
                declared,
            )
        )
        operation.parameters.append(
            self.__reconstruct_parameter(
                rpc.response_type,
                ExchangePattern.OUT,
                rpc.response_stream,
                qualified_name,
                declared,
            )
        )
        return operation

    def __reconstruct_parameter(
        self,
        type_name: str,
        exchange_pattern: ExchangePattern,
        streaming: bool,
        qualified_name: str,
        declared: dict[str, str],
    ) -> Parameter:
        """Reconstruct the parameter an rpc exchanges.

        A stream is a sequence of values rather than one, so it is asynchronous
        communication. The parameter is named after its type, as the Spring
        plugin names a result after its type.
        """
        communication_type = (
            CommunicationType.ASYNCHRONOUS
            if streaming
            else CommunicationType.SYNCHRONOUS
        )
        primitive = primitive_of(type_name)
        if primitive is not None:
            return Parameter(
                type_name,
                communication_type,
                exchange_pattern,
                PrimitiveType(primitive),
            )

        structure = declared.get(type_name)
        if structure is None:
            # A type of an imported file, which this reconstruction has no
            # structure for. Reporting it as a structure would claim one.
            return Parameter(
                type_name,
                communication_type,
                exchange_pattern,
                ComplexType(type_name, type_name, ClassType.UNSPECIFIED),
            )

        # An rpc exchanges a message, never an enumeration, so the kind is not
        # in question here as it is for a field.
        return Parameter(
            structure,
            communication_type,
            exchange_pattern,
            ComplexType(
                structure,
                f"{qualified_name}.{structure}",
                ClassType.DATA_STRUCTURE,
            ),
        )
