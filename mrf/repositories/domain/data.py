"""
Module for transforming the reconstructed architecture information from an
intermediate data format, suited for the reconstruction process with additional,
information, e.g., file paths, into a suitable format for persistence.
"""

from dataclasses import dataclass, field
from enum import Enum

from mrf.plugins.common.common_plugin import Data
from mrf.modules.domain_data import (
    Context,
    DataStructure,
    Field,
    PrimitiveType,
    ComplexType,
    ClassType,
)
from mrf.repositories.common import RData, to_rdata


class RClassType(Enum):
    """
    Class types of reconstructed elements.
    """

    COLLECTION = "COLLECTION"
    ENUM = "ENUM"
    DATA_STRUCTURE = "DATA_STRUCTURE"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass
class RPrimitiveType:
    """
    Name of the reconstructed primitive type, e.g., int
    """

    name: str


@dataclass
class RComplexType:
    """
    Name in information of the reconstructed complex type.

    Attributes:
        name (str): simple name of the complex type, e.g., User
        qualified_name (str): qualified name of the complex type, e.g,
            de.fhdo.User
        class_type (str): class type of the type, e.g., collection or structure
    """

    name: str
    qualified_name: str
    class_type: str


@dataclass
class RField:
    """
    Field of a data structure. Note that the field should only have a complex
    or primitive field type.

    Attributes:
        name (str): Name of the complex field type
        primitive_field_type (RPrimitiveType): Primitive type name of the field
        complex_field_type (RComplexType): Complex type name of the field
        data ([RData]): Meta-data information of the field
    """

    name: str
    primitive_field_type: RPrimitiveType | None
    complex_field_type: RComplexType | None
    data: list[RData] = field(init=False)

    def __post_init__(self):
        self.data = []


@dataclass
class RDataStructure:
    """
    Class for reconstructed data structures.

    Attributes:
        name (str): Name of the data structure, e.g., User
        qualified_name (str): Qualified name, e.g., de.fhdo.User
        data ([RData]): Meta-data about the data structure
        fields: ([RField]): Attributes of the data structure
    """

    name: str
    qualified_name: str
    data: list[RData] = field(init=False)
    fields: list[RField] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.fields = []


@dataclass
class REnumeration:
    """
    Class for a reconstructed enumeration with a specific name

    Attributes:
        name (str): Name of the enumeration
    """

    name: str


@dataclass
class RContext:
    """
    Class for information about the reconstructed bounded contexts.

    Attributes:
        name (str): Name of the bounded context, e.g., CustomerCore
        qualified_name (str): Qualified name, e.g., de.fhdo.CustomerCore
        data_structures ([RDataStructure]): Data structures in the context
        enums ([REnumeration]]): Enumerations identified in the context
        data (data): Meta-data for the bounded context
    """

    name: str
    qualified_name: str
    data_structures: list[RDataStructure] = field(init=False)
    enums: list[REnumeration] = field(init=False)
    data: list[RData] = field(init=False)

    def __post_init__(self):
        self.data_structures = []
        self.enums = []
        self.data = []


def transform_context_for_database(context: Context) -> RContext:
    """
    Transform a :class: `Context` into a :class: `RContext`.
    Args:
        context (Context): Context reconstructed from architecture information

    Returns:
        r_context (RContext): Representation of a reconstructed context for
            persistence purpose
    """
    r_context = __to_rcontext(context)
    return r_context


def __to_rcontext(context: Context):
    r_context = RContext(context.name, context.qualified_name)

    for d in context.data_structures:
        r_context.data_structures.append(__to_rdata_structure(d))
    return r_context


def __to_rdata_structure(data_structure: DataStructure):
    r_data_structure = RDataStructure(
        data_structure.name, data_structure.qualified_name
    )

    for d in data_structure.data:
        r_data_structure.data.append(to_rdata(d))

    for f in data_structure.fields:
        r_data_structure.fields.append(__to_rfield(f))

    return r_data_structure


def __to_rfield(field_: Field):
    primitive_field_type = None
    complex_field_type = None
    # Check for field types (primitive of complex)
    if isinstance(field_.field_type, PrimitiveType):
        primitive_field_type = __to_rprimitive_type(field_.field_type)
    elif isinstance(field_.field_type, ComplexType):
        complex_field_type = __to_rcomplex_type(field_.field_type)

    r_field = RField(field_.name, primitive_field_type, complex_field_type)

    # Handle field data information
    for d in field_.data:
        rdata = to_rdata(d)
        r_field.data.append(rdata)
    return r_field


def __to_rprimitive_type(primitive_field_type: PrimitiveType):
    r_primitive_type = RPrimitiveType(primitive_field_type.name)
    return r_primitive_type


def __to_rcomplex_type(complex_field_type: ComplexType):
    class_type = __to_rclass_type(complex_field_type.class_type)
    r_complex_type = RComplexType(
        complex_field_type.name, complex_field_type.qualified_name, class_type
    )
    return r_complex_type


def __to_rclass_type(class_type: ClassType):
    r_class_type = class_type.value
    return r_class_type
