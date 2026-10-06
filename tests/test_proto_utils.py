"""Unit tests for the proto3 parser.

The parser is hand-written rather than taken from a dependency, so what it
accepts and what it refuses is pinned here rather than assumed. Each test states
one property of proto3 that the reconstruction depends on.
"""

import pytest
from mrf.utilities.proto_utils import (
    ProtoParseError,
    parse_proto_file,
    primitive_of,
)
from mrf.utilities.protobuf import referable_types, structure_name_of


def test_a_package_and_a_service_with_one_rpc():
    proto = parse_proto_file("""
        syntax = "proto3";
        package riskmanagement;
        service RiskManagement {
          rpc Trigger (TriggerRequest) returns (TriggerReply);
        }
    """)

    assert proto.package == "riskmanagement"
    assert [s.name for s in proto.services] == ["RiskManagement"]
    rpc = proto.services[0].rpcs[0]
    assert (rpc.name, rpc.request_type, rpc.response_type) == (
        "Trigger",
        "TriggerRequest",
        "TriggerReply",
    )
    assert not rpc.request_stream
    assert not rpc.response_stream


def test_a_stream_is_read_on_each_side_independently():
    proto = parse_proto_file("""
        service S {
          rpc Out (A) returns (stream B);
          rpc In (stream A) returns (B);
          rpc Both (stream A) returns (stream B);
        }
    """)

    streams = {
        rpc.name: (rpc.request_stream, rpc.response_stream)
        for rpc in proto.services[0].rpcs
    }
    assert streams == {
        "Out": (False, True),
        "In": (True, False),
        "Both": (True, True),
    }


def test_an_rpc_with_a_block_of_options():
    """An rpc may end in a block rather than a semicolon."""
    proto = parse_proto_file("""
        service S {
          rpc A (R) returns (R) { option deadline = 5; }
          rpc B (R) returns (R);
        }
    """)

    assert [rpc.name for rpc in proto.services[0].rpcs] == ["A", "B"]


def test_a_message_and_its_field_labels():
    proto = parse_proto_file("""
        message M {
          string plain = 1;
          repeated int32 many = 2;
          optional bool maybe = 3;
        }
    """)

    fields = {
        f.name: (f.type_name, f.repeated, f.optional) for f in proto.messages[0].fields
    }
    assert fields == {
        "plain": ("string", False, False),
        "many": ("int32", True, False),
        "maybe": ("bool", False, True),
    }


def test_a_field_of_a_oneof_is_optional_and_names_its_group():
    proto = parse_proto_file("""
        message M {
          oneof either {
            string text = 1;
            int32 number = 2;
          }
          string outside = 3;
        }
    """)

    fields = {f.name: (f.optional, f.oneof) for f in proto.messages[0].fields}
    assert fields == {
        "text": (True, "either"),
        "number": (True, "either"),
        "outside": (False, None),
    }


def test_a_map_is_read_as_a_sequence_of_its_value_type():
    """The model has no map, and the value is what a consumer needs."""
    proto = parse_proto_file("message M { map<string, Entry> by_name = 1; }")

    field = proto.messages[0].fields[0]
    assert (field.name, field.type_name, field.repeated) == ("by_name", "Entry", True)


def test_a_nested_message_keeps_its_parents_in_its_name():
    proto = parse_proto_file("""
        message Outer {
          string a = 1;
          message Inner {
            string b = 1;
            message Innermost { string c = 1; }
          }
        }
    """)

    assert [m.name for m in proto.messages] == [
        "Outer",
        "Outer.Inner",
        "Outer.Inner.Innermost",
    ]


def test_a_nested_enum_is_read_with_the_others():
    proto = parse_proto_file("""
        enum Top { A = 0; }
        message M { enum Inner { B = 0; C = 1; } }
    """)

    assert {e.name: e.values for e in proto.enums} == {
        "Top": ["A"],
        "Inner": ["B", "C"],
    }


def test_a_commented_out_declaration_is_not_read():
    """Both comment forms, because a model must not contain what is commented."""
    proto = parse_proto_file("""
        // service LineGhost { rpc N (A) returns (B); }
        /* service BlockGhost { rpc N (A) returns (B); }
           message GhostMessage { string x = 1; } */
        service Real { rpc R (A) returns (B); }
    """)

    assert [s.name for s in proto.services] == ["Real"]
    assert proto.messages == []


@pytest.mark.parametrize(
    "declaration",
    [
        'syntax = "proto3";',
        'import "other.proto";',
        'import public "other.proto";',
        'option java_package = "com.example";',
        "extend M { string x = 1; }",
    ],
)
def test_a_declaration_without_architecture_information_is_skipped(declaration):
    proto = parse_proto_file(f"{declaration} message Kept {{ string a = 1; }}")

    assert [m.name for m in proto.messages] == ["Kept"]


def test_reserved_ranges_and_field_options_are_skipped():
    proto = parse_proto_file("""
        message M {
          option deprecated = true;
          reserved 2, 15 to 20;
          reserved "old_name";
          string kept = 1 [deprecated = true];
        }
    """)

    assert [f.name for f in proto.messages[0].fields] == ["kept"]


def test_an_enum_with_a_reserved_entry():
    proto = parse_proto_file("enum E { A = 0; reserved 2; B = 1; }")

    assert proto.enums[0].values == ["A", "B"]


def test_a_file_that_is_not_proto_is_refused():
    with pytest.raises(ProtoParseError):
        parse_proto_file("service { }")


def test_a_truncated_file_is_refused():
    with pytest.raises(ProtoParseError):
        parse_proto_file("message M { oneof")


def test_every_proto3_scalar_maps_onto_a_primitive():
    """A scalar with no mapping would silently become a complex type."""
    scalars = [
        "double",
        "float",
        "int32",
        "int64",
        "uint32",
        "uint64",
        "sint32",
        "sint64",
        "fixed32",
        "fixed64",
        "sfixed32",
        "sfixed64",
        "bool",
        "string",
        "bytes",
    ]

    assert all(primitive_of(scalar) is not None for scalar in scalars)
    assert primitive_of("Report") is None


def test_a_nested_name_carries_no_dot_into_the_model():
    """A dot in a structure's name would be read as its context by LEMMA."""
    assert structure_name_of("Outer.Inner") == "Outer_Inner"
    assert structure_name_of("Flat") == "Flat"


def test_a_type_is_referable_by_its_simple_and_its_qualified_name():
    referable = referable_types(["Outer", "Outer.Inner"], ["Status"])

    assert referable["Outer.Inner"] == "Outer_Inner"
    assert referable["Inner"] == "Outer_Inner"
    assert referable["Outer"] == "Outer"
    assert referable["Status"] == "Status"


def test_an_ambiguous_simple_name_is_left_unresolved(caplog):
    """Two nested types of the same simple name cannot both own it.

    Resolving one of them would reference the wrong structure, which is worse
    than referencing none: an unresolved type is reported as unspecified.
    """
    referable = referable_types(["A", "A.Inner", "B", "B.Inner"], [])

    assert "Inner" not in referable
    assert referable["A.Inner"] == "A_Inner"
    assert referable["B.Inner"] == "B_Inner"
