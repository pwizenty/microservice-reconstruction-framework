"""Constants and naming rules for reconstructing from Protocol Buffers.

The parser lives in :mod:`mrf.utilities.proto_utils`; what the reconstruction
calls the things it finds is decided here.
"""

import logging
from pathlib import PurePath

logger = logging.getLogger(__name__)

# Meta-data names and keys
PROTO_FIELD = "ProtoField"
"""Meta-data name under which a field keeps what the proto file said about it.

The mapping of a proto scalar onto a primitive loses detail - an int32 and a
sint32 are both an int - so the proto type is kept beside it.
"""

PROTO_RPC = "ProtoRpc"
"""Meta-data name of an operation reconstructed from an rpc."""

PROTO_TYPE = "protoType"
REPEATED = "repeated"
ONEOF = "oneof"
STREAM = "stream"

NESTING_SEPARATOR = "_"
"""Separator between the parts of a nested message's name.

Not a dot, for two reasons: a structure's name is a single identifier in LEMMA,
and the LEMMA side reads the context of a structure as the second to last part
of its qualified name - so a dot inside the name would be read as the context
and the structure would be generated into one that does not exist.
"""

COLLECTION_SUFFIX = "List"
"""Suffix of the collection a repeated field refers to.

The same suffix the Spring plugin uses for a collection of a complex type, so a
consumer sees one convention rather than two.
"""

PROTO_SERVICE = "ProtoService"
"""Meta-data name of the address a gRPC service answers under.

Deliberately **not** the shared ``Endpoint`` name. A reconstructed endpoint is
generated under the one protocol the service generator knows, which is ``rest``,
and the technology model declares no ``grpc`` protocol - so reporting the address
as an endpoint makes the generated model state that a gRPC service is reached
over REST. The address is reported under a name of its own until the LEMMA side
can express the protocol; see docs/node-plugin-plan.md.
"""

PROTO_ADDRESS = "address"
"""Key under which a :data:`PROTO_SERVICE` holds its address."""


def context_name_of(service_name: str) -> str:
    """Return the name of the bounded context a proto service describes.

    The service is the context: its messages are the data of its own domain, and
    LEMMA names the data model after the context.

    Args:
        service_name (str): Name of the ``service`` the file declares

    Returns:
        str: Name of the context
    """
    return service_name


def qualified_context_name(package: str | None, service_name: str, path: str) -> str:
    """Build the qualified name of a context, or of the microservice beside it.

    The qualified name has to end with the name of the context, because the
    LEMMA side reads the context of a data structure as the second to last part
    of the structure's qualified name. A structure is therefore qualified as
    ``<package>.<Service>.<Message>``, and the context as ``<package>.<Service>``.

    A file without a ``package`` is qualified with its own file name instead, so
    the result still has the two parts a LEMMA model needs; a microservice whose
    name has no dot is extracted with a placeholder in front of it.

    Args:
        package (str | None): Package the file declares, if any
        service_name (str): Name of the service the file declares
        path (str): Path of the file, used when it declares no package

    Returns:
        str: Qualified name of the context and of its microservice
    """
    if package:
        return f"{package}.{service_name}"

    stem = PurePath(path).stem
    logger.warning(
        "%s declares no package, so %s is qualified with the file's name "
        "instead. Declare a package to control the name.",
        path,
        service_name,
    )
    return f"{stem}.{service_name}"


def structure_name_of(message_name: str) -> str:
    """Return the name a message is reconstructed under.

    A nested message carries its parents in the name the parser gives it, joined
    by dots. A dot cannot survive into the model (see
    :data:`NESTING_SEPARATOR`), so the parts are joined differently and the
    nesting stays visible.

    Args:
        message_name (str): Name the parser produced, parents included

    Returns:
        str: Name of the structure
    """
    return message_name.replace(".", NESTING_SEPARATOR)


def referable_types(message_names: list[str], enum_names: list[str]) -> dict[str, str]:
    """Map every name a type can be referred to by onto its structure's name.

    proto3 refers to a nested type by its simple name from inside its parent and
    by the qualified one from outside, and the reconstruction declares it under
    neither (see :func:`structure_name_of`). Both are therefore mapped.

    A simple name that two nested types share is left out rather than resolved
    to one of them: a reference to it is ambiguous, and reporting the wrong
    structure would be worse than reporting none.

    Args:
        message_names ([str]): Names of the messages, parents included
        enum_names ([str]): Names of the enumerations

    Returns:
        dict[str, str]: Every referable name, mapped onto a structure's name
    """
    names = list(message_names) + list(enum_names)
    referable: dict[str, str] = {}
    ambiguous: set[str] = set()

    for name in names:
        structure = structure_name_of(name)
        referable[name] = structure

        simple = name.rsplit(".", 1)[-1]
        if simple == name:
            continue
        if simple in referable and referable[simple] != structure:
            ambiguous.add(simple)
        else:
            referable[simple] = structure

    for name in ambiguous:
        logger.warning(
            "More than one nested type is named %s, so a reference to it by "
            "that name alone is left unresolved.",
            name,
        )
        referable.pop(name, None)

    return referable
