"""Module with common classes shared between various plugins."""

from dataclasses import dataclass, field

from javalang.tree import CompilationUnit


@dataclass
class Data:
    """Meta-data attached to reconstructed architecture information.

    Used, e.g., to attach Domain Driven Design features to data fields.

    Attributes:
        name (str): Name of the meta-data information
        values (dict): Key-Value information about the meta-data information
    """

    name: str
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class JavaClassArtifact:
    """Java class source code artifact.

    Holds the path to the file and a corresponding parsed version as a
    CompilationUnit.

    Attributes:
        tree (str): path the java source code artifact
        path (CompilationUnit): Parsed source code artifact
    """

    tree: CompilationUnit
    path: str
