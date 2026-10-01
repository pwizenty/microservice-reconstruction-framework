"""Golden-fixture tests for the reconstruction of service-to-service calls.

Each fixture under ``tests/fixtures/s2s-*/`` holds a minimal system and the
meta-data the reconstruction is expected to attach to its microservices. The
expected files are named ``expected_communication.json`` rather than
``expected.json`` so that the fixtures of ``test_golden.py`` stay separate: what
is compared here is the communication facts, not the domain and service models.

Nothing here touches MongoDB.
"""

import json
import pathlib

import pytest
from deepdiff import DeepDiff
from mrf.modules.reconstruction_handler import ReconstructionHandler
from mrf.plugins.common.spring_mapping import find_mapping
from mrf.plugins.reconstruction_plugin import PluginType
from mrf.plugins.service.communication.configuration import (
    is_placeholder,
    module_of,
    split_placeholder,
)
from mrf.plugins.service.communication.urls import is_schema_url
from mrf.utilities.communication import (
    SERVICE_CALL,
    SERVICE_CALL_ENDPOINT,
    SERVICE_COMMUNICATION_TRANSPORT,
    TRANSPORT,
)
from mrf.utilities.java_utils import get_class_from_tree, parse_java_file
from mrf.utilities.sping import REST_OPERATIONS

from tests.test_golden import load_source_files, reset_handler

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures"
EXPECTED_FILE = "expected_communication.json"


def reconstruct_communication(fixture: pathlib.Path) -> dict:
    """Run the reconstruction over a fixture and return its communication facts.

    The whole handler runs, because the facts are attached to the microservices
    of the service phase and the plugin needs them to tell a service of the
    system from a third party.
    """
    reset_handler()
    handler = ReconstructionHandler(
        load_source_files(fixture),
        [PluginType.JAVA, PluginType.SPRING, PluginType.COMMUNICATION],
    )
    handler.reconstruct_start()

    services = {}
    for microservice in handler.reconstructed_service:
        transport = next(
            (
                data.values[TRANSPORT]
                for data in microservice.data
                if data.name == SERVICE_COMMUNICATION_TRANSPORT
            ),
            None,
        )
        services[microservice.name] = {
            "transport": transport,
            "calls": [
                dict(sorted(data.values.items()))
                for data in microservice.data
                if data.name == SERVICE_CALL
            ],
            "endpoints": [
                dict(sorted(data.values.items()))
                for data in microservice.data
                if data.name == SERVICE_CALL_ENDPOINT
            ],
        }
    return dict(sorted(services.items()))


def fixtures() -> list[pathlib.Path]:
    return sorted(p for p in FIXTURE_ROOT.iterdir() if (p / EXPECTED_FILE).is_file())


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_communication_matches_expected_output(fixture):
    expected = json.loads((fixture / EXPECTED_FILE).read_text(encoding="utf-8"))

    actual = reconstruct_communication(fixture)

    difference = DeepDiff(expected, actual, ignore_order=True)
    assert not difference, f"communication facts changed:\n{difference.pretty()}"


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_reconstruction_is_deterministic(fixture):
    """Two runs over one fixture must produce the same facts.

    The order of the source files follows the file system, and the facts are
    collected per class, so without sorting the calls of a service could come
    out in a different order from one run to the next.
    """
    first = reconstruct_communication(fixture)
    second = reconstruct_communication(fixture)

    assert json.dumps(first, indent=2) == json.dumps(second, indent=2)


def test_split_placeholder_without_a_default():
    assert split_placeholder("${customercore.baseURL}") == (
        "customercore.baseURL",
        None,
    )


def test_split_placeholder_keeps_the_colons_of_a_url_default():
    """Only the first colon separates: a URL default holds colons of its own."""
    assert split_placeholder("${backend.url:http://localhost:8110}") == (
        "backend.url",
        "http://localhost:8110",
    )


def test_split_placeholder_accepts_a_bare_property_name():
    assert split_placeholder("backend.url") == ("backend.url", None)


def test_is_placeholder_distinguishes_a_literal():
    assert is_placeholder("${backend.url}")
    assert not is_placeholder("http://backend:8080")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.w3.org/2001/XMLSchema",
        "http://www.springframework.org/schema/beans",
        "http://maven.apache.org/POM/4.0.0",
    ],
)
def test_a_schema_url_is_no_address(url):
    assert is_schema_url(url)


def test_a_service_url_is_an_address():
    assert not is_schema_url("http://customer-core:8110")


def test_module_of_a_source_file():
    assert (
        module_of("customer-core/src/main/java/com/example/CoreApplication.java")
        == "customer-core"
    )


def test_module_of_a_resource():
    assert (
        module_of("customer-core/src/main/resources/application.properties")
        == "customer-core"
    )


def test_module_of_a_file_outside_a_module():
    assert module_of("docker-compose.yml") is None


MAPPING_SOURCE = """
package com.example;

@FeignClient(name = "backend", url = "${backend.baseURL}")
@RequestMapping("/api")
public interface BackendClient {
    @GetMapping(value = "/items")
    String getItems();

    @GetMapping
    String getRoot();

    @PutMapping(path = "/items/{id}")
    String putItem(String id);

    String unmapped();
}
"""


def mapping_of(method_name: str):
    """Return (annotation name, path) for a method of ``MAPPING_SOURCE``.

    ``find_mapping`` hands back the annotation itself, because a fact read from
    it cites its line; the tests only care about its name and the path.
    """
    clazz = get_class_from_tree(parse_java_file(MAPPING_SOURCE))
    if method_name == "interface":
        mapping = find_mapping(clazz.annotations, ["RequestMapping"])
    else:
        method = next(m for m in clazz.methods if m.name == method_name)
        mapping = find_mapping(method.annotations, REST_OPERATIONS)
    if mapping is None:
        return None
    annotation, path = mapping
    return annotation.name, path


def test_find_mapping_reads_the_base_path_of_the_declaration():
    assert mapping_of("interface") == ("RequestMapping", "/api")


def test_find_mapping_reads_a_verb_and_a_path():
    assert mapping_of("getItems") == ("GetMapping", "/items")


def test_find_mapping_reads_the_path_element_as_well_as_value():
    assert mapping_of("putItem") == ("PutMapping", "/items/{id}")


def test_find_mapping_reports_a_verb_without_a_path():
    """A bare @GetMapping addresses the path of its declaration."""
    assert mapping_of("getRoot") == ("GetMapping", None)


def test_find_mapping_of_a_method_without_one():
    assert mapping_of("unmapped") is None
