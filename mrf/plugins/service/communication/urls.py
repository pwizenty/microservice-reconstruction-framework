"""Reading a URL that a client states, and the evidence for it.

Shared by the detectors: every technology states an address eventually, whether
on an annotation or in a field, and all of them need the same reading of it.
"""

from urllib.parse import urlsplit

from mrf.plugins.service.communication.configuration import (
    ServiceConfiguration,
    is_placeholder,
    split_placeholder,
)
from mrf.plugins.service.communication.detectors.detector import Evidence, ServiceCall
from mrf.utilities.communication import (
    ARTIFACT_TYPE,
    SCHEMA_HOSTS,
    SNIPPET_LENGTH,
    ArtifactType,
    Scheme,
)

__all__ = ["ARTIFACT_TYPE", "evidence_for", "service_call_from"]

KNOWN_SCHEMES = {"http": Scheme.HTTP, "https": Scheme.HTTPS}


def evidence_for(
    path: str, lines: list[str], line: int, artifact_type: ArtifactType
) -> Evidence:
    """Build the evidence of a fact found in a file at a line.

    Args:
        path: Path of the artifact
        lines: Lines of the artifact
        line: Line the fact was read from, 1-based
        artifact_type: Kind of artifact

    Returns:
        Evidence: The evidence, with the line shortened to a snippet
    """
    snippet = ""
    if 1 <= line <= len(lines):
        snippet = lines[line - 1].strip()[:SNIPPET_LENGTH]
    return Evidence(path, line, artifact_type, snippet)


def is_schema_url(value: str) -> bool:
    """Check whether a URL identifies an XML namespace rather than a service.

    ``http://www.w3.org/2001/XMLSchema`` is an identifier that happens to look
    like an address, and a system is full of them.
    """
    host = urlsplit(value.strip()).hostname
    return host is not None and host.lower() in SCHEMA_HOSTS


def service_call_from(
    value: str,
    technology: str,
    evidence: Evidence,
    configuration: ServiceConfiguration | None,
    fallback_target: str | None = None,
) -> ServiceCall | None:
    """Read a call from the address a client states.

    The address is either a URL or a placeholder. A placeholder is resolved
    against the service's own configuration; when nothing defines it the call is
    still reported, with :attr:`Scheme.UNRESOLVED`, because a call whose
    transport is unknown is a fact and guessing one would not be.

    Args:
        value: Address as the sources state it
        technology: Client technology it was found in
        evidence: Where it was read
        configuration: Configuration of the calling service, or ``None``
        fallback_target: Target to report when the address resolves to nothing,
            such as the service name of a Feign client

    Returns:
        ServiceCall | None: The call, or ``None`` when the value addresses
            nothing - an empty address, or an XML namespace
    """
    address = value.strip()
    if not address:
        return None

    property_name: str | None = None
    profile: str | None = None
    if is_placeholder(address):
        property_name, _ = split_placeholder(address)
        resolved = None
        if configuration is not None:
            resolved, profile, property_name = configuration.resolve(address)
        if resolved is None:
            if fallback_target is None:
                return None
            return ServiceCall(
                target=fallback_target,
                scheme=Scheme.UNRESOLVED,
                technology=technology,
                evidence=evidence,
                property_name=property_name,
                profile=profile,
            )
        address = resolved

    if is_schema_url(address):
        return None

    parts = urlsplit(address)
    scheme = KNOWN_SCHEMES.get(parts.scheme.lower())
    if scheme is None:
        # Neither a URL nor a placeholder - a path, or a value assembled
        # somewhere this analysis cannot follow.
        if fallback_target is None:
            return None
        return ServiceCall(
            target=fallback_target,
            scheme=Scheme.UNRESOLVED,
            technology=technology,
            evidence=evidence,
            property_name=property_name,
            profile=profile,
        )

    host = parts.hostname or fallback_target
    if host is None:
        return None

    return ServiceCall(
        target=host,
        scheme=scheme,
        technology=technology,
        evidence=evidence,
        port=str(parts.port) if parts.port is not None else None,
        property_name=property_name,
        resolved_url=address,
        profile=profile,
    )
