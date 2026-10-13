"""Detector for the queues a service uses through Spring's JMS support.

A consumer states its queue on the annotation of the method that receives:

```java
@JmsListener(destination = "${insuranceQuoteRequestEvent.queueName}")
public void receiveInsuranceQuoteRequest(final Message<…> message) { … }
```

A producer states it nowhere near the call. ``JmsTemplate.convertAndSend`` takes
the destination as its first argument, and in practice that argument names a
field whose own annotation holds the placeholder:

```java
@Value("${riskmanagement.queueName}")
private String queueName;
…
jmsTemplate.convertAndSend(queueName, event);
```

So the destination is followed from the argument to the field, from the field to
its ``@Value``, and from the placeholder to the property. A destination that is
a literal is read directly; one that is built at run time is reported as
unresolved rather than guessed.
"""

import logging

from javalang.tree import CompilationUnit, MethodInvocation, TypeDeclaration

from mrf.plugins.service.communication.configuration import is_placeholder
from mrf.plugins.service.communication.detectors.detector import (
    DetectionContext,
    MessageChannel,
)
from mrf.plugins.service.communication.urls import evidence_for
from mrf.utilities.communication import (
    JMS_LISTENER,
    JMS_LISTENER_DESTINATION,
    JMS_SEND_METHODS,
    JMS_TEMPLATE,
    ROLE_CONSUMER,
    ROLE_PRODUCER,
    VALUE_ANNOTATION,
    ArtifactType,
)
from mrf.utilities.java_utils import find_annotation, get_annotation_values

logger = logging.getLogger(__name__)

UNRESOLVED_QUEUE = "unresolved"
"""Reported where a destination is named but cannot be followed to a queue."""


class JmsDetector:
    """Reconstructs the queues a class produces to or consumes from."""

    technology = "JMS"

    def detect(
        self,
        clazz: TypeDeclaration,
        unit: CompilationUnit,
        context: DetectionContext,
    ) -> list[MessageChannel]:
        """Reconstruct the channels a class uses.

        Args:
            clazz: Parsed declaration of the class
            unit: Unit the class is declared in
            context: Path, lines and configuration of the analysed file

        Returns:
            [MessageChannel]: The channels that were found
        """
        channels = self.__consumers(clazz, context)
        if self.__has_jms_template(clazz):
            channels.extend(self.__producers(clazz, context))
        return channels

    def __consumers(
        self, clazz: TypeDeclaration, context: DetectionContext
    ) -> list[MessageChannel]:
        """Every ``@JmsListener`` of the class."""
        channels: list[MessageChannel] = []
        for method in getattr(clazz, "methods", None) or []:
            annotation = find_annotation(
                getattr(method, "annotations", None) or [], [JMS_LISTENER]
            )
            if annotation is None:
                continue
            destination = get_annotation_values(annotation).get(
                JMS_LISTENER_DESTINATION
            )
            channels.append(
                self.__channel(ROLE_CONSUMER, destination, annotation, context)
            )
        return channels

    def __has_jms_template(self, clazz: TypeDeclaration) -> bool:
        """Whether the class holds a ``JmsTemplate``.

        A class that does not cannot produce, so its method bodies need no
        reading at all.
        """
        for field in getattr(clazz, "fields", None) or []:
            if getattr(getattr(field, "type", None), "name", None) == JMS_TEMPLATE:
                return True
        return False

    def __producers(
        self, clazz: TypeDeclaration, context: DetectionContext
    ) -> list[MessageChannel]:
        """Every send through a ``JmsTemplate``.

        The destination is the first argument of the call, which is followed to
        the field it names and to that field's ``@Value``.
        """
        channels: list[MessageChannel] = []
        placeholders = self.__field_placeholders(clazz)

        for _, invocation in clazz.filter(MethodInvocation):
            member = getattr(invocation, "member", None)
            if member not in JMS_SEND_METHODS:
                continue
            arguments = getattr(invocation, "arguments", None)
            if not arguments:
                continue

            destination = self.__destination_of(arguments[0], placeholders)
            channels.append(
                self.__channel(ROLE_PRODUCER, destination, invocation, context)
            )
        return channels

    def __field_placeholders(self, clazz: TypeDeclaration) -> dict[str, str]:
        """The placeholder of every field annotated with ``@Value``."""
        placeholders: dict[str, str] = {}
        for field in getattr(clazz, "fields", None) or []:
            annotation = find_annotation(
                getattr(field, "annotations", None) or [], [VALUE_ANNOTATION]
            )
            if annotation is None:
                continue
            values = get_annotation_values(annotation)
            placeholder = values.get("value")
            if placeholder is None:
                continue
            for declarator in getattr(field, "declarators", None) or []:
                name = getattr(declarator, "name", None)
                if name is not None:
                    placeholders[name] = placeholder
        return placeholders

    def __destination_of(self, argument, placeholders: dict[str, str]) -> str | None:
        """What the first argument of a send names.

        A literal is the queue. A reference to a field annotated with ``@Value``
        is that field's placeholder. Anything else - a method call, a
        concatenation - is not followed, and the channel is reported as
        unresolved.
        """
        literal = getattr(argument, "value", None)
        if isinstance(literal, str) and literal.startswith('"'):
            return literal.strip('"')

        member = getattr(argument, "member", None)
        if isinstance(member, str) and getattr(argument, "selectors", None) in (
            None,
            [],
        ):
            return placeholders.get(member)
        return None

    def __channel(
        self,
        role: str,
        destination: str | None,
        node,
        context: DetectionContext,
    ) -> MessageChannel:
        """One channel, with its queue resolved as far as the sources allow."""
        position = getattr(node, "position", None)
        evidence = evidence_for(
            context.path,
            context.lines,
            position.line if position is not None else 0,
            ArtifactType.SOURCE,
        )

        if destination is None:
            return MessageChannel(
                role=role,
                queue=UNRESOLVED_QUEUE,
                technology=self.technology,
                evidence=evidence,
                resolved=False,
            )

        if not is_placeholder(destination):
            return MessageChannel(
                role=role,
                queue=destination,
                technology=self.technology,
                evidence=evidence,
            )

        if context.configuration is None:
            return MessageChannel(
                role=role,
                queue=UNRESOLVED_QUEUE,
                technology=self.technology,
                evidence=evidence,
                resolved=False,
            )

        value, _, property_name = context.configuration.resolve(destination)
        if value is None or is_placeholder(value):
            logger.debug(
                "%s names the queue %s and nothing resolves it.",
                context.path,
                destination,
            )
            return MessageChannel(
                role=role,
                queue=UNRESOLVED_QUEUE,
                technology=self.technology,
                evidence=evidence,
                property_name=property_name,
                resolved=False,
            )
        return MessageChannel(
            role=role,
            queue=value,
            technology=self.technology,
            evidence=evidence,
            property_name=property_name,
        )
