from enum import Enum

from dataclasses import dataclass, field

from mrf.plugins.common.common_plugin import Data
from mrf.plugins.data.domain_data import Context, DataStructure, Field, PrimitiveType, ComplexType, ClassType


@dataclass
class RData:
    name: str
    values = dict()

@dataclass
class RClassType(Enum):
    COLLECTION = "COLLECTION"
    ENUM = "ENUM"
    DATA_STRUCTURE = "DATA_STRUCTURE"
    UNSPECIFIED = "UNSPECIFIED"

@dataclass
class RPrimitiveType:
    name: str

@dataclass
class RComplexType:
    name: str
    qualified_name: str
    class_type: str

@dataclass
class RField:
    name: str
    primitive_field_type: RPrimitiveType
    complex_field_type: RComplexType
    data: list[RData] = field(init=False)

    def __post_init__(self):
        self.data = []

@dataclass
class RDataStructure:
    name: str
    qualified_name: str
    data: list[RData] = field(init=False)
    fields: list[RField] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.fields = []

@dataclass
class REnumeration:
    name: str

@dataclass
class RContext:
    name: str
    qualified_name: str
    data_structures: list[RDataStructure] = field(init=False)
    enums: list[REnumeration] = field(init=False)
    data: list[RData] = field(init=False)

    def __post_init__(self):
        self.data_structures = []
        self.enums = []
        self.data = []

def transform_context_for_database(context: Context):
    r_context = __to_rcontext(context)
    return r_context

def __to_rcontext(context: Context):
    r_context = RContext(context.name, context.qualified_name)

    for d in context.data_structures:
        r_context.data_structures.append(__to_rdata_structure(d))
    return r_context

def __to_rdata_structure(data_structure: DataStructure):
    r_data_structure = RDataStructure(data_structure.name, data_structure.qualified_name)

    for d in data_structure.data:
        r_data_structure.data.append(__to_rdata(d))

    for f in data_structure.fields:
        r_data_structure.fields.append(__to_rfield(f))

    return r_data_structure

def __to_rdata(data: Data):
    r_data = RData(data.name)
    r_data.values = data.values
    return r_data

def __to_rfield(field_: Field):
    primitive_field_type = RPrimitiveType
    complex_field_type = RComplexType
    if isinstance(field_.field_type, PrimitiveType):
        primitive_field_type = __to_rprimitive_type(field_.field_type)
        complex_field_type = None
    elif isinstance(field_.field_type, ComplexType):
        complex_field_type = __to_rcomplex_type(field_.field_type)
        primitive_field_type = None
    r_field = RField(field_.name, primitive_field_type, complex_field_type)
    #TODO: Add Handling of all Data
    

    return r_field

def __to_rprimitive_type(primitive_field_type: PrimitiveType):
    r_primitive_type = RPrimitiveType(primitive_field_type.name)
    return r_primitive_type

def __to_rcomplex_type(complex_field_type: ComplexType):
    class_type = __to_rclass_type(complex_field_type.class_type)
    r_complex_type = RComplexType(complex_field_type.name, complex_field_type.qualified_name, class_type)

    return r_complex_type

def __to_rclass_type(class_type: ClassType):
    r_class_type = class_type.value
    return r_class_type