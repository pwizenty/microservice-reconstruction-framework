from typing import List

from javalang.tree import CompilationUnit, FieldDeclaration

from mrf.plugins.common.common_plugin import Data
from mrf.plugins.data.domain_data import Context, DataStructure, DDD_ENTITY, PrimitiveType, Field
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.java_utils import parse_java_file, has_annotation, get_class_from_tree, get_class_name, \
    get_qualified_class_name, PRIMITIVE_JAVA_TYPES, get_field_name, match_context
from mrf.utilities.sping import CONTEXT_ANNOTATION, APPLICATION_CLASS, ENTITY_ANNOTATION
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
            self.__reconstruct_data_structure(c)

        return "Execute Reconstruction - Java Plugin"

    def __load_classes(self, source_files: list[SourceFile]):
        for s in source_files:
            if s.suffix in self.file_types():
                tree = parse_java_file(s.file)
                java_class = JavaClassArtefact(tree, s.path)
                self.java_classes.append(java_class)

    def __reconstruct_context(self, java_class: JavaClassArtefact):
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation(clazz, CONTEXT_ANNOTATION):
            name = get_class_name(clazz).removesuffix(APPLICATION_CLASS)
            # Check if context is related to a Spring infrastructure technology
            if any(t in name.lower() for t in INFRASTRUCTURE_TECHNOLOGIES):
                return None
            qualified_name = (get_qualified_class_name(java_class.tree)
                              .removesuffix(APPLICATION_CLASS.lower())
                              .removesuffix("." + name.lower()))
            # Remove potential doubling name parts, e.g., "com.lakesidemutual.customercore.customercore"
            # to "com.lakesidemutual.customercore".
            context = Context(qualified_name, name, java_class.path)
            self.contexts.append(context)

    def __reconstruct_data_structure(self, java_class: JavaClassArtefact):
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation(clazz, ENTITY_ANNOTATION):
            name = get_class_name(clazz)
            qualified_name = get_qualified_class_name(java_class.tree)
            structure = DataStructure(qualified_name, name, java_class.path)
            data = Data(DDD_ENTITY)
            structure.data.append(data)
            primitive_fields = self.__reconstruct_primitive_type(clazz.fields)
            structure.fields.extend(primitive_fields)
            context_name = self.__find_context_name(qualified_name)
            self.__assign_to_structure_to_context(structure, context_name)

    def __reconstruct_primitive_type(self, field_declarations: [FieldDeclaration]):
        primitive_fields: List[Field] = []
        for f in field_declarations:
            if f.type.name.lower() in PRIMITIVE_JAVA_TYPES:
                field_type = f.type.name
                field_name = get_field_name(f)
                primitive_type = PrimitiveType(field_type)
                field = Field(field_name, primitive_type)
                primitive_fields.append(field)
        return primitive_fields

    def __find_context_name(self, qualified_name: str):
        match_parts = []
        for context in self.contexts:
            context_parts = match_context(context.qualified_name, qualified_name)
            if len(match_parts) <= len(context_parts):
                match_parts = context_parts
        if len(match_parts) != 0:
            context_name = ".".join(match_parts)
            return context_name
        else:
            return None

    def __assign_to_structure_to_context(self, data_structure: DataStructure, context_name):
        if context_name is not None:
            context = next((context for context in self.contexts if context.qualified_name == context_name), None)
            context.data_structures.append(data_structure)
            print()
        else:
            # TODO: Handling function to support DataStructures without context. 
            pass
