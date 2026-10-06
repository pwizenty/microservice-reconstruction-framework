"""Plugin API of the reconstruction framework.

Provides the abstract base class and the enumeration used to handle and create
concrete reconstruction plugins.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class PluginType(Enum):
    """Enumeration with all existing plugins."""

    JAVA = "Java"
    DOCKER = "Docker"
    SPRING = "Spring"
    COMMUNICATION = "Communication"
    PROTOBUF = "Protobuf"


class Plugin(ABC):
    """Abstract class for the creation of plugins."""

    @abstractmethod
    def file_types(self) -> list[str]:
        """Abstract method for receiving supported file types form a plugin.

        Returns:
            - Array of supported file types of the plugin.
        """

    @abstractmethod
    def execute_reconstruction(self, source_files) -> Any:
        """Execute the reconstruction functionality of the plugin.

        Args:
            source_files (): a single source code artifact.
        """
