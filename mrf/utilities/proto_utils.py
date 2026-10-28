"""Utility module for handling Protocol Buffers source files.

Parses the subset of proto3 that describes an interface and the data it carries:
``package``, ``service`` with its ``rpc`` declarations, ``message`` with its
fields, and ``enum``. The rest of the language - options, extensions, reserved
ranges, services' options, custom types of imported files - is read and skipped,
so a file that uses it parses rather than failing.

A hand-written parser rather than a dependency: proto3's grammar for these
declarations is small, closed and stable, and the alternatives are ``protobuf``,
which parses no ``.proto`` source at all, and ``grpcio-tools``, which ships the
whole of ``protoc``. See the plan in ``docs/node-plugin-plan.md``.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PROTO_SUFFIX = ".proto"

SCALAR_TYPES = {
    "double": "double",
    "float": "float",
    "int32": "int",
    "int64": "long",
    "uint32": "int",
    "uint64": "long",
    "sint32": "int",
    "sint64": "long",
    "fixed32": "int",
    "fixed64": "long",
    "sfixed32": "int",
    "sfixed64": "long",
    "bool": "boolean",
    "string": "string",
    "bytes": "byte",
}
"""Scalar types of proto3, mapped onto the primitive types MRF knows.

``bytes`` is a sequence of octets and has no counterpart, so it is reported as
the closest primitive rather than as a collection of them; the field keeps its
proto type in its meta-data either way.
"""

LABEL_REPEATED = "repeated"
LABEL_OPTIONAL = "optional"

# A declaration that carries no architecture information. Read to the end of its
# statement or block and dropped.
SKIPPED_KEYWORDS = frozenset(
    {"syntax", "import", "option", "extend", "reserved", "extensions", "public", "weak"}
)

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
NUMBER = re.compile(r"-?\d+(\.\d+)?")
STRING = re.compile(r'"[^"]*"|\'[^\']*\'')
COMMENT_LINE = re.compile(r"//[^\n]*")
COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
PUNCTUATION = frozenset("{}()[]<>=;,")


class ProtoParseError(Exception):
    """Raised when a file cannot be read as proto3."""


@dataclass
class ProtoField:
    """One field of a message.

    Attributes:
        name: Name of the field
        type_name: Type as the file states it, a scalar or a message name
        repeated: Whether the field holds a sequence
        optional: Whether the field is declared optional, or lies in a ``oneof``
        oneof: Name of the ``oneof`` the field belongs to, or ``None``
    """

    name: str
    type_name: str
    repeated: bool = False
    optional: bool = False
    oneof: str | None = None


@dataclass
class ProtoMessage:
    """A message, which is a structure of fields.

    Attributes:
        name: Name of the message, qualified with its parents when nested
        fields: Fields it declares
        nested: Messages declared inside it
        enums: Enumerations declared inside it
    """

    name: str
    fields: list[ProtoField] = field(default_factory=list)
    nested: list["ProtoMessage"] = field(default_factory=list)
    enums: list["ProtoEnum"] = field(default_factory=list)


@dataclass
class ProtoEnum:
    """An enumeration.

    Attributes:
        name: Name of the enumeration
        values: Names of its values, in declaration order
    """

    name: str
    values: list[str] = field(default_factory=list)


@dataclass
class ProtoRpc:
    """One remote procedure of a service.

    Attributes:
        name: Name of the procedure
        request_type: Type of its parameter
        response_type: Type of its result
        request_stream: Whether the parameter is a stream
        response_stream: Whether the result is a stream
    """

    name: str
    request_type: str
    response_type: str
    request_stream: bool = False
    response_stream: bool = False


@dataclass
class ProtoService:
    """A service, which is an interface of remote procedures.

    Attributes:
        name: Name of the service
        rpcs: Procedures it declares
    """

    name: str
    rpcs: list[ProtoRpc] = field(default_factory=list)


@dataclass
class ProtoFile:
    """What one ``.proto`` file declares.

    Attributes:
        package: Package it declares, or ``None``
        services: Services it declares
        messages: Messages it declares, nested ones flattened into this list
        enums: Enumerations it declares
    """

    package: str | None = None
    services: list[ProtoService] = field(default_factory=list)
    messages: list[ProtoMessage] = field(default_factory=list)
    enums: list[ProtoEnum] = field(default_factory=list)


def parse_proto_file(content: str) -> ProtoFile:
    """Parse the content of a ``.proto`` file.

    Args:
        content (str): Content of the file

    Returns:
        ProtoFile: What the file declares

    Raises:
        ProtoParseError: When the file cannot be read as proto3
    """
    parser = _Parser(_tokenize(content))
    return parser.parse_file()


def is_scalar(type_name: str) -> bool:
    """Check whether a type is one of proto3's scalars."""
    return type_name in SCALAR_TYPES


