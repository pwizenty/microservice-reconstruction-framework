"""Spring plugin reconstructing microservices and their REST interfaces.

Analyses Java source code artifacts for annotations of the Spring framework,
e.g., @SpringBootApplication or @RestController.
"""

from copy import deepcopy
from dataclasses import dataclass

from javalang.tree import (
    Annotation,
    CompilationUnit,
    FormalParameter,
    MethodDeclaration,
    ReferenceType,
)

from mrf.modules.domain_data import (
    UNKNOWN_CONTEXT,
    ClassType,
    ComplexType,
    PrimitiveType,
)
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
    COLLECTION_TYPES,
    PRIMITIVE_JAVA_TYPES,
    TECHNOLOGY_SPRING_TYPES,
    VOID_TYPES,
    adjust_qualified_name,
    find_annotation,
    get_annotation_values,
    get_class_from_tree,
    get_class_name,
    get_qualified_class_name,
    has_annotation,
    load_classes,
    match_microservice_interface,
    resolve_complex_field,
)
from mrf.utilities.sping import (
    APPLICATION_CLASS,
    CONTROLLER_CLASS,
    ENDPOINT,
    ENDPOINT_ADDRESS,
    INFRASTRUCTURE_ANNOTATIONS,
    INFRASTRUCTURE_TECHNOLOGIES,
    MAPPING_PATH_ELEMENTS,
    OPERATION_ANNOTATIONS,
    PARAMETER_ANNOTATIONS,
    REQUEST_MAPPING,
    REST_CONTROLLER,
    REST_OPERATIONS,
    SPRING_BOOT_APPLICATION,
)


@dataclass
class SpringReconstructionResult:
    """Result of a run of the :class:`SpringPlugin`.

    Attributes:
        microservices ([Microservice]): Reconstructed microservices
        complex_types ([ComplexType]): Complex types used by their operations
    """

    microservices: list[Microservice]
    complex_types: list[ComplexType]


