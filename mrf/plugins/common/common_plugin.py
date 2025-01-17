"""
Module with common classes shared between various plugins.
"""

from dataclasses import dataclass

from javalang.tree import CompilationUnit


@dataclass
class Data:
    """
    Data structure class for adding meta-data to reconstructed architecture
    information, e.g., Domain Driven Design features to data fields.

    Attributes:
        name (str): Name of the meta-data information
    """

    name: str
    values = {}


@dataclass
class JavaClassArtifact:
    """
    Representation of a Java class source code artifact with the path to the
    file and a corresponding parsed version as a CompilationUnit.

    Attributes:
        tree (str): path the java source code artifact
        path (CompilationUnit): Parsed source code artifact
    """

    tree: CompilationUnit
    path: str
