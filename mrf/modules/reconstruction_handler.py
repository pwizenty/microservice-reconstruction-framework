from mrf.plugins.data.java.java_plugin import JavaPlugin
from mrf.plugins.reconstruction_plugin import PluginType
from mrf.utilities.command_line import SourceFile


class ReconstructionHandler(object):
    _instance = None
    source_files = [SourceFile]
    reconstructed_data = []
    plugins = []

    def __new__(cls, source_files, plugins):
        if cls._instance is None:
            print("Create Reconstruction Handler")
            cls._instance = super(ReconstructionHandler, cls).__new__(cls)
        cls.source_files = source_files
        cls.plugins = plugins
        return cls._instance

    def reconstruct_start(self):
        self.reconstruct_data(self.source_files)


        return "start - testo"

    def reconstruct_data(self, source_files: list[SourceFile]):
        if PluginType.Java in self.plugins:
            self.reconstructed_data = JavaPlugin().execute_reconstruction(source_files)
