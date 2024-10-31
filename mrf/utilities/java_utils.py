import javalang as java_lang
from javalang.tree import CompilationUnit, ClassDeclaration, FieldDeclaration

from mrf.utilities.sping import APPLICATION_CLASS

PRIMITIVE_JAVA_TYPES = ["byte", "short", "int", "long", "float", "double", "char", "boolean", "string"]


def parse_java_file(file):
    tree = java_lang.parse.parse(file)
    return tree


def get_class_from_tree(unit: CompilationUnit):
    classes = [c for c in unit.types if isinstance(c, ClassDeclaration)]
    return classes[0] if classes else None


def has_annotation(clazz: ClassDeclaration, annotation_name):
    annotation = find_annotation(clazz, annotation_name)
    if annotation is not None:
        return True
    else:
        return False


def find_annotation(clazz: ClassDeclaration, annotation_name):
    if hasattr(clazz, "annotations"):
        annotation = [an for an in clazz.annotations if hasattr(an, "name") and getattr(an, "name") == annotation_name]
        if annotation is not None:
            return annotation[0] if annotation else None
    else:
        return None


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
    context_parts = qualified_name_context.split(".")
    structure_parts = qualified_name_structure.split(".")
    # Remove Element specific name from the arrays, e.g., from "com.lakesidemutual.customercore.customercore"
    # to "com.lakesidemutual.customercore" to get the top level name of the context
    match_parts = []
    for context_part, structure_part in zip(context_parts, structure_parts):
        if context_part == structure_part:
            match_parts.append(context_part)
        else:
            # Stop at the first not matching part
            break
    return match_parts
