from abc import ABC, abstractmethod
from enum import Enum


class PluginType(Enum):
    Java = "Java"
    Docker = "Docker"


class Plugin(ABC):
    @abstractmethod
    def file_types(self):
        pass

    @abstractmethod
    def execute_reconstruction(self, source_file):
        pass
