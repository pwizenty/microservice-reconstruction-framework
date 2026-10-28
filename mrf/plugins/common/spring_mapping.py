"""Reading the mapping annotation of a Spring REST element.

Shared by the plugins that read one from either side of a call: the Spring
plugin, for the controller a service offers, and the communication plugin, for
the client a service calls with. Both need the same two facts - which mapping
annotation it is, and the path it names - and Spring writes them the same way
whether the element is a controller or a client.
"""

from javalang.tree import Annotation

from mrf.utilities.java_utils import find_annotation, get_annotation_values
from mrf.utilities.sping import MAPPING_PATH_ELEMENTS


def find_mapping(
    annotations: list[Annotation], names: list[str]
) -> tuple[Annotation, str | None] | None:
    """Find the mapping annotation among the given ones, and the path it names.

    The annotation itself is returned rather than only its name, because it
    carries the position a fact read from it should cite: the line of the
    annotation says what was read, where the line of the method it sits on does
    not.

    Args:
        annotations ([Annotation]): Annotations of a class, an interface or a
            method
        names ([str]): Names of the annotations that may hold a path

    Returns:
        tuple[Annotation, str | None] | None: The annotation and the path it
            names, or ``None`` when none of the annotations is there. The path
            is ``None`` for an annotation that names none, as a bare
            ``@GetMapping`` does.
    """
    annotation = find_annotation(annotations, names)
    if annotation is None:
        return None

    values = get_annotation_values(annotation)
    path = next(
        (values[element] for element in MAPPING_PATH_ELEMENTS if element in values),
        None,
    )
    return annotation, path or None
