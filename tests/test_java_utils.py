"""Unit tests for the Java parsing helpers."""

import logging

import pytest
from javalang.parser import JavaParserBaseException
from mrf.utilities.command_line import SourceFile
from mrf.utilities.java_utils import (
    HIERARCHY_LEVEL,
    NoJavaDeclrationException,
    adjust_name,
    adjust_qualified_name,
    get_class_from_tree,
    get_class_name,
    get_qualified_class_name,
    has_annotation,
    load_classes,
    match_context,
    match_microservice_interface,
    parse_java_file,
)

ENTITY_SOURCE = """
package com.lakesidemutual.customercore.domain.customer;

import javax.persistence.Entity;

@Entity
public class Customer {
    @Id private String firstname;
}
"""


def test_parse_java_file_yields_package_and_class_name():
    tree = parse_java_file(ENTITY_SOURCE)

    assert get_qualified_class_name(tree) == (
        "com.lakesidemutual.customercore.domain.customer.Customer"
    )
    assert get_class_name(get_class_from_tree(tree)) == "Customer"


def test_parse_java_file_supports_records():
    # ljavalang (not javalang) is used precisely because of Java 9-22 syntax.
    tree = parse_java_file("package a.b; public record Point(int x, int y) {}")

    assert get_class_name(get_class_from_tree(tree)) == "Point"


def test_get_class_from_tree_without_declaration_raises():
    tree = parse_java_file("package a.b;")

    with pytest.raises(NoJavaDeclrationException):
        get_class_from_tree(tree)


def test_has_annotation_matches_field_annotations():
    clazz = get_class_from_tree(parse_java_file(ENTITY_SOURCE))

    assert has_annotation(clazz.fields[0], ["Id"]) is True
    assert has_annotation(clazz.fields[0], ["Column"]) is False


def test_has_annotation_matches_class_annotations():
    clazz = get_class_from_tree(parse_java_file(ENTITY_SOURCE))

    assert has_annotation(clazz, ["Entity"]) is True
    assert has_annotation(clazz, ["RestController"]) is False


def test_adjust_name_removes_application_suffix():
    assert adjust_name("CustomerCoreApplication") == "CustomerCore"
    assert adjust_name("CustomerCore") == "CustomerCore"


def test_adjust_qualified_name_reroots_structure_onto_context():
    assert (
        adjust_qualified_name(
            "de.dmsa.parkandcharge.station",
            "de.dmsa.parkandcharge.station.domain.ProcessedEvent",
        )
        == "de.dmsa.parkandcharge.station.ProcessedEvent"
    )


def test_match_context_returns_common_prefix_and_stops_at_difference():
    assert match_context("com.example.a.b", "com.example.a.c") == [
        "com",
        "example",
        "a",
    ]
    assert match_context("com.example", "org.other") == []


def test_match_microservice_interface_requires_hierarchy_level_parts():
    # HIERARCHY_LEVEL matching parts are required for a match.
    assert HIERARCHY_LEVEL == 3
    assert (
        match_microservice_interface(
            "com.lakesidemutual.customercore",
            "com.lakesidemutual.customercore.interfaces",
        )
        is True
    )
    assert (
        match_microservice_interface("com.lakesidemutual", "com.other.service") is False
    )


UNPARSABLE_SOURCE = """
package com.example;

public class DataLoader {
    void load() {
        registry.module(schema);
    }
}
"""


def test_load_classes_skips_a_file_the_parser_cannot_read(caplog):
    """An unreadable file must not end the reconstruction of the readable ones.

    The source uses a restricted keyword as a method name. Which construct the
    parser rejects is a property of the pinned parser revision, so the test
    asserts that it is rejected rather than assuming it, and fails loudly if a
    parser update makes it readable - otherwise this test would silently stop
    covering anything.
    """
    unparsable = SourceFile(
        "src/com/example/DataLoader.java", UNPARSABLE_SOURCE, ".java"
    )
    readable = SourceFile("src/com/example/Customer.java", ENTITY_SOURCE, ".java")

    with pytest.raises(JavaParserBaseException):
        parse_java_file(UNPARSABLE_SOURCE)

    with caplog.at_level(logging.WARNING):
        java_classes = load_classes([unparsable, readable], [".java"])

    assert [get_class_name(get_class_from_tree(c.tree)) for c in java_classes] == [
        "Customer"
    ]
    assert "src/com/example/DataLoader.java" in caplog.text
    assert "the reconstruction is incomplete" in caplog.text
