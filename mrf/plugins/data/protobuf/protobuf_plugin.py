"""Protobuf plugin reconstructing the domain data of a gRPC service.

Analyses the ``message`` and ``enum`` declarations of a ``.proto`` file. A proto
file is the contract of a gRPC service: it names the service, its operations and
the structures they exchange, so the structures become the bounded context of
that service and the operations are reconstructed by the plugin of the service
phase.

See the plan in ``docs/node-plugin-plan.md`` for why a proto file is read and
what is deliberately left to a later step.
"""

import logging
from pathlib import PurePath

from mrf.modules.domain_data import (
    ClassType,
    Collection,
    ComplexType,
    Context,
    DataStructure,
    Enumeration,
    Field,
    PrimitiveType,
)
from mrf.plugins.common.common_plugin import Data
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.proto_utils import (
    PROTO_SUFFIX,
    ProtoFile,
    ProtoMessage,
    ProtoParseError,
    parse_proto_file,
    primitive_of,
)
from mrf.utilities.protobuf import (
    COLLECTION_SUFFIX,
    ONEOF,
    PROTO_FIELD,
    PROTO_TYPE,
    REPEATED,
    context_name_of,
    qualified_context_name,
    referable_types,
    structure_name_of,
)

logger = logging.getLogger(__name__)


class ProtobufDataPlugin(Plugin):
    """Reconstructs the bounded context a proto file describes."""

    def __init__(self) -> None:
        self.contexts: list[Context] = []

    def file_types(self) -> list[str]:
        """Return the file suffixes this plugin analyses.

        Returns:
            [str]: The suffix of a Protocol Buffers file
        """
        return [PROTO_SUFFIX]

    def execute_reconstruction(self, source_files: list[SourceFile]) -> list[Context]:
        """Reconstruct the domain data the analysed system's proto files declare.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            [Context]: Reconstructed bounded contexts, one per service a proto
            file declares
        """
        for source_file in self.__proto_files(source_files):
            proto = self.__parse(source_file)
            if proto is None:
                continue
            self.contexts.extend(self.__reconstruct_contexts(proto, source_file))
        return self.contexts

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

    def __reconstruct_contexts(
        self, proto: ProtoFile, source_file: SourceFile
    ) -> list[Context]:
        """Reconstruct one context per service the file declares.

        The structures of a file belong to the service it declares, so a file
        with no service declares no context of its own: its messages are types
        of another file's service, reached through the proto package, and a
        context with no service would have no microservice to belong to.
        """
        if not proto.services:
            logger.debug(
                "%s declares no service, so its messages belong to no context.",
                source_file.path,
            )
            return []

        contexts: list[Context] = []
        for service in proto.services:
            name = context_name_of(service.name)
            qualified_name = qualified_context_name(
                proto.package, service.name, source_file.path
            )
            context = Context(qualified_name, name, source_file.path)

            # Every name a field may refer to, mapped onto the structure it is
            # reconstructed as. A type that is not in it comes from an imported
            # file, which this reconstruction has no structure for.
            declared = referable_types(
                [m.name for m in proto.messages], [e.name for e in proto.enums]
            )
            # An enumeration is declared as one, so a field that refers to it
            # has to say so: the LEMMA generator branches on the kind and would
            # otherwise reference a structure that was never declared.
            enumerations = {
                structure_name_of(enumeration.name) for enumeration in proto.enums
            }
            for message in proto.messages:
                context.data_structures.append(
                    self.__reconstruct_structure(
                        message, qualified_name, source_file, declared, enumerations
                    )
                )
                context.collections.extend(
                    self.__reconstruct_collections(
                        message, qualified_name, declared, enumerations
                    )
                )
            for enumeration in proto.enums:
                context.enums.append(Enumeration(enumeration.name))

            contexts.append(context)
        return contexts

    def __reconstruct_structure(
        self,
        message: ProtoMessage,
        context_qualified_name: str,
        source_file: SourceFile,
        declared: dict[str, str],
        enumerations: set[str],
    ) -> DataStructure:
        """Reconstruct a message as a data structure of its context."""
        name = structure_name_of(message.name)
        structure = DataStructure(
            f"{context_qualified_name}.{name}", name, source_file.path
        )
        for proto_field in message.fields:
            structure.fields.append(
                self.__reconstruct_field(
                    proto_field, context_qualified_name, declared, enumerations
                )
            )
        return structure

    def __reconstruct_field(
        self,
        proto_field,
        context_qualified_name: str,
        declared: dict[str, str],
        enumerations: set[str],
    ) -> Field:
        """Reconstruct a field, with what the proto file says about it.

        A repeated field refers to a collection of its type, so the collection
        is reconstructed beside the structure and the field refers to it. The
        proto type is kept as meta-data in every case, because the mapping onto
        a primitive loses the distinction between, say, an int32 and a sint32.
        """
        if proto_field.repeated:
            element = self.__type_of(
                proto_field.type_name, context_qualified_name, declared, enumerations
            )
            name = f"{element.name[:1].upper()}{element.name[1:]}{COLLECTION_SUFFIX}"
            field_type: PrimitiveType | ComplexType = ComplexType(
                name,
                f"{context_qualified_name}.{name}",
                ClassType.COLLECTION,
            )
        else:
            field_type = self.__type_of(
                proto_field.type_name, context_qualified_name, declared, enumerations
            )

        field = Field(proto_field.name, field_type)
        data = Data(PROTO_FIELD)
        values = {PROTO_TYPE: proto_field.type_name}
        if proto_field.repeated:
            values[REPEATED] = str(proto_field.repeated).lower()
        if proto_field.oneof is not None:
            # A field of a oneof is optional by construction, and which group it
            # belongs to is what says why.
            values[ONEOF] = proto_field.oneof
        data.values = values
        field.data.append(data)
        return field

    def __reconstruct_collections(
        self,
        message: ProtoMessage,
        context_qualified_name: str,
        declared: dict[str, str],
        enumerations: set[str],
    ) -> list[Collection]:
        """Reconstruct a collection for every repeated field of a message."""
        collections: list[Collection] = []
        for proto_field in message.fields:
            if not proto_field.repeated:
                continue
            element = self.__type_of(
                proto_field.type_name, context_qualified_name, declared, enumerations
            )
            name = f"{element.name[:1].upper()}{element.name[1:]}{COLLECTION_SUFFIX}"
            if any(c.name == name for c in collections):
                continue
            collections.append(
                Collection(f"{context_qualified_name}.{name}", name, element)
            )
        return collections

    def __type_of(
        self,
        type_name: str,
        context_qualified_name: str,
        declared: dict[str, str],
        enumerations: set[str],
    ) -> PrimitiveType | ComplexType:
        """Map a proto type onto a primitive or a reference to a structure."""
        primitive = primitive_of(type_name)
        if primitive is not None:
            return PrimitiveType(primitive)

        structure = declared.get(type_name)
        if structure is None:
            return ComplexType(type_name, type_name, ClassType.UNSPECIFIED)
        kind = ClassType.ENUM if structure in enumerations else ClassType.DATA_STRUCTURE
        return ComplexType(structure, f"{context_qualified_name}.{structure}", kind)
