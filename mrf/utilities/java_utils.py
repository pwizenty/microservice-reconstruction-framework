"""Utility module for handling Java-based source code artifacts."""

import logging
from dataclasses import dataclass
from enum import Enum

import javalang as java_lang
from javalang.parser import JavaParserBaseException
from javalang.tokenizer import LexerError
from javalang.tree import (
    Annotation,
    AnnotationDeclaration,
    ClassDeclaration,
    CompilationUnit,
    Declaration,
    EnumDeclaration,
    FieldDeclaration,
    InterfaceDeclaration,
    Literal,
    RecordDeclaration,
    TypeDeclaration,
)

from mrf.plugins.common.common_plugin import JavaClassArtifact
from mrf.utilities.command_line import SourceFile
from mrf.utilities.sping import APPLICATION_CLASS

logger = logging.getLogger(__name__)

TECHNOLOGY_SPRING_TYPES = ["responseentity"]

ANNOTATION_VALUE_ELEMENT = "value"
"""Name Java gives the element of a single-element annotation.

``@RequestMapping("/customers")`` is shorthand for
``@RequestMapping(value = "/customers")``, so the unnamed element is
reported under this name.
"""

COLLECTION_TYPES = ["list"]

VOID_TYPES = ["void"]
"""Names of the Java types that express the absence of a return value.

Covers the primitive ``void`` and the class ``java.lang.Void``, which Spring
uses to say that a response carries no body, as in ``ResponseEntity<Void>``.
"""

PRIMITIVE_JAVA_TYPES = [
    "byte",
    "short",
    "int",
    "integer",
    "long",
    "float",
    "double",
    "char",
    "boolean",
    "string",
    "date",
    "instant",
    "bigdecimal",
]
# Level for matching qualified names, e.g.,
# 'com.lakesidemutual.customercore.domain.customer' to
# 'com.lakesidemutual.customercore.domain'
HIERARCHY_LEVEL = 3

UNKNOWN_CLASS_NAME = "UnknownClassName"
UNKNOWN_PACKAGE_NAME = "UnknownPackageName"
UNKNOWN_FIELD_NAME = "UnkownFieldName"
UNKNOWN_IMPORT_NAME = "UnknownImportName"


class DependencyType(Enum):
    """Type of a dependency between Java artifacts.

    Distinguishes dependencies within the same Java package, within the same
    project, and external dependencies imported via a dependency management
    tool like Maven.
    """

    EXTERNAL_DEPENDENCY = "ExternalDependency"
    PROJECT_DEPENDENCY = "ProjectDependency"
    PACKAGE_DEPENDENCY = "PackageDependency"
    UNKNOWN_DEPENDENCY = "UnkownDependency"


@dataclass
class ImportType:
    """Class for handling different types of imports."""

    qualified_import_name: str
    dependency_type: DependencyType


class NoJavaDeclrationException(Exception):
    """Raised when a Java compilation unit has no valid declaration."""

    def __init__(self, unit: CompilationUnit, message: str):
        self.unit = unit
        self.message = message
        super().__init__(message)

    def __str__(self):
        return self.message