def primitive_of(type_name: str) -> str | None:
    """Return the primitive MRF knows a proto scalar as, or ``None``."""
    return SCALAR_TYPES.get(type_name)


def _tokenize(content: str) -> list[str]:
    """Split the content into identifiers, literals and punctuation.

    Comments are removed first, so a declaration commented out is not read as
    one.
    """
    text = COMMENT_BLOCK.sub(" ", content)
    text = COMMENT_LINE.sub(" ", text)

    tokens: list[str] = []
    position = 0
    while position < len(text):
        character = text[position]
        if character.isspace():
            position += 1
            continue
        if character in PUNCTUATION:
            tokens.append(character)
            position += 1
            continue
        for pattern in (STRING, IDENTIFIER, NUMBER):
            match = pattern.match(text, position)
            if match is not None:
                tokens.append(match.group(0))
                position = match.end()
                break
        else:
            # A character proto3 does not use. Skipping it keeps a file with an
            # unexpected byte readable instead of ending the reconstruction.
            logger.debug("Skipping the unexpected character %r.", character)
            position += 1
    return tokens


class _Parser:
    """Recursive parser over the tokens of one file."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.position = 0

    def parse_file(self) -> ProtoFile:
        proto = ProtoFile()
        while not self.__at_end():
            token = self.__next()
            if token == "package":
                proto.package = self.__read_until(";").strip()
            elif token == "service":
                proto.services.append(self.__parse_service())
            elif token == "message":
                self.__collect(self.__parse_message(prefix=""), proto)
            elif token == "enum":
                proto.enums.append(self.__parse_enum())
            elif token in SKIPPED_KEYWORDS:
                self.__skip_statement()
            elif token == ";":
                continue
            else:
                # An unknown top level declaration. Skipping its statement or
                # block keeps the rest of the file readable.
                logger.debug("Skipping the unknown declaration %r.", token)
                self.__skip_statement()
        return proto

    def __collect(self, message: ProtoMessage, proto: ProtoFile) -> None:
        """Add a message and everything nested in it to the file.

        Nesting is flattened, because the model MRF reconstructs has no notion
        of a structure inside a structure; a nested message keeps its parents in
        its name so two of the same name stay apart.
        """
        proto.messages.append(message)
        proto.enums.extend(message.enums)
        for nested in message.nested:
            self.__collect(nested, proto)
        message.nested = []
        message.enums = []

    def __parse_service(self) -> ProtoService:
        name = self.__expect_identifier("a service's name")
        service = ProtoService(name)
        self.__expect("{")
        while True:
            token = self.__next_or_fail("the end of service " + name)
            if token == "}":
                return service
            if token == "rpc":
                service.rpcs.append(self.__parse_rpc())
            elif token == ";":
                continue
            else:
                self.__skip_statement()

    def __parse_rpc(self) -> ProtoRpc:
        name = self.__expect_identifier("an rpc's name")
        self.__expect("(")
        request_stream, request_type = self.__parse_rpc_type()
        self.__expect(")")
        self.__expect("returns")
        self.__expect("(")
        response_stream, response_type = self.__parse_rpc_type()
        self.__expect(")")

        # An rpc ends with a semicolon or with a block of options.
        token = self.__next_or_fail("the end of rpc " + name)
        if token == "{":
            self.__skip_block()
        elif token != ";":
            self.position -= 1

        return ProtoRpc(
            name, request_type, response_type, request_stream, response_stream
        )

    def __parse_rpc_type(self) -> tuple[bool, str]:
        token = self.__next_or_fail("a type of an rpc")
        if token == "stream":
            return True, self.__expect_identifier("a type of an rpc")
        return False, token

    def __parse_message(self, prefix: str) -> ProtoMessage:
        simple_name = self.__expect_identifier("a message's name")
        name = f"{prefix}{simple_name}"
        message = ProtoMessage(name)
        self.__expect("{")

        while True:
            token = self.__next_or_fail("the end of message " + name)
            if token == "}":
                return message
            if token == "message":
                message.nested.append(self.__parse_message(prefix=f"{name}."))
            elif token == "enum":
                message.enums.append(self.__parse_enum())
            elif token == "oneof":
                message.fields.extend(self.__parse_oneof())
            elif token in {"reserved", "extensions", "option", "extend"}:
                self.__skip_statement()
            elif token == ";":
                continue
            else:
                parsed = self.__parse_field(token)
                if parsed is not None:
                    message.fields.append(parsed)

    def __parse_oneof(self) -> list[ProtoField]:
        """Parse a ``oneof``, whose fields are optional by construction."""
        name = self.__expect_identifier("a oneof's name")
        self.__expect("{")
        fields: list[ProtoField] = []
        while True:
            token = self.__next_or_fail("the end of oneof " + name)
            if token == "}":
                return fields
            if token == ";":
                continue
            if token == "option":
                self.__skip_statement()
                continue
            parsed = self.__parse_field(token)
            if parsed is not None:
                parsed.optional = True
                parsed.oneof = name
                fields.append(parsed)

    def __parse_field(self, first: str) -> ProtoField | None:
        """Parse one field, whose first token has already been read.

        A field is ``[label] type name = number [options];``. ``map<k, v>`` is
        read as a field of its value type, because the model has no map of its
        own and the value is what a consumer needs.
        """
        repeated = False
        optional = False
        type_name = first

        if first in {LABEL_REPEATED, LABEL_OPTIONAL}:
            repeated = first == LABEL_REPEATED
            optional = first == LABEL_OPTIONAL
            type_name = self.__next_or_fail("a field's type")

        if type_name == "map":
            self.__expect("<")
            self.__next_or_fail("a map's key type")
            self.__expect(",")
            type_name = self.__next_or_fail("a map's value type")
            self.__expect(">")
            repeated = True

        name = self.__next_or_fail("a field's name")
        if name in PUNCTUATION:
            # Not a field after all; read to the end of the statement and drop
            # it rather than reporting a field that does not exist.
            self.__skip_statement()
            return None

        self.__read_until(";")
        return ProtoField(name, type_name, repeated, optional)

    def __parse_enum(self) -> ProtoEnum:
        name = self.__expect_identifier("an enumeration's name")
        enumeration = ProtoEnum(name)
        self.__expect("{")
        while True:
            token = self.__next_or_fail("the end of enum " + name)
            if token == "}":
                return enumeration
            if token in {";", "option", "reserved"}:
                if token != ";":
                    self.__skip_statement()
                continue
            enumeration.values.append(token)
            self.__read_until(";")

    # Reading primitives

    def __at_end(self) -> bool:
        return self.position >= len(self.tokens)

    def __next(self) -> str:
        token = self.tokens[self.position]
        self.position += 1
        return token

    def __next_or_fail(self, expected: str) -> str:
        if self.__at_end():
            raise ProtoParseError(f"The file ends where {expected} was expected.")
        return self.__next()

    def __expect(self, token: str) -> None:
        found = self.__next_or_fail(repr(token))
        if found != token:
            raise ProtoParseError(f"Expected {token!r} but found {found!r}.")

    def __expect_identifier(self, expected: str) -> str:
        token = self.__next_or_fail(expected)
        if IDENTIFIER.fullmatch(token) is None:
            raise ProtoParseError(f"Expected {expected} but found {token!r}.")
        return token

    def __read_until(self, token: str) -> str:
        """Read up to and including a token, and return what came before it."""
        read: list[str] = []
        while not self.__at_end():
            found = self.__next()
            if found == token:
                break
            if found == "{":
                self.__skip_block()
                continue
            read.append(found)
        return " ".join(read)

    def __skip_statement(self) -> None:
        """Skip a declaration, whether it ends in a semicolon or a block."""
        while not self.__at_end():
            token = self.__next()
            if token == ";":
                return
            if token == "{":
                self.__skip_block()
                return

    def __skip_block(self) -> None:
        """Skip a block whose opening brace has already been read."""
        depth = 1
        while not self.__at_end() and depth > 0:
            token = self.__next()
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
