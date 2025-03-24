"""
Module of the Java plugin for reconstructing domain data information based of
Java source code artifacts. This plugin analyses annotations form the Spring
framework, e.g., @Entity or @SpringBootApplication to identify relevant
information.
"""

from typing import List

from javalang.tree import FieldDeclaration

from mrf.plugins.common.common_plugin import Data, JavaClassArtifact
from mrf.modules.domain_data import (
    UNKNOWN_CONTEXT,
    UNKNOWN_TYPE,
    Context,
    DataStructure,
    DDD_ENTITY,
    PrimitiveType,
    Field,
    ComplexType,
    ClassType,
    DDD_IDENTIFIER,
)
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.java_utils import (
    parse_java_file,
    has_annotation_for_class,
    get_class_from_tree,
    get_class_name,
    get_qualified_class_name,
    PRIMITIVE_JAVA_TYPES,
    get_field_name,
    match_context,
    resolve_complex_field,
    DependencyType,
    ImportType,
    has_annotation_for_field,
)
from mrf.utilities.sping import (
    CONTEXT_ANNOTATION,
    APPLICATION_CLASS,
    ENTITY_ANNOTATION,
    ID_ANNOTATIONS,
)
from mrf.utilities.sping import INFRASTRUCTURE_TECHNOLOGIES


