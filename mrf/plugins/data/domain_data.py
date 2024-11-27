from enum import Enum
from typing import List

from mrf.plugins.common.common_plugin import Data

DDD_ENTITY = "Entity"
DDD_IDENTIFIER = "Identifier"


class DomainData:
    def __init__(self):
        self.context = []
        self.data_structures = []
        self.enums = []

class ClassType(Enum):
    COLLECTION = "COLLECTION"
    ENUM = "ENUM"
    DATA_STRUCTURE = "DATA_STRUCTURE"
    UNSPECIFIED = "UNSPECIFIED"

class Context:
    def __init__(self, qualified_name, name, origin_file):
        self.qualified_name = qualified_name
        self.name = name
        self.origin_file = origin_file
        self.data_structures: List[DataStructure] = []
        self.enums: List[Enumeration] = []
        self.data: List[Data] = []


class DataStructure:
    def __init__(self, qualified_name, name, origin_file):
        self.qualified_name = qualified_name
        self.name = name
        self.origin_file = origin_file
        self.fields: List[Field] = []
        self.data: List[Data] = []


class Field:
    def __init__(self, name, field_type):
        self.name = name
        self.field_type = field_type
        self.data: List[Data] = []


class ComplexType:
    def __init__(self, qualified_name, name, class_type: ClassType):
        self.qualified_name = qualified_name
        self.name = name
        self.class_type = class_type


class PrimitiveType:
    def __init__(self, name):
        self.name = name


class Enumeration:
    def __init__(self, name):
        self.name = name



