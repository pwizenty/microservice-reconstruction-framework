"""
Module with class and methods to reconstruction microservices from Java based
source code artifacts.
"""
from copy import deepcopy
from typing import List

from dataclasses import dataclass
from javalang.tree import (
    Annotation,
    CompilationUnit,
    FormalParameter,
    MethodDeclaration,
    ReferenceType,
)

from mrf.modules.domain_data import ClassType, ComplexType, PrimitiveType
from mrf.modules.service import (
    MICROSERVICE_FUNCTIONAL,
    MICROSERVICE_PUBLIC,
    CommunicationType,
    ExchangePattern,
    Interface,
    Microservice,
    Operation,
    Parameter,
)
from mrf.plugins.common.common_plugin import Data, JavaClassArtifact
from mrf.plugins.reconstruction_plugin import Plugin
from mrf.utilities.command_line import SourceFile
from mrf.utilities.java_utils import (
    PRIMITIVE_JAVA_TYPES,
    get_class_from_tree,
    get_class_name,
    get_qualified_class_name,
    has_annotation,
    load_classes,
    match_microservice_interface,
    resolve_complex_field, TECHNOLOGY_SPRING_TYPES,
)
from mrf.utilities.sping import (
    APPLICATION_CLASS,
    CONTROLLER_CLASS,
    INFRASTRUCTURE_TECHNOLOGIES,
    REST_CONTROLLER,
    REST_OPERATIONS,
    SPRING_BOOT_APPLICATION,
)
from utilities.java_utils import COLLECTION_TYPES, adjust_qualified_name


@dataclass
class SpringReconstructionResult:
    microservices: list[Microservice]
    complex_types: list[ComplexType]