class JavaPlugin(Plugin):
    """
    Main class of the Java plugin to reconstruct relevant information from the
    source code.
    """

    def __init__(self):
        self.java_classes: List[JavaClassArtifact] = []
        self.contexts: List[Context] = []

    def file_types(self):
        """
        Method to receives supported file types of the Java plugin.

        Returns: Suffix of supported file types.

        """
        return [".java"]

    def execute_reconstruction(self, source_files: list[SourceFile]) -> list[Context]:
        """
        Method that executes the functionalities of the Java plugin.

        Args:
            source_files (): Array of source files for the reconstruction
            process.

        Returns:
            contexts (Context): List of reconstructed domain data information.
        """
        self.__load_classes(source_files)
        for clazz in self.java_classes:
            context = self.__reconstruct_context(clazz)
            if context is not None:
                self.contexts.append(context)
        for clazz in self.java_classes:
            self.__reconstruct_entity(clazz)

        return self.contexts

    def __load_classes(self, source_files: list[SourceFile]):
        for s in source_files:
            if s.suffix in self.file_types():
                tree = parse_java_file(s.file)
                java_class = JavaClassArtifact(tree, s.path)
                self.java_classes.append(java_class)

    def __reconstruct_context(self, java_class: JavaClassArtifact) -> Context | None:
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation_for_class(clazz, CONTEXT_ANNOTATION):
            name = get_class_name(clazz).removesuffix(APPLICATION_CLASS)
            # Check if context is related to a Spring infrastructure technology
            if any(t in name.lower() for t in INFRASTRUCTURE_TECHNOLOGIES):
                return None
            qualified_name = (
                get_qualified_class_name(java_class.tree)
                .removesuffix(APPLICATION_CLASS.lower())
                .removesuffix("." + name.lower())
            )
            # Remove potential doubling name parts, e.g.,
            # "com.lakesidemutual.customercore.customercore" to
            # "com.lakesidemutual.customercore".
            context = Context(qualified_name, name, java_class.path)
            return context
        return None

    def __reconstruct_entity(self, java_class: JavaClassArtifact):
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation_for_class(clazz, ENTITY_ANNOTATION):
            structure = self.__reconstruct_data_structure(java_class)
            data = Data(DDD_ENTITY)
            structure.data.append(data)
            context_name = self.__find_context_name(structure.qualified_name)
            context = next(
                (c for c in self.contexts if c.qualified_name == context_name),
                self.__handle_unkown_context(),
            )
            context.data_structures.append(structure)

    def __reconstruct_data_structure(
        self, java_class: JavaClassArtifact
    ) -> DataStructure:
        clazz = get_class_from_tree(java_class.tree)
        name = get_class_name(clazz)
        qualified_name = get_qualified_class_name(java_class.tree)
        structure = DataStructure(qualified_name, name, java_class.path)
        primitive_fields = self.__reconstruct_primitive_type(clazz.fields)
        complex_fields = self.__reconstruct_complex_type(java_class)
        structure.fields.extend(primitive_fields)
        structure.fields.extend(complex_fields)
        return structure

    def __reconstruct_primitive_type(
        self, field_decs: list[FieldDeclaration]
    ) -> list[Field]:
        primitive_fields: List[Field] = []
        for f in field_decs:
            type = getattr(f, "type")
            if type.name.lower() in PRIMITIVE_JAVA_TYPES:
                field_type = type.name.lower()
                field_name = get_field_name(f)
                primitive_type = PrimitiveType(field_type)
                field = Field(field_name, primitive_type)

                if has_annotation_for_field(f, ID_ANNOTATIONS):
                    data = Data(DDD_IDENTIFIER)
                    field.data.append(data)
                primitive_fields.append(field)
        return primitive_fields

    def __reconstruct_complex_type(self, java_class: JavaClassArtifact) -> list[Field]:
        complex_fields: List[Field] = []
        clazz = get_class_from_tree(java_class.tree)

        for f in clazz.fields:
            type = getattr(f, "type")
            if type.name.lower() not in PRIMITIVE_JAVA_TYPES:
                result = resolve_complex_field(java_class.tree, type.name)
                complex_type = self.__handle_dependency(result)
                field_name = get_field_name(f)
                field = Field(field_name, complex_type)
                if has_annotation_for_field(f, ID_ANNOTATIONS):
                    data = Data(DDD_IDENTIFIER)
                    field.data.append(data)
                complex_fields.append(field)
        return complex_fields

    def __find_context_name(self, qualified_name: str) -> str:
        match_parts = []
        for context in self.contexts:
            parts = match_context(context.qualified_name, qualified_name)
            if len(match_parts) <= len(parts):
                match_parts = parts
        if len(match_parts) != 0:
            context_name = ".".join(match_parts)
            return context_name
        return UNKNOWN_CONTEXT

    def __handle_dependency(self, import_type: ImportType) -> ComplexType:
        match import_type.dependency_type:
            case DependencyType.PROJECT_DEPENDENCY:
                return self.__handle_project_dependency(
                    import_type.qualified_import_name
                )
            case DependencyType.PACKAGE_DEPENDENCY:
                return self.__handle_package_dependency(
                    import_type.qualified_import_name
                )
            case DependencyType.EXTERNAL_DEPENDENCY:
                return self.__handle_external_dependency(
                    import_type.qualified_import_name
                )
        return ComplexType(UNKNOWN_TYPE, UNKNOWN_TYPE, ClassType.UNSPECIFIED)

    def __handle_project_dependency(self, import_name: str) -> ComplexType:
        exist = self.__check_for_dependency(import_name)
        if exist is False:
            class_name = import_name.split(".").pop()
            java_class = next(
                (
                    java
                    for java in self.java_classes
                    if java.path.endswith(class_name + ".java")
                ),
            )

            structure = self.__reconstruct_data_structure(java_class)
            context_name = self.__find_context_name(structure.qualified_name)
            context = next(
                (c for c in self.contexts if c.qualified_name == context_name)
            )

            context.data_structures.append(structure)
            complex_type = ComplexType(
                structure.name, structure.qualified_name, ClassType.DATA_STRUCTURE
            )
            return complex_type
        type = ComplexType(UNKNOWN_TYPE, UNKNOWN_TYPE, ClassType.UNSPECIFIED)
        return type

    def __handle_package_dependency(self, import_name: str) -> ComplexType:
        # TODO: May need to be adapted, when we don't map a microservice to
        #  exactly one context
        return self.__handle_project_dependency(import_name)

    def __handle_external_dependency(self, import_name: str) -> ComplexType:
        complex_type = ComplexType(
            import_name, import_name.split(".").pop(), ClassType.UNSPECIFIED
        )
        return complex_type

    def __check_for_dependency(self, import_name: str) -> bool:
        context_name = self.__find_context_name(import_name)
        data_structure_name = import_name.split(".").pop()
        qualified_name = context_name + "." + data_structure_name.lower()
        context = next(
            (c for c in self.contexts if c.qualified_name == context_name), None
        )
        if context is None:
            return False
        else:
            struct = next(
                (
                    s
                    for s in context.data_structures
                    if s.qualified_name == qualified_name
                ),
                None,
            )
            return bool(struct)

    def __handle_unkown_context(self) -> Context:
        context = next(
            (c for c in self.contexts if c.qualified_name == UNKNOWN_CONTEXT), None
        )
        if context is None:
            return Context(UNKNOWN_CONTEXT, UNKNOWN_CONTEXT, None)
        else:
            return context
