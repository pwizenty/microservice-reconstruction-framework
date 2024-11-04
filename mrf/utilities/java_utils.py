from enum import Enum

import javalang as java_lang
from javalang.tree import CompilationUnit, ClassDeclaration, FieldDeclaration, Annotation

from mrf.utilities.sping import APPLICATION_CLASS

PRIMITIVE_JAVA_TYPES = ["byte", "short", "int", "long", "float", "double", "char", "boolean", "string", "date"]
# Level for matching qualified names, e.g., 'com.lakesidemutual.customercore.domain.customer' to
# 'com.lakesidemutual.customercore.domain'
HIERARCHY_LEVEL = 3


class DependencyType(Enum):
    EXTERNAL_DEPENDENCY = "External_Dependency"
    PROJECT_DEPENDENCY = "Project_Dependency"
    PACKAGE_DEPENDENCY = "Package_Dependency"


class ImportType:
    def __init__(self, qualified_import_name: str, dependency_type: DependencyType):
        self.qualified_import_name = qualified_import_name
        self.dependency_type = dependency_type


def parse_java_file(file):
    tree = java_lang.parse.parse(file)
    return tree


def get_class_from_tree(unit: CompilationUnit):
    classes = [c for c in unit.types if isinstance(c, ClassDeclaration)]
    return classes[0] if classes else None


def has_annotation_for_class(clazz: ClassDeclaration, annotation_name):
    if hasattr(clazz, "annotations"):
        annotation = find_annotation(clazz.annotations, annotation_name)
        if annotation is not None:
            return True
        else:
            return False


def has_annotation_for_field(field: FieldDeclaration, annotation_name):
    if hasattr(field, "annotations"):
        annotation = find_annotation(field.annotations, annotation_name)
        if annotation is not None:
            return True
        else:
            return False


def find_annotation(annotations: list[Annotation], annotation_name):
    return next((an for an in annotations if hasattr(an, "name") and getattr(an, "name") == annotation_name), None)


def get_class_name(clazz: ClassDeclaration):
    if hasattr(clazz, "name"):
        return clazz.name


def get_qualified_class_name(tree: CompilationUnit):
    clazz = get_class_from_tree(tree)
    class_name = get_class_name(clazz)
    if hasattr(tree, "package"):
        package_name = tree.package.name
        return package_name + "." + class_name.lower()
    # Return simple class name, when package is not set
    return class_name


def get_field_name(field: FieldDeclaration):
    if hasattr(field, "declarators"):
        return field.declarators[0].name
    else:
        return None


def adjust_name(name: str):
    return name.removesuffix(APPLICATION_CLASS.lower())


def match_context(qualified_name_context: str, qualified_name_structure: str):
    return __build_matches(qualified_name_context, qualified_name_structure, ".")


def resolve_complex_field(tree: CompilationUnit, field_type: str):
    if hasattr(tree, "imports"):
        basic_name = next(
            (im for im in tree.imports if hasattr(im, "path") and getattr(im, "path").endswith(field_type)), None)
        # Case 1: Complex type exist in the same package as the currently reconstructed Java class (code accessible)
        if basic_name is None:
            qualified_import_name = __build_qualified_name(tree, field_type)
            return ImportType(qualified_import_name, DependencyType.PACKAGE_DEPENDENCY)
        # Case 2: Complex type exist in a different package as the reconstructed Java class (code accessible)
        elif basic_name is not None and __has_matching_name(basic_name.path, __get_package_name(tree)):
            return ImportType(basic_name.path, DependencyType.PROJECT_DEPENDENCY)
        # Case 3: Complex type is an external import, e.g., Maven import (code not accessible)
        elif basic_name is not None and not __has_matching_name(basic_name.path, __get_package_name(tree)):
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
    else:
        return None


def __has_matching_name(name1: str, name2: str):
    matched_parts = __build_matches(name1, name2, ".")
    if len(matched_parts) < HIERARCHY_LEVEL:
        return False
    else:
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
