"""
Module for handling the reconstruction process including the management of
source code files and reconstruction process.
"""

from mrf.modules.domain_data import Context
from mrf.modules.service import Microservice
from mrf.plugins.data.java.java_plugin import JavaPlugin
from mrf.plugins.reconstruction_plugin import PluginType
from mrf.plugins.service.spring.spring_plugin import SpringPlugin
from mrf.repositories.mongo_repository import save_contexts
from mrf.utilities.command_line import SourceFile
from mrf.repositories.mongo_repository import save_microservices


class ReconstructionHandler:
    """
    Class for handling the reconstruction process.
    """

    _instance = None
    source_files: list[SourceFile] = []
    reconstructed_data: list[Context] = []
    reconstructed_service: list[Microservice] = []
    plugins = []

    def __new__(cls, source_files, plugins):
        if cls._instance is None:
            print("Create Reconstruction Handler")
            cls._instance = super(ReconstructionHandler, cls).__new__(cls)
        cls.source_files = source_files
        cls.plugins = plugins
        return cls._instance

    def reconstruct_start(self):
        """
        Method that start the phases of the reconstruction process in the order,
        domain data, microservices and operation.
        """
        self.__reconstruct_data(self.source_files)
        self.__reconstruct_service(self.source_files)

    def __reconstruct_data(self, source_files: list[SourceFile]):
        if PluginType.JAVA in self.plugins:
            self.reconstructed_data.extend(
                JavaPlugin().execute_reconstruction(source_files)
            )

    def __reconstruct_service(self, source_files: list[SourceFile]):
        if PluginType.SPRING in self.plugins:
            self.reconstructed_service.extend(
                SpringPlugin().execute_reconstruction(source_files)
            )

    def reconstruct_save(self):
        """
        Save the reconstructed architecture information to the database.
        """
        save_contexts(self.reconstructed_data)
        save_microservices(self.reconstructed_service)
