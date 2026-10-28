"""Operation information of the reconstructed software system.

Describes how the reconstructed microservices are deployed. See ADR-0008: a
node is either a container, which deploys microservices, or an infrastructure
node, which the system runs on rather than in.

The deployment technology a node uses is deliberately absent. It is a reference
into a LEMMA technology model and is chosen there, not reconstructed from the
sources.
"""

from dataclasses import dataclass, field
from enum import Enum

from mrf.plugins.common.common_plugin import Data


class NodeType(Enum):
    """Kind of an :class:`OperationNode`."""

    CONTAINER = "CONTAINER"
    INFRASTRUCTURE = "INFRASTRUCTURE"


@dataclass
class DeployedService:
    """Reference to a microservice an :class:`OperationNode` deploys.

    Holds the names rather than the :class:`Microservice` itself: the operation
    phase reconstructs from deployment artifacts, which name a service without
    describing it.

    Attributes:
        name (str): Name of the microservice, e.g. CustomerCore
        qualified_name (str): Qualified name of the microservice
    """

    name: str
    qualified_name: str


@dataclass
class OperationNode:
    """Node of the software system's operation, e.g. a Docker container.

    Attributes:
        qualified_name (str): Qualified name of the node
        name (str): Name of the node, e.g. CustomerCoreContainer
        node_type (NodeType): Container or infrastructure node
        origin_file (str | None): File the node was reconstructed from
        operation_environment (str | None): Base image the node runs on, or
            ``None`` when no such information was found
        deployed_services ([:class:`DeployedService`]): Microservices the node
            deploys. Empty for an infrastructure node
        depends_on ([str]): Names of the nodes this node depends on
        data ([:class:`Data`]): Meta-data assigned to the node
    """

    qualified_name: str
    name: str
    node_type: NodeType
    origin_file: str | None = None
    operation_environment: str | None = None
    deployed_services: list[DeployedService] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    data: list[Data] = field(default_factory=list)
