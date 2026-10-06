"""Golden-fixture tests for the reconstruction from Protocol Buffers files.

Each fixture under ``tests/fixtures/protobuf-*/`` holds one ``.proto`` file and
the model it is expected to produce. The expected files are named
``expected_protobuf.json`` so the fixtures of ``test_golden.py``, which are
discovered by the name ``expected.json``, stay separate: a proto fixture has no
Java to reconstruct and would compare two empty lists there.

Nothing here touches MongoDB.
"""

import json
import pathlib

import pytest
from deepdiff import DeepDiff
from mrf.modules.reconstruction_handler import ReconstructionHandler
from mrf.plugins.reconstruction_plugin import PluginType

from tests.test_golden import load_source_files, reset_handler, to_plain

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures"
EXPECTED_FILE = "expected_protobuf.json"


def reconstruct_protobuf(fixture: pathlib.Path) -> dict:
    """Run the reconstruction over a fixture and return the serialised model.

    The whole handler runs, because one selection of the plugin contributes to
    the domain phase and to the service phase, and the two have to agree on the
    qualified names they produce.
    """
    reset_handler()
    handler = ReconstructionHandler(load_source_files(fixture), [PluginType.PROTOBUF])
    handler.reconstruct_start()
    return {
        "contexts": to_plain(handler.reconstructed_data),
        "microservices": to_plain(handler.reconstructed_service),
    }


def fixtures() -> list[pathlib.Path]:
    return sorted(p for p in FIXTURE_ROOT.iterdir() if (p / EXPECTED_FILE).is_file())


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_protobuf_matches_expected_output(fixture):
    expected = json.loads((fixture / EXPECTED_FILE).read_text(encoding="utf-8"))

    actual = reconstruct_protobuf(fixture)

    difference = DeepDiff(expected, actual, ignore_order=True)
    assert not difference, f"reconstruction output changed:\n{difference.pretty()}"


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_reconstruction_is_deterministic(fixture):
    """Two runs over one fixture must produce the same model.

    The order of the source files follows the file system, so the proto files
    are sorted before they are read.
    """
    first = reconstruct_protobuf(fixture)
    second = reconstruct_protobuf(fixture)

    assert json.dumps(first, indent=2) == json.dumps(second, indent=2)


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_a_structure_resolves_to_the_context_it_belongs_to(fixture):
    """Every structure must be qualified so the LEMMA side finds its context.

    ``Util.getContextNameFromQualifedName`` on the LEMMA side reads the context
    of a structure as the **second to last** part of the structure's qualified
    name, and names the data model file after the context. A structure qualified
    any other way is generated into a model whose import does not resolve, which
    no test of the reconstruction alone would otherwise notice.
    """
    model = reconstruct_protobuf(fixture)

    for context in model["contexts"]:
        for structure in context["data_structures"]:
            parts = structure["qualified_name"].split(".")
            assert parts[-2] == context["name"], (
                f"{structure['qualified_name']} would be read into the context "
                f"{parts[-2]}, not into {context['name']}"
            )
        for collection in context["collections"]:
            parts = collection["qualified_name"].split(".")
            assert parts[-2] == context["name"]


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_a_microservice_name_has_a_qualifying_part(fixture):
    """A microservice whose name has no dot is extracted with a placeholder.

    ``ServiceDslExtractor.lemmaName`` writes ``ADD_QUALIFYING_PART.<name>`` for
    a microservice whose name is a single identifier, so a reconstruction that
    produces one puts that text into the model.
    """
    model = reconstruct_protobuf(fixture)

    for microservice in model["microservices"]:
        assert "." in microservice["qualified_name"], (
            f"{microservice['qualified_name']} has no qualifying part"
        )
