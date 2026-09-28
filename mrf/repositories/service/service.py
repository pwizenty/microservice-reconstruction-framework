"""Persistence format for reconstructed microservices.

Transforms the reconstructed architecture information from the intermediate
service format, which carries additional information needed during the
reconstruction process such as file paths, into a format suited for
persistence.
"""

from dataclasses import dataclass, field
from enum import Enum

from mrf.modules.domain_data import ComplexType
from mrf.modules.service import Interface, Microservice, Operation, Parameter
from mrf.repositories.common import RData, to_rdata
from mrf.repositories.domain.data import RComplexType, RPrimitiveType


class RExchangePattern(Enum):
    """Persistence representation of :class:`ExchangePattern`."""

    IN = "In"
    OUT = "Out"
    INOUT = "Inout"


class RCommunicationType(Enum):
    """Persistence representation of :class:`CommunicationType`."""

    SYNCHRONOUS = "Synchronous"
    ASYNCHRONOUS = "Asynchronous"


@dataclass
class RParameter:
    """Persistence representation of a :class:`Parameter`.

    Attributes:
        name (str): Name of the parameter
        communication_type (str): Synchronous or asynchronous
        exchange_pattern (str): Direction of the exchange
        primitive_parameter_type (RPrimitiveType | None): Type if primitive
        complex_parameter_type (RComplexType | None): Type if complex
        data ([RData]): Meta-data of the parameter
    """

    name: str
    communication_type: str
    exchange_pattern: str
    primitive_parameter_type: RPrimitiveType | None
    complex_parameter_type: RComplexType | None
    data: list[RData] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []


@dataclass
class ROperation:
    """Persistence representation of an :class:`Operation`.

    Attributes:
        name (str): Name of the operation
        data ([RData]): Meta-data of the operation
        parameters ([RParameter]): Parameters exchanged by the operation
    """

    name: str
    data: list[RData] = field(init=False)
    parameters: list[RParameter] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []
        self.parameters = []


@dataclass
class RInterface:
    """Persistence representation of an :class:`Interface`.

    Attributes:
        qualified_name (str): Fully qualified name of the interface
        name (str): Name of the interface
        data ([RData]): Meta-data of the interface
        operations ([ROperation]): Operations offered by the interface
    """

    qualified_name: str
    name: str
    data: list[RData] = field(init=False)
    operations: list[ROperation] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []
        self.operations = []


@dataclass
class RMicroservice:
    """Persistence representation of a :class:`Microservice`.

    Attributes:
        qualified_name (str): Fully qualified name of the microservice
        name (str): Name of the microservice
        data ([RData]): Meta-data of the microservice
        interfaces ([RInterface]): Interfaces offered by the microservice
    """

    qualified_name: str
    name: str
    data: list[RData] = field(init=False)
    interfaces: list[RInterface] = field(init=False)

    def __post_init__(self) -> None:
        self.data = []
        self.interfaces = []


def transform_microservice_for_database(microservice: Microservice) -> RMicroservice:
    """Transform a :class:`Microservice` into a :class:`RMicroservice`.

    Args:
        microservice (Microservice): Reconstructed microservice information

    Returns:
        RMicroservice: Representation of the microservice for persistence
    """
    r_microservice = RMicroservice(microservice.qualified_name, microservice.name)

    for interface in microservice.interfaces:
        r_microservice.interfaces.append(__to_rinterface(interface))

    for data in microservice.data:
        r_microservice.data.append(to_rdata(data))

    return r_microservice


def __to_rinterface(interface: Interface) -> RInterface:
    r_interface = RInterface(interface.qualified_name, interface.name)

    for operation in interface.operations:
        r_interface.operations.append(__to_roperation(operation))

    for data in interface.data:
        r_interface.data.append(to_rdata(data))

    return r_interface


def __to_roperation(operation: Operation) -> ROperation:
    r_operation = ROperation(operation.name)

    for data in operation.data:
        r_operation.data.append(to_rdata(data))

    for parameter in operation.parameters:
        r_operation.parameters.append(__to_rparameter(parameter))
    return r_operation


def __to_rparameter(parameter: Parameter) -> RParameter:
    r_communication_type = RCommunicationType[
        parameter.communication_type.value.upper()
    ].value
    r_exchange_pattern = RExchangePattern[
        parameter.exchange_pattern.value.upper()
    ].value
    r_complex_type = None
    r_primitive_type = None

    if isinstance(parameter.type, ComplexType):
        rcomplex_type = RComplexType(
            parameter.type.name,
            parameter.type.qualified_name,
            parameter.type.class_type.value,
        )
        r_complex_type = rcomplex_type

    else:
        r_primitive_type = RPrimitiveType(parameter.type.name)

    r_parameter = RParameter(
        parameter.name,
        r_communication_type,
        r_exchange_pattern,
        r_primitive_type,
        r_complex_type,
    )
    for data in parameter.data:
        r_parameter.data.append(to_rdata(data))
    return r_parameter