class NoProjectDependencyFoundException(Exception):
    """Exepction when the project dependency could not be resolved."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def __str__(self):
        return self.message


def parse_java_file(file: str) -> CompilationUnit:
    """Parse a given Java file into a CompilationUnit.

    Args:
        file (): Java file as a String

    Returns:
        tree (CompilationUnit): Parsed Java file
    """
    tree = java_lang.parse.parse(file)
    return tree


def get_class_from_tree(unit: CompilationUnit) -> TypeDeclaration:
    """Transform a Java CompilationUnit into a Java class.

    Applies if the unit is an instance of an Enumeration, Interface, Package
    or Class.

    Args:
        unit (CompilationUnit): Java ComplicationUnit

    Returns:
        class(Declaration): Specific declaration
    """
    classes = [
        c
        for c in unit.types
        if isinstance(
            c,
            ClassDeclaration
            | InterfaceDeclaration
            | EnumDeclaration
            | AnnotationDeclaration
            | RecordDeclaration,
        )
    ]

    if not classes:
        raise NoJavaDeclrationException(unit, "No declration found in Unit")

    return classes[0]


def has_annotation(dec: Declaration, names: list[str]) -> bool:
    """Check if a declaration has one of the given annotations.

    Args:
        dec (Declaration): Parsed Java declaration
        names ([str]): Names of the annotations to look for

    Returns:
        bool: ``True`` if the declaration carries one of the annotations
    """
    if hasattr(dec, "annotations"):
        annotation = find_annotation(dec.annotations, names)
        return bool(annotation)
    return False


def find_annotation(
    annotations: list[Annotation], annotation_names
) -> Annotation | None:
    """Method that checks if an annotation is in a list of annotations.

    Args:
        annotations (): List of possible annotations.
        annotation_names (): Name of the annotation we are looking for.

    Returns:
        annotation: Annotation we are looking for.
    """
    annotation = next(
        (
            an
            for an in annotations
            if hasattr(an, "name") and an.name in annotation_names
        ),
        None,
    )
    return annotation


def get_annotation_values(annotation: Annotation) -> dict[str, str]:
    """Read the literal element values of an annotation, by element name.

    Java writes the element of an annotation in three shapes, and all three
    reach here: a marker annotation such as ``@PathVariable`` has no element, a
    single-element annotation such as ``@RequestMapping("/customers")`` names
    none, and ``@RequestParam(value = "filter", defaultValue = "")`` names each
    of them. The unnamed element is Java's ``value``, so it is reported under
    that name.

    Only literal values are reported. An element whose value is an expression,
    such as ``@RequestMapping(method = RequestMethod.GET)``, carries no literal
    to recover and is left out rather than reported as the text of the
    expression.

    Args:
        annotation (Annotation): Parsed Java annotation

    Returns:
        dict[str, str]: Literal values of the annotation, by element name, with
            the quotes of a string literal removed
    """
    element = annotation.element
    if element is None:
        return {}

    if not isinstance(element, list):
        value = __literal_value(element)
        return {} if value is None else {ANNOTATION_VALUE_ELEMENT: value}

    values: dict[str, str] = {}
    for pair in element:
        name = getattr(pair, "name", None)
        value = __literal_value(getattr(pair, "value", None))
        if name is not None and value is not None:
            values[name] = value
    return values


def __literal_value(element) -> str | None:
    """Return the value of a literal element, or ``None`` for an expression."""
    if not isinstance(element, Literal):
        return None
    value = element.value
    if not isinstance(value, str):
        return None
    # A string literal keeps its quotes in the parse tree, a numeric or boolean
    # literal has none.
    if len(value) > 1 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def get_class_name(clazz: TypeDeclaration) -> str:
    """Get the name of a Java class.

    Args:
        clazz (ClassDeclaration): Java class

    Returns:
        name (str): Name of the Java class
    """
    if hasattr(clazz, "name"):
        return clazz.name
    else:
        return UNKNOWN_CLASS_NAME


def get_qualified_class_name(tree: CompilationUnit) -> str:
    """Get the qualified name of a class from a CompilationUnit.

    Args:
        tree (): ComplicationUnit of a Java class artifact

    Returns:
        class_name (str): Qualified class name of the ComplicationUnit
    """
    clazz = get_class_from_tree(tree)

    if clazz is None:
        return UNKNOWN_CLASS_NAME

    class_name = get_class_name(clazz)

    if hasattr(tree, "package"):
        package = tree.package
        package_name = package.name
        return package_name + "." + class_name
    # Return simple class name, when package is not set
    return class_name


def get_field_name(field: FieldDeclaration) -> str:
    """Get the name of a field from a FieldDeclaration.

    Args:
        field (FieldDeclaration): Field of a Java class

    Returns:
        field_name (str): Name of the field
    """
    if hasattr(field, "declarators"):
        declarators = field.declarators
        return declarators[0].name
    return UNKNOWN_FIELD_NAME


def adjust_name(name: str) -> str:
    """Remove specific naming parts from a string.

    For example, remove "Application" from the class name
    "CustomerCoreApplication".

    This is dane because the "Application" suffix does not add any value about
    the domain to the class name, but is a used to best practices in the
    Spring Framework to signal the main class of the Spring application.

    Args:
        name (): Name of a class, for example.

    Returns:
        adjusted_name (str): Adjusted name
    """
    return name.removesuffix(APPLICATION_CLASS)


def match_context(
    qualified_name_context: str, qualified_name_structure: str
) -> list[str]:
    """Compare of names of a reconstructed context.

    Args:
        qualified_name_context (str): Context name
        qualified_name_structure (str): Context name

    Returns:
        True / False if the context matches
    """
    return __build_matches(qualified_name_context, qualified_name_structure, ".")


def resolve_complex_field(tree: CompilationUnit, field_type: str) -> ImportType:
    """Resolve the qualified name of a complex type from its dependency type.

    Args:
        tree (CompilationUnit): Unit of the class that the type is in
        field_type (str): Type of the import

    Returns:
        import_type (ImportType): Resolved import
    """
    if hasattr(tree, "imports"):
        basic_name = next(
            (
                im
                for im in tree.imports
                if hasattr(im, "path") and im.path.endswith(field_type)
            ),
            None,
        )
        # Case 1: Complex type exist in the same package as the currently
        # reconstructed Java class (code accessible)
        if basic_name is None:
            qualified_import_name = __build_qualified_name(tree, field_type)
            return ImportType(qualified_import_name, DependencyType.PACKAGE_DEPENDENCY)
        # Case 2: Complex type exist in a different package as the reconstructed
        # Java class (code accessible)
        if basic_name is not None and __has_matching_name(
            basic_name.path, __get_package_name(tree)
        ):
            return ImportType(basic_name.path, DependencyType.PROJECT_DEPENDENCY)
        # Case 3: Complex type is an external import, e.g., Maven import
        # (code not accessible)
        if basic_name is not None and not __has_matching_name(
            basic_name.path, __get_package_name(tree)
        ):
            return ImportType(basic_name.path, DependencyType.EXTERNAL_DEPENDENCY)
    return ImportType(UNKNOWN_FIELD_NAME, DependencyType.UNKNOWN_DEPENDENCY)


def load_classes(
    source_files: list[SourceFile], java_types: list[str]
) -> list[JavaClassArtifact]:
    """Load java class file for plugin.

    Args:
        source_files (): List of Java source files
        java_types (): Supported filed types by the Java plugin

    Returns:
        java_classes (JavaClassArtifact): List of Java class artifacts
    """
    java_classes: list[JavaClassArtifact] = []
    unparsable: list[str] = []
    for s in source_files:
        if s.suffix in java_types:
            try:
                tree = parse_java_file(s.file)
            except (JavaParserBaseException, LexerError) as error:
                # A single file the parser cannot read must not end the
                # reconstruction of the whole system. Report it instead, so
                # that the gap in the result stays visible.
                unparsable.append(s.path)
                logger.warning(
                    "Skipping %s, the parser cannot read it: %s",
                    s.path,
                    type(error).__name__,
                )
                continue
            java_class = JavaClassArtifact(tree, s.path)
            java_classes.append(java_class)
    if unparsable:
        logger.warning(
            "%d of %d Java files were skipped, the reconstruction is incomplete: %s",
            len(unparsable),
            len(unparsable) + len(java_classes),
            ", ".join(unparsable),
        )
    return java_classes


def match_microservice_interface(microservice_name: str, interface_name: str) -> bool:
    """Check whether an interface belongs to a microservice.

    Args:
        microservice_name (str): Qualified name of the microservice
        interface_name (str): Qualified name of the interface

    Returns:
        bool: ``True`` if both qualified names match up to
        :data:`HIERARCHY_LEVEL` package levels
    """
    return __has_matching_name(microservice_name, interface_name)


def __build_qualified_name(tree: CompilationUnit, field_type: str) -> str:
    package_name = __get_package_name(tree)
    if package_name is not None:
        qualified_field_type = package_name + "." + field_type
        return qualified_field_type


def __get_package_name(tree: CompilationUnit) -> str:
    if hasattr(tree, "package"):
        package = tree.package
        return package.name
    return UNKNOWN_PACKAGE_NAME


def __has_matching_name(name1: str, name2: str) -> bool:
    matched_parts = __build_matches(name1, name2, ".")
    return len(matched_parts) >= HIERARCHY_LEVEL


def __build_matches(string1: str, string2: str, split_char: str) -> list[str]:
    matches = []
    string1_parts = string1.split(split_char)
    string2_parts = string2.split(split_char)

    # strict=False on purpose: the names usually differ in length and
    # matching stops at the first differing part anyway.
    for part1, part2 in zip(string1_parts, string2_parts, strict=False):
        if part1 == part2:
            matches.append(part1)
        else:
            # Stop at first not matching part
            break
    return matches


def adjust_qualified_name(
    context_qualified_name: str, data_structure_qualified_name: str
) -> str:
    """Re-root a data structure's qualified name onto its context.

    Args:
        context_qualified_name (str): Qualified name of the context
        data_structure_qualified_name (str): Qualified name of the structure

    Returns:
        str: Qualified name of the structure below the context
    """
    name = data_structure_qualified_name.rsplit(".", 1)[-1]
    adjusted_name = f"{context_qualified_name}.{name}"
    return adjusted_name
