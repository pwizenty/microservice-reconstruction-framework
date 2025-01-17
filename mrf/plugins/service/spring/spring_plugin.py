"""
Module with class and methods to reconstruction microservices from Java based
source code artifacts.
"""

from typing import List

from mrf.plugins.common.common_plugin import JavaClassArtifact
from mrf.plugins.reconstruction_plugin import Plugin


class SpringPlugin(Plugin):
    """
    Class Plugin for recovering microservices from source code written in Java using
    the Spring framework.
    """

    def __init__(self):
        self.java_classes: List[JavaClassArtifact] = []

    def file_types(self):
        """
        Return the type of files that are supported by the Spring plugin.

        Returns: list of supported file types.

        """
        return [".java"]

    def execute_reconstruction(self, source_files):
        """
        Execute the reconstruction functionality of the Spring plugin.

        Args:
            source_files ():

        Returns:

        """
