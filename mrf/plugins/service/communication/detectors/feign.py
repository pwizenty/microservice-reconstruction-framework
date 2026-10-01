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

from mrf.plugins.common.spring_mapping import find_mapping
from mrf.plugins.service.communication.detectors.detector import (
    CalledEndpoint,
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
from mrf.utilities.sping import REQUEST_MAPPING, REST_OPERATIONS


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
        if call is None:
            return []
        call.endpoints.extend(self.__called_endpoints(clazz, context))
        return [call]

    def __called_endpoints(
        self, clazz: TypeDeclaration, context: DetectionContext
    ) -> list[CalledEndpoint]:
        """Read the endpoints the methods of a Feign client address.

        A Feign client declares what it calls the way a controller declares what
        it offers: the interface may carry a base path, and every method carries
        a mapping annotation with the rest of it. So the endpoints of the callee
        this client addresses are stated exactly, and need no analysis of a
        method body.

        Args:
            clazz: Parsed declaration of the client interface
            context: Path, lines and configuration of the analysed file

        Returns:
            [CalledEndpoint]: The endpoints the client addresses
        """
        annotations = getattr(clazz, "annotations", None) or []
        base = find_mapping(annotations, [REQUEST_MAPPING])
        base_path = base[1] if base is not None else None

        endpoints: list[CalledEndpoint] = []
        for method in getattr(clazz, "methods", None) or []:
            mapping = find_mapping(method.annotations or [], REST_OPERATIONS)
            if mapping is None:
                continue
            annotation, path = mapping
            position = getattr(annotation, "position", None)
            endpoints.append(
                CalledEndpoint(
                    verb=annotation.name,
                    path=self.__join(base_path, path),
                    method=method.name,
                    evidence=evidence_for(
                        context.path,
                        context.lines,
                        position.line if position is not None else 0,
                        ArtifactType.SOURCE,
                    ),
                )
            )
        return sorted(endpoints, key=lambda e: (e.path, e.verb, e.method))

    def __join(self, base: str | None, path: str | None) -> str:
        """Join the base path of the client with the path of one of its methods.

        Spring reads a method's path relative to the one of its declaration, and
        either may be absent: a client without a base path states absolute paths
        on its methods, and a method without a path addresses the base itself.
        """
        parts = [p.strip("/") for p in (base, path) if p]
        return "/" + "/".join(p for p in parts if p)