class SpringPlugin(Plugin):
    """
    Class Plugin for recovering microservices from source code written in Java using
    the Spring framework.
    """

    def __init__(self):
        self.java_classes: List[JavaClassArtifact] = []
        self.microservices: List[Microservice] = []
        self.complex_types: List[ComplexType] = []
        self.name: str

    def file_types(self):
        """
        Return the type of files that are supported by the Spring plugin.

        Returns: list of supported file types.

        """
        return [".java"]

    def execute_reconstruction(
        self, source_files: list[SourceFile]
    ) -> SpringReconstructionResult:
        """
        Execute the reconstruction functionality of the Spring plugin.

        Args:
            source_files ():

        Returns:

        """
        print("Test Spring Plugin")
        self.java_classes.extend(load_classes(source_files, self.file_types()))
        # Reconstruct microservices
        for clazz in self.java_classes:
            microservice = self.__reconstruct_microservice(clazz)
            if microservice is not None:
                self.microservices.append(microservice)

        # Reconstruct interfaces
        for clazz in self.java_classes:
            self.__reconstruct_interface(clazz)

        return SpringReconstructionResult(self.microservices, self.complex_types)

    def __reconstruct_microservice(
        self, java_class: JavaClassArtifact
    ) -> Microservice | None:
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation(clazz, [SPRING_BOOT_APPLICATION]):
            name = get_class_name(clazz).removesuffix(APPLICATION_CLASS)
            if any(t in name.lower() for t in INFRASTRUCTURE_TECHNOLOGIES):
                return None
            qualified_name = (
                get_qualified_class_name(java_class.tree)
                .removesuffix(APPLICATION_CLASS)
                #.removesuffix("." + name.lower())
            )
            microservice = Microservice(qualified_name, name, java_class.path)
            public_data = Data(MICROSERVICE_PUBLIC)
            functional_data = Data(MICROSERVICE_FUNCTIONAL)
            microservice.data.append(public_data)
            microservice.data.append(functional_data)
            return microservice
        return None

    def __reconstruct_interface(
        self, java_class: JavaClassArtifact
    ) -> Interface | None:
        clazz = get_class_from_tree(java_class.tree)
        if has_annotation(clazz, [REST_CONTROLLER]):
            name = get_class_name(clazz).removesuffix(CONTROLLER_CLASS)
            qualified_name = get_qualified_class_name(java_class.tree).removesuffix(
                CONTROLLER_CLASS
            )
            interface = Interface(qualified_name, name)
            service = next(
                microservice
                for microservice in self.microservices
                if match_microservice_interface(
                    microservice.qualified_name, interface.qualified_name
                )
            )

            # Reconstruct Operations

            for method in clazz.methods:
                if has_annotation(method, REST_OPERATIONS):
                    operation = self.__reconstruct_operation(method, java_class.tree)
                    interface.operations.append(operation)

            interface.qualified_name = adjust_qualified_name(service.qualified_name, interface.qualified_name)
            service.interfaces.append(interface)

    def __reconstruct_operation(
        self, method: MethodDeclaration, unit: CompilationUnit
    ) -> Operation:
        print("")
        name = getattr(method, "name")
        operation = Operation(name)
        annotations = getattr(method, "annotations")
        operation.data.extend(self.__handle_annotations(annotations))

        return_type = getattr(method, "return_type")
        formal_parameters = getattr(method, "parameters")

        operation.parameters.extend(self.__handle_parameters(formal_parameters, unit))
        if return_type != "void":
            operation.parameters.append(self.__handle_return_type(return_type, unit))

        return operation

    def __handle_annotations(self, annotations: list[Annotation]) -> List[Data]:
        data: list[Data] = []
        for annotation in annotations:
            annotation_data = self.__handle_annotation(annotation)
            if annotation_data is not None:
                data.append(annotation_data)
        return data

    def __handle_annotation(self, annotation: Annotation) -> Data | None:
        name = getattr(annotation, "name")
        if name in REST_OPERATIONS:
            data = Data(name)
            return data
        return None

    def __handle_parameters(
        self, formal_parameters: list[FormalParameter], unit: CompilationUnit
    ) -> List[Parameter]:
        parameters: list[Parameter] = []
        for parameter in formal_parameters:
            parameters.append(self.__handle_parameter(parameter, unit))
        return parameters

    def __handle_parameter(
        self,
        formal_parameter: FormalParameter,
        unit: CompilationUnit
    ) -> Parameter:
        name = getattr(formal_parameter, "name")
        com_type = CommunicationType.SYNCHRONOUS
        exch_pat = ExchangePattern.IN
        parameter_type = getattr(formal_parameter, "type")
        type = self.__handle_parameter_type(parameter_type, unit)
        parameter = Parameter(name, com_type, exch_pat, type)
        return parameter

    def __handle_return_type(
        self, reference_type: ReferenceType, unit: CompilationUnit
    ) -> Parameter:
        name = getattr(reference_type, "name")

        if reference_type.name.lower() in TECHNOLOGY_SPRING_TYPES:
            return self.__handle_specific_return_type(reference_type, unit)
        else:
            com_type = CommunicationType.SYNCHRONOUS
            exch_pat = ExchangePattern.OUT
            type = self.__handle_parameter_type(reference_type, unit)
            return Parameter(name, com_type, exch_pat, type)

    def __handle_specific_return_type(self, reference_type: ReferenceType, unit: CompilationUnit) -> Parameter:
        arguments = getattr(reference_type, "arguments")
        com_type = CommunicationType.SYNCHRONOUS
        exch_pat = ExchangePattern.OUT
        if arguments is not None:
            parameter_ref_type = getattr(arguments[0], "type")
            p_type = self.__handle_parameter_type(parameter_ref_type, unit)
            parameter = Parameter(p_type.name, com_type, exch_pat, p_type)
            data = Data(getattr(reference_type, "name"))
            parameter.data.append(data)
            return parameter
        else:
            p_type = self.__handle_parameter_type(reference_type, unit)
            parameter = Parameter(p_type.name, com_type, exch_pat, p_type)
            return parameter

    def __handle_parameter_type(
        self, reference_type: ReferenceType, unit: CompilationUnit
    ) -> ComplexType | PrimitiveType:
        name = getattr(reference_type, "name")
        if name.lower() in PRIMITIVE_JAVA_TYPES:
            return self.__handle_primitive_type(name)
        else:
            return self.__handle_complex_type(reference_type, unit)

    def __handle_primitive_type(self, name: str) -> PrimitiveType:
        return PrimitiveType(name)

    def __handle_complex_type(
        self, reference_type: ReferenceType, unit: CompilationUnit
    ) -> ComplexType:
        class_type = ClassType.DATA_STRUCTURE
        if reference_type.name.lower() in COLLECTION_TYPES:
            class_type = ClassType.COLLECTION
            arguments = getattr(reference_type, "arguments")
            reference_type = getattr(arguments[0], "type")
            print()

        name = getattr(reference_type, "name")
        import_type = resolve_complex_field(unit, name)
        complex_type = ComplexType(
            name, import_type.qualified_import_name, class_type
        )
        qualified_name = self.__find_microservice(complex_type.qualified_name)
        complex_type.qualified_name = adjust_qualified_name(qualified_name, complex_type.qualified_name)
        if complex_type.class_type is ClassType.COLLECTION:
            complex_type_list = deepcopy(complex_type)
            complex_type.class_type = ClassType.DATA_STRUCTURE
            complex_type_list.name = complex_type.name + "List"
            complex_type_list.qualified_name = complex_type.qualified_name + "List"
            if name.lower() not in PRIMITIVE_JAVA_TYPES:
                self.complex_types.append(complex_type)
            self.complex_types.append(complex_type_list)
            return complex_type_list

        self.complex_types.append(complex_type)
        return complex_type

    def __find_microservice(self, complex_type_qualified_name: str):
        for ms in self.microservices:
            if (
                    complex_type_qualified_name == ms.qualified_name.removesuffix(ms.name)
                    or complex_type_qualified_name.startswith(ms.qualified_name.removesuffix(ms.name))
            ):
                return ms.qualified_name
        return None