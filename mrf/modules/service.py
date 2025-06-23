"""
Module with classes to reconstruct information about the software system's
microservices, API, and dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum

from mrf.modules.domain_data import ComplexType, PrimitiveType

from mrf.plugins.common.common_plugin import Data

MICROSERVICE_PUBLIC = "public"
MICROSERVICE_FUNCTIONAL = "functional"


class ExchangePattern(Enum):
    IN = "In"
    OUT = "Out"
    INOUT = "Inout"


class CommunicationType(Enum):
    SYNCHRONOUS = "Synchronous"
    ASYNCHRONOUS = "Asynchronous"


@dataclass
class Parameter:
    name: str
    communication_type: CommunicationType
    exchange_pattern: ExchangePattern
    type: PrimitiveType | ComplexType
    data: list[Data] = field(init=False)

    def __post_init__(self):
        self.data = []


@dataclass
class Operation:
    name: str
    data: list[Data] = field(init = False)
    parameters: list[Parameter] = field(init = False)

    def __post_init__(self):
        self.data = []
        self.parameters = []


@dataclass
class Interface:
    """
    Class for storing architecture information about interfaces of
    microservices, e.g., API endpoints and service dependencies.
    """

    qualified_name: str
    name: str
    data: list[Data] = field(init=False)
    operations: list[Operation] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.operations = []


@dataclass
class Microservice:
    """
    Class for storeing architecture information about the software systems
    microservices, e.g., API, dependencies and technologies.
    """

    qualified_name: str
    name: str
    origin_file: str
    data: list[Data] = field(init=False)
    interfaces: list[Interface] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.interfaces = []
