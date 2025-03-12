"""
Module with classes to reconstruct information about the software system's
domain including concepts from Domain Driven Design.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from mrf.plugins.common.common_plugin import Data

DDD_ENTITY = "Entity"
DDD_IDENTIFIER = "Identifier"

UNKNOWN_CONTEXT = "UnknownContext"
UNKNOWN_TYPE = "UnknownType"


class ClassType(Enum):
    """
    Enumeration with class types for :class:`ComplexType`.
    """

    COLLECTION = "COLLECTION"
    ENUM = "ENUM"
    DATA_STRUCTURE = "DATA_STRUCTURE"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass
class ComplexType:
    """
    Complex data type of :class:`DataStructure`.
    """

    name: str
    qualified_name: str
    class_type: ClassType


@dataclass
class PrimitiveType:
    """
    Simple / primitive data type of :class:`DataStructure`.
    """

    name: str


@dataclass
class Field:
    """
    Data field of complex
    """

    name: str
    field_type: PrimitiveType | ComplexType
    data: list[Data] = field(init=False)

    def __post_init__(self):
        self.data = []


@dataclass
class DataStructure:
    """
    Data structure for domain concepts, e.g., entities or aggregates.
    """

    qualified_name: str
    name: str
    origin_file: str
    fields: list[Field] = field(init=False)
    data: list[Data] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.fields = []


@dataclass
class Enumeration:
    """
    Enumeration type for domain information.
    """

    name: str


@dataclass
class Context:
    """
    Class for saving architecture information about the software systems domain.
    Related to a Bounded Context from Domain Driven Design.

    Attributes:
         qualified_name (str): Qualified name of the context, e.g. de.fhdo.User
         name (str): Name of the context, e.g., User
         origin_file (str): Path to the file the Context was reconstructed from
         data_structures ([:class:`DataStructure`]): Reconstructed structures
         enums ([:class:`Enumeration`]): Reconstructed information
         data ([:class:`Data`]): Meta-data assigned to the context
    """

    def __init__(self, qualified_name, name, origin_file):
        self.qualified_name = qualified_name
        self.name = name
        self.origin_file = origin_file
        self.data_structures: List[DataStructure] = []
        self.enums: List[Enumeration] = []
        self.data: List[Data] = []
