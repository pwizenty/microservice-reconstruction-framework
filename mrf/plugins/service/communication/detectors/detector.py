"""Contract of a detector for one client technology.

A detector recognises the way one technology states the address of the service
it calls, and reports what it found as :class:`ServiceCall` facts. Adding a
technology is a module of its own plus an entry in
:data:`mrf.plugins.service.communication.detectors.DETECTORS`, so nothing else
has to change for it.
"""

from dataclasses import dataclass, field
from typing import Protocol

from javalang.tree import CompilationUnit, TypeDeclaration

from mrf.plugins.service.communication.configuration import ServiceConfiguration
from mrf.utilities.communication import ArtifactType, Scheme


@dataclass
class Evidence:
    """Where a fact was read.

    Attributes:
        file: Path of the artifact, relative to the analysed system
        line: Line the fact was read from, 1-based
        artifact_type: Kind of artifact
        snippet: The line itself, shortened
    """

    file: str
    line: int
    artifact_type: ArtifactType
    snippet: str


@dataclass
class CalledEndpoint:
    """One endpoint of another service that a client declares it addresses.

    Attributes:
        verb: Mapping annotation the client states, which is the HTTP verb
        path: Path the client addresses, the client's base path joined with the
            path of the method
        method: Name of the method that addresses it, for the evidence
        evidence: Where it was read
    """

    verb: str
    path: str
    method: str
    evidence: Evidence


@dataclass
class ServiceCall:
    """A call to another service, as the sources state it.

    The target is the host or service name the sources name. Whether it is a
    service of the system is decided by the plugin, which knows the
    reconstructed microservices; a detector reports what it read.

    Attributes:
        target: Host or service name the call addresses
        scheme: Transport of the call, :attr:`Scheme.UNRESOLVED` when it could
            not be determined
        technology: Client technology the call was found in
        evidence: Where the call was read
        port: Port of the target, when the URL names one
        property_name: Property the address came from, for a placeholder
        resolved_url: Address the placeholder resolved to
        profile: Spring profile the address was resolved for
        endpoints: Endpoints of the target the client declares it addresses.
            Empty when the technology does not state them, which is the case for
            every client that assembles its paths in the call expression.
    """

    target: str
    scheme: Scheme
    technology: str
    evidence: Evidence
    port: str | None = None
    property_name: str | None = None
    resolved_url: str | None = None
    profile: str | None = None
    endpoints: list[CalledEndpoint] = field(default_factory=list)


@dataclass
class MessageChannel:
    """A queue a service produces to or consumes from, as the sources state it.

    A fact of its own beside :class:`ServiceCall`: the evidence is a queue and
    a broker rather than a verb and a path, and the refactoring differs too -
    mutual TLS secures a call, a broker's ``ssl://`` secures a queue.

    The peer at the other end is not decided here. A detector reports which
    queue this service produces to or consumes from; pairing a producer with a
    consumer needs every service's facts and is the plugin's business.

    Attributes:
        role: ``producer`` or ``consumer``
        queue: Name of the queue, resolved against the service's configuration
        technology: Client technology the channel was found in
        evidence: Where it was read
        property_name: Property the queue name came from, for a placeholder
        resolved: Whether the queue name is known rather than a placeholder
            nothing resolves
    """

    role: str
    queue: str
    technology: str
    evidence: Evidence
    property_name: str | None = None
    resolved: bool = True


@dataclass
class DetectionContext:
    """What a detector needs beside the parsed class.

    Attributes:
        path: Path of the analysed file, relative to the analysed system
        lines: Lines of the file, for the evidence of a fact
        configuration: Configuration of the service the file belongs to, or
            ``None`` when the service has none
    """

    path: str
    lines: list[str] = field(default_factory=list)
    configuration: ServiceConfiguration | None = None


class MessagingDetector(Protocol):
    """Detector for the queues one messaging technology uses.

    Separate from :class:`ClientDetector` because it reports a different fact.
    A technology is added as a module plus an entry in
    :data:`mrf.plugins.service.communication.detectors.MESSAGING_DETECTORS`.
    """

    technology: str

    def detect(
        self,
        clazz: TypeDeclaration,
        unit: CompilationUnit,
        context: DetectionContext,
    ) -> list[MessageChannel]:
        """Reconstruct the queues a class produces to or consumes from.

        Args:
            clazz: Parsed declaration of the class
            unit: Unit the class is declared in
            context: Path, lines and configuration of the analysed file

        Returns:
            The channels that were found, empty when the class uses none
        """
        ...


class ClientDetector(Protocol):
    """Detector for the calls one client technology makes."""

    technology: str

    def detect(
        self,
        clazz: TypeDeclaration,
        unit: CompilationUnit,
        context: DetectionContext,
    ) -> list[ServiceCall]:
        """Reconstruct the calls a class makes with this technology.

        Args:
            clazz: Parsed declaration of the class
            unit: Unit the class is declared in
            context: Path, lines and configuration of the analysed file

        Returns:
            The calls that were found, empty when the class makes none
        """
        ...