class SpringPlugin(Plugin):
    """Plugin recovering microservices from Java source code using Spring."""

    def __init__(self):
        self.java_classes: list[JavaClassArtifact] = []
        self.microservices: list[Microservice] = []
        self.complex_types: list[ComplexType] = []
        self.name: str

    def file_types(self):
        """Return the type of files that are supported by the Spring plugin.

        Returns: list of supported file types.

        """
        return [".java"]

    def execute_reconstruction(
        self, source_files: list[SourceFile]
    ) -> SpringReconstructionResult:
        """Execute the reconstruction functionality of the Spring plugin.

        Args:
            source_files ([SourceFile]): Source files of the analysed system

        Returns:
            SpringReconstructionResult: Reconstructed microservices and the
            complex types used by their operations
        """
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
            # Infrastructure runs the system rather than belonging to its
            # domain, so it is neither a context nor a microservice. The
            # operation phase reconstructs it as an infrastructure node.
            if has_annotation(clazz, INFRASTRUCTURE_ANNOTATIONS) or any(
                t in name.lower() for t in INFRASTRUCTURE_TECHNOLOGIES
            ):
                return None
            qualified_name = (
                get_qualified_class_name(java_class.tree).removesuffix(
                    APPLICATION_CLASS
                )
                # .removesuffix("." + name.lower())
            )
            microservice = Microservice(qualified_name, name, java_class.path)
            public_data = Data(MICROSERVICE_PUBLIC)
            functional_data = Data(MICROSERVICE_FUNCTIONAL)
            microservice.data.append(public_data)
            microservice.data.append(functional_data)
            return microservice
        return None

    def __reconstruct_interface(self, java_class: JavaClassArtifact) -> None:
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

            # The path of the controller is the endpoint all of its operations
            # are addressed below.
            endpoint = self.__reconstruct_endpoint(clazz.annotations, [REQUEST_MAPPING])
            if endpoint is not None:
                interface.data.append(endpoint)

            # Reconstruct Operations

            for method in clazz.methods:
                if has_annotation(method, REST_OPERATIONS):
                    operation = self.__reconstruct_operation(method, java_class.tree)
                    interface.operations.append(operation)

            interface.qualified_name = adjust_qualified_name(
                service.qualified_name, interface.qualified_name
            )
            service.interfaces.append(interface)

    def __reconstruct_operation(
        self, method: MethodDeclaration, unit: CompilationUnit
    ) -> Operation:
        name = method.name
        operation = Operation(name)
        annotations = method.annotations
        operation.data.extend(self.__handle_annotations(annotations))

        return_type = method.return_type
        formal_parameters = method.parameters

        operation.parameters.extend(self.__handle_parameters(formal_parameters, unit))
        return_parameter = self.__handle_return_type(return_type, unit)
        if return_parameter is not None:
            operation.parameters.append(return_parameter)

        return operation

    def __handle_annotations(self, annotations: list[Annotation]) -> list[Data]:
        """Reconstruct the technology information of an operation.

        The annotation that makes the method an operation is reported under its
        own name, together with the further annotations of the operation the
        technology model declares. Its path is no annotation but an endpoint,
        so it is reported separately, see :func:`__reconstruct_endpoint`.

        Args:
            annotations ([Annotation]): Annotations of the method

        Returns:
            [Data]: Meta-data of the operation
        """
        data: list[Data] = []
        for annotation in annotations:
            annotation_data = self.__handle_annotation(annotation)
            if annotation_data is not None:
                data.append(annotation_data)

        endpoint = self.__reconstruct_endpoint(
            annotations, [*REST_OPERATIONS, REQUEST_MAPPING]
        )
        if endpoint is not None:
            data.append(endpoint)
        return data

    def __handle_annotation(self, annotation: Annotation) -> Data | None:
        name = annotation.name
        if name in REST_OPERATIONS:
            # A mapping annotation is declared as an aspect without properties,
            # so its elements - the path - do not belong to it.
            return Data(name)
        if name in OPERATION_ANNOTATIONS:
            data = Data(name)
            data.values = get_annotation_values(annotation)
            return data
        return None

    def __reconstruct_endpoint(
        self, annotations: list[Annotation], names: list[str]
    ) -> Data | None:
        """Reconstruct the endpoint one of the given annotations addresses.

        Spring writes the path of a controller or of a method into the mapping
        annotation, and LEMMA writes it as the address of an endpoint. Both
        read an address relative to the element above it, so the path is
        carried over unchanged.

        Args:
            annotations ([Annotation]): Annotations of the class or method
            names ([str]): Names of the annotations that may hold a path

        Returns:
            Data | None: The endpoint, or ``None`` when none of the annotations
                is there or holds a path, as for a bare ``@GetMapping``
        """
        annotation = find_annotation(annotations, names)
        if annotation is None:
            return None

        values = get_annotation_values(annotation)
        address = next(
            (values[element] for element in MAPPING_PATH_ELEMENTS if element in values),
            None,
        )
        if not address:
            return None

        endpoint = Data(ENDPOINT)
        endpoint.values = {ENDPOINT_ADDRESS: address}
        return endpoint

    def __handle_parameters(
        self, formal_parameters: list[FormalParameter], unit: CompilationUnit
    ) -> list[Parameter]:
        parameters: list[Parameter] = []
        for parameter in formal_parameters:
            parameters.append(self.__handle_parameter(parameter, unit))
        return parameters

    def __handle_parameter(
        self, formal_parameter: FormalParameter, unit: CompilationUnit
    ) -> Parameter:
        name = formal_parameter.name
        com_type = CommunicationType.SYNCHRONOUS
        exch_pat = ExchangePattern.IN
        parameter_type = formal_parameter.type
        type = self.__handle_parameter_type(parameter_type, unit)
        parameter = Parameter(name, com_type, exch_pat, type)
        parameter.data.extend(
            self.__handle_parameter_annotations(formal_parameter.annotations)
        )
        return parameter

    def __handle_parameter_annotations(
        self, annotations: list[Annotation]
    ) -> list[Data]:
        """Reconstruct the technology information of a parameter.

        Only the annotations the technology model declares as aspects for a
        parameter are carried over. Spring's controllers also carry the
        annotations of an OpenAPI description, which no aspect of the model
        declares and which say nothing about the architecture.

        Args:
            annotations ([Annotation]): Annotations of the formal parameter

        Returns:
            [Data]: Meta-data of the parameter
        """
        data: list[Data] = []
        for annotation in annotations:
            if annotation.name not in PARAMETER_ANNOTATIONS:
                continue
            annotation_data = Data(annotation.name)
            annotation_data.values = get_annotation_values(annotation)
            data.append(annotation_data)
        return data

    def __handle_return_type(
        self, reference_type: ReferenceType | None, unit: CompilationUnit
    ) -> Parameter | None:
        """Reconstruct the outgoing parameter of an operation.

        An operation that returns nothing has none. The parser reports the
        primitive ``void`` as the plain string ``"void"`` rather than a type,
        and Spring expresses the same through ``ResponseEntity<Void>``.

        Args:
            reference_type (ReferenceType | None): Return type of the method
            unit (CompilationUnit): Unit the method is declared in

        Returns:
            Parameter | None: The outgoing parameter, or ``None`` when the
                operation returns nothing
        """
        if reference_type is None or self.__is_void(reference_type):
            return None

        name = reference_type.name

        if reference_type.name.lower() in TECHNOLOGY_SPRING_TYPES:
            return self.__handle_specific_return_type(reference_type, unit)
        else:
            com_type = CommunicationType.SYNCHRONOUS
            exch_pat = ExchangePattern.OUT
            type = self.__handle_parameter_type(reference_type, unit)
            return Parameter(name, com_type, exch_pat, type)

    def __handle_specific_return_type(
        self, reference_type: ReferenceType, unit: CompilationUnit
    ) -> Parameter | None:
        arguments = reference_type.arguments
        com_type = CommunicationType.SYNCHRONOUS
        exch_pat = ExchangePattern.OUT
        if arguments is not None:
            parameter_ref_type = arguments[0].type
            # ResponseEntity<Void> is a response without a body, so the
            # operation returns nothing.
            if self.__is_void(parameter_ref_type):
                return None
            p_type = self.__handle_parameter_type(parameter_ref_type, unit)
            parameter = Parameter(p_type.name, com_type, exch_pat, p_type)
            data = Data(reference_type.name)
            parameter.data.append(data)
            return parameter
        else:
            p_type = self.__handle_parameter_type(reference_type, unit)
            parameter = Parameter(p_type.name, com_type, exch_pat, p_type)
            return parameter

    def __is_void(self, reference_type) -> bool:
        """Check whether a return type expresses the absence of a value.

        The parser reports the primitive ``void`` as a plain string and every
        other return type as a node carrying a name, so both shapes reach
        here.
        """
        if reference_type is None:
            return True
        name = (
            reference_type
            if isinstance(reference_type, str)
            else getattr(reference_type, "name", "")
        )
        return name.lower() in VOID_TYPES

    def __handle_parameter_type(
        self, reference_type: ReferenceType, unit: CompilationUnit
    ) -> ComplexType | PrimitiveType:
        name = reference_type.name
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
            arguments = reference_type.arguments
            reference_type = arguments[0].type

        name = reference_type.name
        import_type = resolve_complex_field(unit, name)
        complex_type = ComplexType(name, import_type.qualified_import_name, class_type)
        qualified_name = self.__find_microservice(complex_type.qualified_name)
        complex_type.qualified_name = adjust_qualified_name(
            qualified_name, complex_type.qualified_name
        )
        if qualified_name == UNKNOWN_CONTEXT and class_type is not ClassType.COLLECTION:
            # The type belongs to none of the reconstructed microservices, e.g.
            # a framework class such as ResponseEntity. Reporting it as a data
            # structure would claim a domain data model that does not exist.
            complex_type.class_type = ClassType.UNSPECIFIED
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

    def __find_microservice(self, complex_type_qualified_name: str) -> str:
        """Find the microservice a complex type belongs to.

        Args:
            complex_type_qualified_name (str): Qualified name of the type

        Returns:
            str: Qualified name of the owning microservice, or
                :data:`UNKNOWN_CONTEXT` for a type that belongs to none of the
                reconstructed microservices, e.g. a framework type such as
                ``ResponseEntity``.
        """
        for ms in self.microservices:
            if complex_type_qualified_name == ms.qualified_name.removesuffix(
                ms.name
            ) or complex_type_qualified_name.startswith(
                ms.qualified_name.removesuffix(ms.name)
            ):
                return ms.qualified_name
        return UNKNOWN_CONTEXT
