"""Persistence format for the reconstructed operation of a software system.

Transforms the reconstructed operation nodes from the intermediate format,
which carries information needed during the reconstruction such as the file a
node was found in, into the format persisted in the ``operation`` collection.
See ADR-0008 for the document shape.
"""

from dataclasses import dataclass, field

from mrf.modules.operation import DeployedService, OperationNode
from mrf.repositories.common import RData, to_rdata


@dataclass
class RDeployedService:
    """Persistence representation of a :class:`DeployedService`.

    Attributes:
        name (str): Name of the microservice
        qualified_name (str): Qualified name of the microservice
    """

    name: str
    qualified_name: str


@dataclass
class ROperationNode:
    """Persistence representation of an :class:`OperationNode`.

    Attributes:
        qualified_name (str): Qualified name of the node
        name (str): Name of the node
        node_type (str): ``CONTAINER`` or ``INFRASTRUCTURE``
        operation_environment (str | None): Base image the node runs on
        deployed_services ([RDeployedService]): Microservices the node deploys
        depends_on ([str]): Names of the nodes this node depends on
        data ([RData]): Meta-data of the node
    """

    qualified_name: str
    name: str
    node_type: str
    operation_environment: str | None
    deployed_services: list[RDeployedService] = field(init=False)
    depends_on: list[str] = field(init=False)
    data: list[RData] = field(init=False)

    def __post_init__(self) -> None:
        self.deployed_services = []
        self.depends_on = []
        self.data = []


def transform_operation_node_for_database(node: OperationNode) -> ROperationNode:
    """Transform an :class:`OperationNode` into an :class:`ROperationNode`.

    Args:
        node (OperationNode): Reconstructed operation information

    Returns:
        ROperationNode: Representation of the node for persistence
    """
    r_node = ROperationNode(
        node.qualified_name,
        node.name,
        node.node_type.value,
        node.operation_environment,
    )

    for service in node.deployed_services:
        r_node.deployed_services.append(__to_rdeployed_service(service))

    r_node.depends_on.extend(node.depends_on)

    for data in node.data:
        r_node.data.append(to_rdata(data))

    return r_node


def __to_rdeployed_service(service: DeployedService) -> RDeployedService:
    return RDeployedService(service.name, service.qualified_name)
