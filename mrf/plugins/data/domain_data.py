from enum import Enum
from typing import List

from mrf.plugins.common.common_plugin import Data

DDD_ENTITY = "Entity"

class DomainData:
    def __init__(self):
        self.context = []
        self.data_structures = []
        self.enums = []


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
    def __init__(self, qualified_name, name, complex_type):
        self.qualified_name = qualified_name
        self.name = name
        self.complex_type = complex_type

class PrimitiveType:
    def __init__(self, name):
        self.name = name

class Enumeration:
    def __init__(self, name):
        self.name = name

class ClassType(Enum):
    Collection = "COLLECTION"
    Enum = "ENUM"
    Data_Structure = "DATA_STRUCTURE"
    Unspecified = "UNSPECIFIED"
