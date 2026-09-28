"""Handling of the reconstruction process.

Covers the management of source code files and the order of the reconstruction
phases.
"""

import logging
from typing import ClassVar

from mrf.modules.domain_data import Context
from mrf.modules.service import Microservice
from mrf.plugins.data.java.java_plugin import JavaPlugin
from mrf.plugins.reconstruction_plugin import PluginType
from mrf.plugins.service.spring.spring_plugin import SpringPlugin
from mrf.repositories.mongo_repository import save_contexts, save_microservices
from mrf.utilities.command_line import SourceFile

logger = logging.getLogger(__name__)


class ReconstructionHandler:
    """Class for handling the reconstruction process."""

    # NOTE: These are deliberately class level because the handler is a
    # singleton. State therefore leaks between runs and tests; see the known
    # issues in CLAUDE.md. Annotated as ClassVar to describe the current
    # behaviour, not to endorse it.
    _instance: ClassVar["ReconstructionHandler | None"] = None
    source_files: ClassVar[list[SourceFile]] = []
    reconstructed_data: ClassVar[list[Context]] = []
    reconstructed_service: ClassVar[list[Microservice]] = []
    plugins: ClassVar[list[PluginType]] = []

    def __new__(
        cls, source_files: list[SourceFile], plugins: list[PluginType]
    ) -> "ReconstructionHandler":
        """Return the singleton handler, updating it with the current run's input.

        Args:
            source_files ([SourceFile]): Source files of the analysed system
            plugins ([PluginType]): Plugins selected for the reconstruction

        Returns:
            ReconstructionHandler: The shared handler instance
        """
        if cls._instance is None:
            logger.debug("Create Reconstruction Handler")
            cls._instance = super().__new__(cls)
        cls.source_files = source_files
        cls.plugins = plugins
        return cls._instance

    def reconstruct_start(self) -> None:
        """Start the phases of the reconstruction process.

        The phases run in the order domain data, microservices and operation.
        """
        self.__reconstruct_data(self.source_files)
        self.__reconstruct_service(self.source_files)

    def __reconstruct_data(self, source_files: list[SourceFile]) -> None:
        if PluginType.JAVA in self.plugins:
            self.reconstructed_data.extend(
                JavaPlugin().execute_reconstruction(source_files)
            )

    def __reconstruct_service(self, source_files: list[SourceFile]) -> None:
        if PluginType.SPRING in self.plugins:
            results = SpringPlugin().execute_reconstruction(source_files)
            contexts = JavaPlugin().reconstruct_dependencies(
                source_files, results.complex_types
            )
            self.reconstructed_service.extend(results.microservices)
            # Assign on the class, not the instance: the attribute is shared
            # state of the singleton (see the note above).
            ReconstructionHandler.reconstructed_data = self.__merge_contexts(
                self.reconstructed_data, contexts
            )

    def reconstruct_save(self) -> None:
        """Save the reconstructed architecture information to the database."""
        save_contexts(self.reconstructed_data)
        save_microservices(self.reconstructed_service)

    def __merge_contexts(
        self, base: list[Context], other: list[Context]
    ) -> list[Context]:
        for ctx in other:
            existing = next((c for c in base if c.name == ctx.name), None)
            if existing is None:
                base.append(ctx)
                continue
            for structure in ctx.data_structures:
                if not any(s.name == structure.name for s in existing.data_structures):
                    existing.data_structures.append(structure)
            for collection in ctx.collections:
                if not any(s.name == collection.name for s in existing.collections):
                    existing.collections.append(collection)
            for enum in ctx.enums:
                if not any(e.name == enum.name for e in existing.enums):
                    existing.enums.append(enum)
        return base
