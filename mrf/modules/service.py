"""Architecture model of a software system's microservices.

Covers the microservices themselves, their interfaces and operations, and the
parameters exchanged over them.
"""

from dataclasses import dataclass, field
from enum import Enum

from mrf.modules.domain_data import ComplexType, PrimitiveType
from mrf.plugins.common.common_plugin import Data

MICROSERVICE_PUBLIC = "public"
MICROSERVICE_FUNCTIONAL = "functional"


class ExchangePattern(Enum):
    """Direction in which a parameter is exchanged by an operation."""

    IN = "In"
    OUT = "Out"
    INOUT = "Inout"


class CommunicationType(Enum):
    """Kind of communication an operation uses."""

    SYNCHRONOUS = "Synchronous"
    ASYNCHRONOUS = "Asynchronous"


@dataclass
class Parameter:
    """Parameter exchanged by an :class:`Operation`.

    Attributes:
        name (str): Name of the parameter
        communication_type (CommunicationType): Synchronous or asynchronous
        exchange_pattern (ExchangePattern): Direction of the exchange
        type (PrimitiveType | ComplexType): Data type of the parameter
        data ([Data]): Meta-data of the parameter
    """

    name: str
    communication_type: CommunicationType
    exchange_pattern: ExchangePattern
    type: PrimitiveType | ComplexType
    data: list[Data] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []


@dataclass
class Operation:
    """Operation offered by an :class:`Interface`.

    Attributes:
        name (str): Name of the operation
        data ([Data]): Meta-data of the operation, e.g., the REST verb
        parameters ([Parameter]): Parameters exchanged by the operation
    """

    name: str
    data: list[Data] = field(init=False)
    parameters: list[Parameter] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []
        self.parameters = []


@dataclass
class Interface:
    """Interface of a microservice.

    Stores architecture information about interfaces of microservices, e.g.,
    API endpoints and service dependencies.

    Attributes:
        qualified_name (str): Fully qualified name of the interface
        name (str): Name of the interface
        data ([Data]): Meta-data of the interface
        operations ([Operation]): Operations offered by the interface
    """

    qualified_name: str
    name: str
    data: list[Data] = field(init=False)
    operations: list[Operation] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []
        self.operations = []


@dataclass
class Microservice:
    """Microservice of the reconstructed software system.

    Stores architecture information about the software system's microservices,
    e.g., API, dependencies and technologies.

    Attributes:
        qualified_name (str): Fully qualified name of the microservice
        name (str): Name of the microservice
        origin_file (str): Path to the source code artifact it was found in
        data ([Data]): Meta-data of the microservice
        interfaces ([Interface]): Interfaces offered by the microservice
    """

    qualified_name: str
    name: str
    origin_file: str
    data: list[Data] = field(init=False)
    interfaces: list[Interface] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []
        self.interfaces = []
