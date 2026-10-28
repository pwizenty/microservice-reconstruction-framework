"""Contract tests for class-level annotation parsing.

Detecting annotations on the first top-level type is how both plugins find
microservices, bounded contexts and entities. Released ljavalang 2.1.0 drops
them, which made MRF reconstruct nothing; the pinned fork fixes it (ADR-0006).

These tests are the contract MRF relies on from the parser. They fail if the
pin is moved to a revision that regresses, so they guard the dependency rather
than any MRF code.
"""

import pytest
from javalang.parser import JavaSyntaxError
from mrf.utilities.java_utils import get_class_from_tree, parse_java_file


def annotations_of(source: str) -> list[str]:
    """Return the annotation names of the first top-level type."""
    clazz = get_class_from_tree(parse_java_file(source))
    return [a.name for a in clazz.annotations]


@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        (
            "conventional form",
            "package a;\nimport javax.persistence.Entity;\n"
            "@Entity\npublic class C {}\n",
            ["Entity"],
        ),
        (
            "several annotations keep source order",
            'package a;\n@Entity\n@Table(name = "c")\npublic class C {}\n',
            ["Entity", "Table"],
        ),
        (
            "annotation after the modifier is kept by the parser itself",
            "package a;\npublic @Entity class C {}\n",
            ["Entity"],
        ),
        (
            "element containing a nested annotation and braces",
            'package a;\n@Table(indexes = {@Index(name = "x")})\npublic class C {}\n',
            ["Table"],
        ),
        (
            "qualified annotation name",
            "package a;\n@javax.persistence.Entity\npublic class C {}\n",
            ["javax.persistence.Entity"],
        ),
        ("no annotation at all", "package a;\npublic class C {}\n", []),
        (
            "no package declaration",
            "@Entity\npublic class C {}\n",
            ["Entity"],
        ),
        (
            "several modifiers",
            "package a;\n@Entity\npublic final class C {}\n",
            ["Entity"],
        ),
        ("record", "package a;\n@Entity\npublic record C(int x) {}\n", ["Entity"]),
        (
            "interface",
            "package a;\n@RestController\npublic interface C {}\n",
            ["RestController"],
        ),
        ("enum", "package a;\n@Entity\npublic enum C { A }\n", ["Entity"]),
        (
            "annotation type declaration",
            "package a;\n@Documented\npublic @interface C {}\n",
            ["Documented"],
        ),
    ],
)
def test_first_type_annotations_are_parsed(label, source, expected):
    assert annotations_of(source) == expected, label


def test_package_annotation_is_not_attributed_to_the_type():
    # @Deprecated annotates the package declaration, not the class.
    source = "@Deprecated\npackage a;\npublic class C {}\n"

    assert annotations_of(source) == []


def test_further_top_level_types_keep_their_annotations():
    source = "package a;\n@A\nclass First {}\n@B\nclass Second {}\n"
    unit = parse_java_file(source)

    assert [a.name for a in unit.types[0].annotations] == ["A"]
    assert [a.name for a in unit.types[1].annotations] == ["B"]


def test_annotations_at_every_position_are_parsed():
    source = (
        "package a;\n"
        "@RestController\n"
        "public class Ctrl {\n"
        "  @Id private String f;\n"
        '  @GetMapping("/x")\n'
        "  public String get() { return null; }\n"
        "  @Deprecated static class Inner {}\n"
        "}\n"
    )
    clazz = get_class_from_tree(parse_java_file(source))

    assert [a.name for a in clazz.annotations] == ["RestController"]
    assert [a.name for a in clazz.fields[0].annotations] == ["Id"]
    assert [a.name for a in clazz.methods[0].annotations] == ["GetMapping"]


def test_annotation_arguments_are_parsed():
    # MRF matches on names only, but the parser keeps the element, so an
    # argument-aware heuristic stays possible.
    clazz = get_class_from_tree(
        parse_java_file('package a;\n@Table(name = "c")\npublic class C {}\n')
    )

    assert clazz.annotations[0].name == "Table"
    assert clazz.annotations[0].element is not None


def test_unparsable_source_raises():
    with pytest.raises(JavaSyntaxError):
        parse_java_file("package a; this is not java")
