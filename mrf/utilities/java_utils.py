"""
Utility module for handling Java-based source code artifacts.
"""

from dataclasses import dataclass
from enum import Enum

import javalang as java_lang
from javalang.tree import (
    CompilationUnit,
    ClassDeclaration,
    FieldDeclaration,
    Annotation,
    InterfaceDeclaration,
    PackageDeclaration,
    EnumDeclaration,
)

from mrf.utilities.sping import APPLICATION_CLASS

PRIMITIVE_JAVA_TYPES = [
    "byte",
    "short",
    "int",
    "long",
    "float",
    "double",
    "char",
    "boolean",
    "string",
    "date",
]
# Level for matching qualified names, e.g.,
# 'com.lakesidemutual.customercore.domain.customer' to
# 'com.lakesidemutual.customercore.domain'
HIERARCHY_LEVEL = 3


class DependencyType(Enum):
    """
    Enumeration for handling different types of dependencies, e.g.,
    dependencies that are in the same Java package, dependencies that are in the
    same project or external dependencies that are imported via a dependency
    management tool like Maven.
    """

    EXTERNAL_DEPENDENCY = "External_Dependency"
    PROJECT_DEPENDENCY = "Project_Dependency"
    PACKAGE_DEPENDENCY = "Package_Dependency"


@dataclass
class ImportType:
    """
    Class for handling different types of imports.
    """

    qualified_import_name: str
    dependency_type: DependencyType


def parse_java_file(file: str):
    """
    Parse a given Java file into a ComplicationUnit

    Args:
        file (): Java file as a String

    Returns:
        tree (CompilationUnit): Parsed Java file
    """
    tree = java_lang.parse.parse(file)
    return tree


def get_class_from_tree(unit: CompilationUnit):
    """
    Transform a Java ComplicationUnit into a Java class if it is an instance of
    a Enumeration, Interface, Package or Class.

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
            | PackageDeclaration
            | EnumDeclaration,
        )
    ]
    return classes[0] if classes else None


def has_annotation_for_class(clazz: ClassDeclaration, annotation_name: str):
    """
    Method that check that a clazz has a specific annotation.

    Args:
        clazz (ClassDeclaration): Parsed Java class artifact
        annotation_name (str): Name of the annotation

    Returns:
        True / False based of the class has the annotation
    """
    if hasattr(clazz, "annotations"):
        annotation = find_annotation(clazz.annotations, annotation_name)
        return bool(annotation)
    return False


def has_annotation_for_field(field: FieldDeclaration, annotation_names: str):
    """
    Checks if a field of a has a specific annotation.

    Args:
        field (FieldDeclaration): Field of a Java class
        annotation_names (): Annotation name

    Returns:
        True / False based of the field has the annotation
    """
    if hasattr(field, "annotations"):
        annotation = find_annotation(field.annotations, annotation_names)
        return bool(annotation)
    return False


def find_annotation(annotations: list[Annotation], annotation_names):
    """
    Method that checks if an annotation is in a list of annotations.

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
            if hasattr(an, "name") and getattr(an, "name") in annotation_names
        ),
        None,
    )
    return annotation


def get_class_name(clazz: ClassDeclaration):
    """
    Get the name of a Java class

    Args:
        clazz (ClassDeclaration): Java class

    Returns:
        name (str): Name of the Java class
    """
    if hasattr(clazz, "name"):
        return clazz.name
    return None


def get_qualified_class_name(tree: CompilationUnit):
    """
    Get the qualified name of a class from a ComplicationUnit

    Args:
        tree (): ComplicationUnit of a Java class artifact

    Returns:
        class_name (str): Qualified class name of the ComplicationUnit
    """
    clazz = get_class_from_tree(tree)
    class_name = get_class_name(clazz)
    if hasattr(tree, "package"):
        package_name = tree.package.name
        return package_name + "." + class_name.lower()
    # Return simple class name, when package is not set
    return class_name


def get_field_name(field: FieldDeclaration):
    """
    Get the name of a field from a FieldDeclaration.

    Args:
        field (FieldDeclaration): Field of a Java class

    Returns:
        field_name (str): Name of the field
    """
    if hasattr(field, "declarators"):
        return field.declarators[0].name
    return None


def adjust_name(name: str):
    """
    Remove specific naming parts from a string, e.g., remove "Application" from
    the class name "CustomerCoreApplication".

    This is dane because the "Application" suffix does not add any value about
    the domain to the class name, but is a used to best practices in the
    Spring Framework to signal the main class of the Spring application.

    Args:
        name (): Name of a class, for example.

    Returns:
        adjusted_name (str): Adjusted name
    """
    return name.removesuffix(APPLICATION_CLASS.lower())


def match_context(qualified_name_context: str, qualified_name_structure: str):
    """
    Compare of names of a reconstructed context.

    Args:
        qualified_name_context (str): Context name
        qualified_name_structure (str): Context name

    Returns:
        True / False if the context matches
    """
    return __build_matches(qualified_name_context, qualified_name_structure, ".")


def resolve_complex_field(tree: CompilationUnit, field_type: str):
    """
    Resolve the qualified name of a complex type based on the type of dependency

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
                if hasattr(im, "path") and getattr(im, "path").endswith(field_type)
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
    return None


def __build_qualified_name(tree: CompilationUnit, field_type: str):
    package_name = __get_package_name(tree)
    if package_name is not None:
        qualified_field_type = package_name + "." + field_type
        return qualified_field_type
    return "cc"


def __get_package_name(tree: CompilationUnit):
    if hasattr(tree, "package"):
        return tree.package.name
    return None


def __has_matching_name(name1: str, name2: str):
    matched_parts = __build_matches(name1, name2, ".")
    if len(matched_parts) < HIERARCHY_LEVEL:
        return False
    return True


def __build_matches(string1: str, string2: str, split_char: str):
    matches = []
    string1_parts = string1.split(split_char)
    string2_parts = string2.split(split_char)

    for part1, part2 in zip(string1_parts, string2_parts):
        if part1 == part2:
            matches.append(part1)
        else:
            # Stop at first not matching part
            break
    return matches
