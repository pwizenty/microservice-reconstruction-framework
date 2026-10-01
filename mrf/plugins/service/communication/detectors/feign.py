"""Detector for a client declared with Spring Cloud's ``@FeignClient``.

A Feign client states what it calls on the annotation of the interface, so the
address and the service name are both there and need no analysis of a method
body:

```java
@FeignClient(name="customercore", url="${customercore.baseURL}")
public interface CustomerCoreClient { … }
```

``url`` may be absent, in which case the address comes from service discovery
under ``name`` and the transport is not stated in the sources.
"""

from javalang.tree import CompilationUnit, TypeDeclaration

from mrf.plugins.service.communication.detectors.detector import (
    DetectionContext,
    ServiceCall,
)
from mrf.plugins.service.communication.urls import evidence_for, service_call_from
from mrf.utilities.communication import (
    FEIGN_CLIENT,
    FEIGN_NAME_ELEMENT,
    FEIGN_URL_ELEMENT,
    ArtifactType,
    Scheme,
)
from mrf.utilities.java_utils import find_annotation, get_annotation_values


class FeignDetector:
    """Reconstructs the call a ``@FeignClient`` interface declares."""

    technology = "Feign"

    def detect(
        self,
        clazz: TypeDeclaration,
        unit: CompilationUnit,
        context: DetectionContext,
    ) -> list[ServiceCall]:
        """Reconstruct the call the annotation of the class declares.

        Args:
            clazz: Parsed declaration of the class
            unit: Unit the class is declared in
            context: Path, lines and configuration of the analysed file

        Returns:
            [ServiceCall]: The declared call, or an empty list
        """
        annotations = getattr(clazz, "annotations", None) or []
        annotation = find_annotation(annotations, [FEIGN_CLIENT])
        if annotation is None:
            return []

        values = get_annotation_values(annotation)
        name = values.get(FEIGN_NAME_ELEMENT)
        url = values.get(FEIGN_URL_ELEMENT)
        line = getattr(annotation, "position", None)
        evidence = evidence_for(
            context.path,
            context.lines,
            line.line if line is not None else 0,
            ArtifactType.SOURCE,
        )

        if url is None:
            # Discovery by name: the sources state no transport at all.
            if name is None:
                return []
            return [
                ServiceCall(
                    target=name,
                    scheme=Scheme.UNRESOLVED,
                    technology=self.technology,
                    evidence=evidence,
                )
            ]

        call = service_call_from(
            url, self.technology, evidence, context.configuration, fallback_target=name
        )
        return [call] if call is not None else []
