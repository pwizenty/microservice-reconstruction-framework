"""
Module for transforming the reconstructed architecture information from an
intermediate service format, suited for the reconstruction process with additional,
information, e.g., file paths, into a suitable format for persistence.
"""

from dataclasses import dataclass, field
from enum import Enum

from mrf.modules.domain_data import ComplexType
from mrf.modules.service import Microservice, Interface, Operation, Parameter
from mrf.repositories.common import RData, to_rdata
from mrf.repositories.domain.data import RPrimitiveType, RComplexType


class RExchangePattern(Enum):
    IN = "In"
    OUT = "Out"
    INOUT = "Inout"


class RCommunicationType(Enum):
    SYNCHRONOUS = "Synchronous"
    ASYNCHRONOUS = "Asynchronous"


@dataclass
class RParameter:
    name: str
    communication_type: RCommunicationType
    exchange_pattern: RExchangePattern
    primitive_parameter_type: RPrimitiveType | None
    complex_parameter_type: RComplexType | None
    data: list[RData] = field(init=False)

    def __post_init__(self):
        self.data = []


@dataclass
class ROperation:
    name: str
    data: list[RData] = field(init=False)
    parameters: list[RParameter] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.parameters = []


@dataclass
class RInterface:
    qualified_name: str
    name: str
    data: list[RData] = field(init=False)
    operations: list[ROperation] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.operations = []


@dataclass
class RMicroservice:
    qualified_name: str
    name: str
    data: list[RData] = field(init=False)
    interfaces: list[RInterface] = field(init=False)

    def __post_init__(self):
        self.data = []
        self.interfaces = []


def transform_microservice_for_database(microservice: Microservice) -> RMicroservice:
    """
    Transform a :class: `Context` into a :class: `RContext`.
    Args:
        microservice (Microservice): Context reconstructed from architecture information

    Returns:
        r_microservice (RMicroservice): Representation of a reconstructed microservice for
            persistence purpose
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
        r_primitive_type = parameter.type

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
