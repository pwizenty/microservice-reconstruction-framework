"""Detector for the HTTP clients of Spring: RestTemplate, RestClient, WebClient.

None of them states what it calls in a declaration. The address is a field the
service injects, or a literal somewhere in a method:

```java
@Value("${customercore.baseURL}")
private String customerCoreBaseURL;
…
restTemplate.getForObject(customerCoreBaseURL + "/customers/" + ids, …);
```

The address and the call are therefore found separately, and the unit of
detection is the class rather than the call site: a class that uses one of these
clients is reported as calling every address it injects or states. The parser
resolves no symbols (ADR-0003), so following a field into the argument of a
particular call is not possible, and a class that holds an address without the
field being the one that is called would be reported all the same. The evidence
names the line the address was read from, so the fact can be checked.
"""

from javalang.tree import CompilationUnit, Literal, ReferenceType, TypeDeclaration

from mrf.plugins.service.communication.detectors.detector import (
    DetectionContext,
    ServiceCall,
)
from mrf.plugins.service.communication.urls import evidence_for, service_call_from
from mrf.utilities.communication import (
    CLIENT_TYPES,
    MOCK_TYPES,
    VALUE_ANNOTATION,
    ArtifactType,
)
from mrf.utilities.java_utils import find_annotation, get_annotation_values

URL_MARKERS = ("http://", "https://", "${")


class RestClientDetector:
    """Reconstructs the calls a class makes with an HTTP client of Spring."""

    technology = "RestTemplate"

    def detect(
        self,
        clazz: TypeDeclaration,
        unit: CompilationUnit,
        context: DetectionContext,
    ) -> list[ServiceCall]:
        """Reconstruct the calls the class makes.

        Args:
            clazz: Parsed declaration of the class
            unit: Unit the class is declared in
            context: Path, lines and configuration of the analysed file

        Returns:
            [ServiceCall]: The calls that were found
        """
        technology = self.__client_type(clazz, unit)
        if technology is None or self.__uses_test_double(clazz, unit):
            return []

        calls = self.__from_injected_values(clazz, technology, context)
        calls.extend(self.__from_literals(clazz, technology, context))
        return calls

    def __client_type(
        self, clazz: TypeDeclaration, unit: CompilationUnit
    ) -> str | None:
        """Return the client type the class uses, or ``None``.

        The type is looked for in the imports and in every type the class names.
        A class that names none of them holds no call, however many URLs it
        states - a constant is not a call.
        """
        imported = {
            path.split(".")[-1]
            for imp in (unit.imports or [])
            for path in [imp.path or ""]
        }
        referenced = {
            node.name
            for _, node in clazz.filter(ReferenceType)
            if node.name is not None
        }
        for client_type in CLIENT_TYPES:
            if client_type in imported or client_type in referenced:
                return client_type
        return None

    def __uses_test_double(self, clazz: TypeDeclaration, unit: CompilationUnit) -> bool:
        """Check whether the class drives a mock server rather than a service."""
        imported = " ".join(imp.path or "" for imp in (unit.imports or []))
        referenced = {
            node.name
            for _, node in clazz.filter(ReferenceType)
            if node.name is not None
        }
        return any(mock in imported or mock in referenced for mock in MOCK_TYPES)

    def __from_injected_values(
        self, clazz: TypeDeclaration, technology: str, context: DetectionContext
    ) -> list[ServiceCall]:
        """Read the addresses the class injects with ``@Value``."""
        calls: list[ServiceCall] = []
        for field in getattr(clazz, "fields", None) or []:
            annotation = find_annotation(field.annotations or [], [VALUE_ANNOTATION])
            if annotation is None:
                continue
            values = get_annotation_values(annotation)
            address = values.get("value")
            if address is None:
                continue
            evidence = evidence_for(
                context.path,
                context.lines,
                self.__line_of(annotation),
                ArtifactType.SOURCE,
            )
            call = service_call_from(
                address, technology, evidence, context.configuration
            )
            if call is not None:
                calls.append(call)
        return calls

    def __from_literals(
        self, clazz: TypeDeclaration, technology: str, context: DetectionContext
    ) -> list[ServiceCall]:
        """Read the addresses the class states as literals."""
        calls: list[ServiceCall] = []
        for _, literal in clazz.filter(Literal):
            value = literal.value
            if not isinstance(value, str) or len(value) < 2:
                continue
            if not (value.startswith('"') and value.endswith('"')):
                continue
            text = value[1:-1]
            if not text.startswith(URL_MARKERS):
                continue
            evidence = evidence_for(
                context.path,
                context.lines,
                self.__line_of(literal),
                ArtifactType.SOURCE,
            )
            call = service_call_from(text, technology, evidence, context.configuration)
            if call is not None:
                calls.append(call)
        return calls

    def __line_of(self, node) -> int:
        position = getattr(node, "position", None)
        return position.line if position is not None else 0
