"""What the JavaScript of a Node service says about a channel's transport.

The manifest and the configuration of a Node service name an address; whether
the channel to it is encrypted is decided in the code that opens it. ``nconf``
reads a configuration that has no schema, and no library writes the transport
into it - ``grpc.ServerCredentials.createInsecure()`` is a call, not a property.
So without reading the sources the fact stays unresolved, and that is what kept
the two channels of Lakeside Mutual's Risk Management server out of the
generated models and out of the detection.

Read by name rather than parsed, as the weakened-verification facts of the Java
side are (``docs/backlog.md`` A2): the names are API of the libraries, a call to
one of them is the evidence, and nothing here needs a JavaScript grammar. That
is also its limit - a name reached through an alias or assembled at runtime is
not seen, and is reported as unresolved rather than as plaintext.

The values are those of :class:`mrf.utilities.communication.Transport`, so a
Node fact and a Spring fact state the same thing in the same words.
"""

import logging
from dataclasses import dataclass

from mrf.utilities.communication import Transport
from mrf.utilities.node import (
    CLIENT_AUTH_REQUIRED,
    GRPC_CLIENT_AUTH_ARGUMENT,
    INSECURE_GRPC_SERVER,
    MESSAGING_ANCHOR,
    MESSAGING_WINDOW,
    SECURE_GRPC_SERVER,
    SSL_OPTION,
    TLS_URL_SCHEMES,
)

logger = logging.getLogger(__name__)


@dataclass
class TransportEvidence:
    """What the sources of a service state about one channel.

    Attributes:
        transport: A value of :class:`mrf.utilities.communication.Transport`
        client_auth: ``need`` where the channel requires a client certificate,
            ``None`` where nothing in the sources requires one
        value_source: File the evidence was read from, ``None`` where no file
            states anything
    """

    transport: str
    client_auth: str | None = None
    value_source: str | None = None


def grpc_server_transport(sources: dict[str, str]) -> TransportEvidence:
    """Read the transport a gRPC server binds its port with.

    ``createInsecure`` and ``createSsl`` are the two ways a gRPC server states
    it. A server that calls neither is reported as unresolved: the credentials
    may be built somewhere this does not look.

    Args:
        sources (dict[str, str]): Contents of the service's sources, by path

    Returns:
        TransportEvidence: What the sources state
    """
    for path, content in sorted(sources.items()):
        if SECURE_GRPC_SERVER.search(content):
            return TransportEvidence(
                Transport.TLS.value, grpc_client_auth(content), path
            )
        if INSECURE_GRPC_SERVER.search(content):
            return TransportEvidence(Transport.PLAINTEXT.value, None, path)
    return TransportEvidence(Transport.UNRESOLVED.value)


def messaging_transport(sources: dict[str, str]) -> TransportEvidence:
    """Read the transport a service opens its broker connection with.

    The evidence is looked for around the call that opens the connection rather
    than anywhere in the file: a service that secures one channel and not
    another states both in the same source, and a match from the wrong one would
    report a plaintext channel as protected. See
    :data:`mrf.utilities.node.MESSAGING_WINDOW` for how wide that window is and
    what it therefore misses.

    A service whose sources open no connection is reported as unresolved rather
    than as plaintext.

    Args:
        sources (dict[str, str]): Contents of the service's sources, by path

    Returns:
        TransportEvidence: What the sources state
    """
    for path, content in sorted(sources.items()):
        window = messaging_window(content)
        if window is None:
            continue
        if SSL_OPTION.search(window) or any(
            scheme in window for scheme in TLS_URL_SCHEMES
        ):
            # What the broker requires of a client certificate is the broker's
            # own configuration, and the broker is no service of the model, so
            # only the encryption is read here.
            return TransportEvidence(Transport.TLS.value, None, path)
        return TransportEvidence(Transport.PLAINTEXT.value, None, path)
    return TransportEvidence(Transport.UNRESOLVED.value)


def messaging_window(content: str) -> str | None:
    """Return the lines around the calls that open a broker connection.

    Args:
        content (str): Content of a source

    Returns:
        str | None: The window, or ``None`` where the source opens no connection
    """
    lines = content.splitlines()
    anchors = [i for i, line in enumerate(lines) if MESSAGING_ANCHOR.search(line)]
    if not anchors:
        return None
    start = max(0, anchors[0] - MESSAGING_WINDOW)
    end = min(len(lines), anchors[-1] + MESSAGING_WINDOW + 1)
    return "\n".join(lines[start:end])


def grpc_client_auth(content: str) -> str | None:
    """Read whether a secure gRPC server requires a client certificate.

    Args:
        content (str): Content of the source that calls ``createSsl``

    Returns:
        str | None: :data:`mrf.utilities.node.CLIENT_AUTH_REQUIRED` where a
        client certificate is required, ``None`` otherwise
    """
    match = SECURE_GRPC_SERVER.search(content)
    if match is None:
        return None
    arguments = call_arguments(content, match.end())
    if len(arguments) > 2 and arguments[2].strip() == GRPC_CLIENT_AUTH_ARGUMENT:
        return CLIENT_AUTH_REQUIRED
    return None


def call_arguments(content: str, start: int) -> list[str]:
    """Split the arguments of a call whose opening bracket was consumed.

    Args:
        content (str): Content of the source
        start (int): Index just behind the opening bracket of the call

    Returns:
        [str]: The arguments at the call's own bracket level
    """
    arguments: list[str] = []
    current: list[str] = []
    # The brackets of an argument - an array of key-certificate pairs, an
    # object - are counted, so that a comma inside one does not end it.
    depth = 0
    for character in content[start:]:
        if character in "([{":
            depth += 1
        elif character in ")]}":
            if depth == 0:
                break
            depth -= 1
        if character == "," and depth == 0:
            arguments.append("".join(current))
            current = []
            continue
        current.append(character)
    arguments.append("".join(current))
    return arguments
