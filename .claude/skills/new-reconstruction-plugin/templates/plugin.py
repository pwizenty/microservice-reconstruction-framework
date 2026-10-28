"""Plugin for reconstructing <WHAT> from <TECHNOLOGY> source artifacts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile

logger = logging.getLogger(__name__)


@dataclass
class TechnologyReconstructionResult:
    """Result of the <TECHNOLOGY> reconstruction.

    Attributes:
        items: Reconstructed model elements (replace with concrete model types
            from ``mrf.modules``).
    """

    items: list[object] = field(default_factory=list)


class TechnologyPlugin(Plugin):
    """Reconstructs <WHAT> from <TECHNOLOGY> artifacts."""

    def __init__(self) -> None:
        self._result = TechnologyReconstructionResult()

    def file_types(self) -> list[str]:
        """Return the file suffixes this plugin analyses.

        Returns:
            Supported file suffixes including the dot, e.g. ``[".yml"]``.
        """
        return [".<suffix>"]

    def execute_reconstruction(
        self, source_files: list[SourceFile]
    ) -> TechnologyReconstructionResult:
        """Run the reconstruction on all supported source files.

        Args:
            source_files: All source artifacts of the analysed system.

        Returns:
            The reconstructed model elements.
        """
        relevant = [
            f
            for f in source_files
            if f.suffix in self.file_types() and f.file is not None
        ]
        logger.info("%s: analysing %d files", type(self).__name__, len(relevant))
        for source_file in relevant:
            self._reconstruct(source_file)
        return self._result

    def _reconstruct(self, source_file: SourceFile) -> None:
        raise NotImplementedError
