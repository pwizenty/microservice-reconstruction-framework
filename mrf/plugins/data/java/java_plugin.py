from typing import List

from javalang.tree import CompilationUnit, FieldDeclaration

from mrf.plugins.common.common_plugin import Data
from mrf.plugins.data.domain_data import Context, DataStructure, DDD_ENTITY, \
    PrimitiveType, Field, ComplexType, ClassType, DDD_IDENTIFIER
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.java_utils import parse_java_file, has_annotation_for_class, \
    get_class_from_tree, get_class_name, get_qualified_class_name, \
    PRIMITIVE_JAVA_TYPES, get_field_name, match_context, resolve_complex_field, \
    DependencyType, ImportType, has_annotation_for_field
from mrf.utilities.sping import CONTEXT_ANNOTATION, APPLICATION_CLASS, \
    ENTITY_ANNOTATION, ID_ANNOTATIONS
from mrf.utilities.sping import INFRASTRUCTURE_TECHNOLOGIES


class JavaClassArtefact:
    def __init__(self, tree: CompilationUnit, path: str):
        self.tree = tree
        self.path = path


class JavaPlugin(Plugin):
    def __init__(self):
        self.java_classes: List[JavaClassArtefact] = []
        self.contexts: List[Context] = []

    def file_types(self):
        return [".java"]

    def execute_reconstruction(self, source_files: list[SourceFile]):
        self.__load_classes(source_files)
        for c in self.java_classes:
            self.__reconstruct_context(c)
        for c in self.java_classes:
            self.__reconstruct_entity(c)

        return self.contexts

    def __load_classes(self, source_files: list[SourceFile]):
        for s in source_files:
            if s.suffix in self.file_types():
                tree = parse_java_file(s.file)
                java_class = JavaClassArtefact(tree, s.path)
                self.java_classes.append(java_class)

    def __reconstruct_context(self, java_class: JavaClassArtefact):
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation_for_class(clazz, CONTEXT_ANNOTATION):
            name = get_class_name(clazz).removesuffix(APPLICATION_CLASS)
            # Check if context is related to a Spring infrastructure technology
            if any(t in name.lower() for t in INFRASTRUCTURE_TECHNOLOGIES):
                return None
            qualified_name = (get_qualified_class_name(java_class.tree)
                              .removesuffix(APPLICATION_CLASS.lower())
                              .removesuffix("." + name.lower()))
            # Remove potential doubling name parts, e.g.,
            # "com.lakesidemutual.customercore.customercore" to
            # "com.lakesidemutual.customercore".
            context = Context(qualified_name, name, java_class.path)
            self.contexts.append(context)

    def __reconstruct_entity(self, java_class: JavaClassArtefact):
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation_for_class(clazz, ENTITY_ANNOTATION):
            structure = self.__reconstruct_data_structure(java_class)
            data = Data(DDD_ENTITY)
            structure.data.append(data)
            context_name = self.__find_context_name(structure.qualified_name)
            context = next(
                (c for c in self.contexts if c.qualified_name == context_name),
                None)
            context.data_structures.append(structure)

    def __reconstruct_data_structure(self, java_class: JavaClassArtefact):
        clazz = get_class_from_tree(java_class.tree)
        name = get_class_name(clazz)
        qualified_name = get_qualified_class_name(java_class.tree)
        structure = DataStructure(qualified_name, name, java_class.path)
        primitive_fields = self.__reconstruct_primitive_type(clazz.fields)
        complex_fields = self.__reconstruct_complex_type(java_class)
        structure.fields.extend(primitive_fields)
        structure.fields.extend(complex_fields)
        return structure

    def __reconstruct_primitive_type(self, field_decs: [FieldDeclaration]):
        primitive_fields: List[Field] = []
        for f in field_decs:
            if f.type.name.lower() in PRIMITIVE_JAVA_TYPES:
                field_type = f.type.name.lower()
                field_name = get_field_name(f)
                primitive_type = PrimitiveType(field_type)
                field = Field(field_name, primitive_type)

                if has_annotation_for_field(f, ID_ANNOTATIONS):
                    data = Data(DDD_IDENTIFIER)
                    field.data.append(data)
                primitive_fields.append(field)
        return primitive_fields

    def __reconstruct_complex_type(self, java_class: JavaClassArtefact):
        complex_fields: List[Field] = []
        clazz = get_class_from_tree(java_class.tree)

        for f in clazz.fields:
            if (hasattr(f, "type")
                    and f.type.name.lower() not in PRIMITIVE_JAVA_TYPES):
                result = resolve_complex_field(java_class.tree, f.type.name)
                complex_type = self.__handle_dependency(result)
                field_name = get_field_name(f)
                field = Field(field_name, complex_type)
                if has_annotation_for_field(f, ID_ANNOTATIONS):
                    data = Data(DDD_IDENTIFIER)
                    field.data.append(data)
                complex_fields.append(field)
        return complex_fields

    def __find_context_name(self, qualified_name: str):
        match_parts = []
        for context in self.contexts:
            parts = match_context(context.qualified_name, qualified_name)
            if len(match_parts) <= len(parts):
                match_parts = parts
        if len(match_parts) != 0:
            context_name = ".".join(match_parts)
            return context_name
        else:
            return None

    def __assign_struct_to_context(self, data_structure: DataStructure, name):
        if name is not None:
            context = next((context for context in self.contexts
                            if context.qualified_name == name), None)
            context.data_structures.append(data_structure)
        else:
            # TODO: Handling function to support DataStructures without context. 
            pass

    def __handle_dependency(self, import_type: ImportType):
        complex_type = None
        match import_type.dependency_type:
            case DependencyType.PROJECT_DEPENDENCY:
                complex_type = self.__handle_project_dependency(
                    import_type.qualified_import_name)
            case DependencyType.PACKAGE_DEPENDENCY:
                complex_type = self.__handle_package_dependency(
                    import_type.qualified_import_name)
            case DependencyType.EXTERNAL_DEPENDENCY:
                complex_type = self.__handle_external_dependency(
                    import_type.qualified_import_name)
        return complex_type

    def __handle_project_dependency(self, import_name: str):
        exist = self.__check_for_dependency(import_name)
        if exist is False:
            class_name = import_name.split(".").pop()
            java_class = next((java for java in self.java_classes if
                               java.path.endswith(class_name + ".java")), None)
            structure = self.__reconstruct_data_structure(java_class)
            context_name = self.__find_context_name(structure.qualified_name)
            context = next((c for c in self.contexts if
                            c.qualified_name == context_name), None)
            context.data_structures.append(structure)
            complex_type = ComplexType(structure.qualified_name, structure.name,
                                       ClassType.DATA_STRUCTURE)
            return complex_type

    def __handle_package_dependency(self, import_name: str):
        # TODO: May need to be adapted, when we don't map a microservice to
        #  exactly one context
        return self.__handle_project_dependency(import_name)

    def __handle_external_dependency(self, import_name: str):
        complex_type = ComplexType(import_name, import_name.split(".").pop(),
                                   ClassType.UNSPECIFIED)
        return complex_type

    def __check_for_dependency(self, import_name: str):
        context_name = self.__find_context_name(import_name)
        data_structure_name = import_name.split(".").pop()
        qualified_name = context_name + "." + data_structure_name.lower()
        context = next((c for c in self.contexts
                        if c.qualified_name == context_name), None)
        struct = next((s for s in context.data_structures
                       if s.qualified_name == qualified_name), None)
        if struct is not None:
            return True
        else:
            return False
