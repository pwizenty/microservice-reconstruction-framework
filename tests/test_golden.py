"""Golden-fixture regression tests for the reconstruction plugins.

Each fixture under ``tests/fixtures/<system>/`` holds a minimal source tree and
the expected reconstruction output. Nothing here touches MongoDB: the
comparison runs against the in-memory model.

Two levels are covered:

``expected.json``
    What the plugins return on their own, through ``execute_reconstruction``.

``expected_pipeline.json``
    What the whole reconstruction produces, including the phase that resolves
    the complex types referenced by the controllers and merges the resulting
    contexts. Only fixtures carrying such a file take part in that test.

Both files are reviewed by a human. When a change alters the output, show the
diff and confirm it before updating the file - never regenerate it just to make
the test pass.
"""

import json
import pathlib
from enum import Enum

import pytest
from deepdiff import DeepDiff
from mrf.modules.reconstruction_handler import ReconstructionHandler
from mrf.plugins.data.java.java_plugin import JavaPlugin
from mrf.plugins.reconstruction_plugin import PluginType
from mrf.plugins.service.spring.spring_plugin import SpringPlugin
from mrf.utilities.command_line import SourceFile

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures"


def to_plain(value):
    """Serialise the architecture model into plain JSON-compatible data.

    ``dataclasses.asdict`` is unusable here: ``Context`` carries the
    ``@dataclass`` decorator but declares no fields, so ``asdict`` returns an
    empty dict for it. Walking ``vars()`` handles both shapes.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if hasattr(value, "__dict__"):
        return {key: to_plain(val) for key, val in sorted(vars(value).items())}
    return value


def load_source_files(fixture: pathlib.Path) -> list[SourceFile]:
    """Read a fixture's sources with paths relative to the fixture root."""
    paths = sorted(p for p in (fixture / "src").rglob("*") if p.is_file())
    return [
        SourceFile(
            str(path.relative_to(fixture)),
            path.read_text(encoding="utf-8"),
            path.suffix,
        )
        for path in paths
    ]


def reconstruct(fixture: pathlib.Path) -> dict:
    """Run both plugins over a fixture and return the serialised model."""
    source_files = load_source_files(fixture)
    spring_result = SpringPlugin().execute_reconstruction(source_files)
    contexts = JavaPlugin().execute_reconstruction(source_files)
    return {
        "microservices": to_plain(spring_result.microservices),
        "contexts": to_plain(contexts),
    }


def reconstruct_pipeline(fixture: pathlib.Path) -> dict:
    """Run the full reconstruction the CLI runs and return the serialised model.

    Unlike :func:`reconstruct` this covers the second phase, in which the
    complex types the controllers reference are resolved into data structures
    (``JavaPlugin.reconstruct_dependencies``) and the resulting contexts are
    merged into the ones found in the domain phase. Nothing is saved: the
    handler's ``reconstruct_save`` is the only part that touches MongoDB.
    """
    reset_handler()
    handler = ReconstructionHandler(
        load_source_files(fixture),
        [PluginType.JAVA, PluginType.SPRING, PluginType.DOCKER],
    )
    handler.reconstruct_start()
    return {
        "microservices": to_plain(handler.reconstructed_service),
        "contexts": to_plain(handler.reconstructed_data),
        "operation": to_plain(handler.reconstructed_operation),
    }


def reset_handler() -> None:
    """Clear the handler's class-level state, which leaks between runs."""
    ReconstructionHandler._instance = None
    ReconstructionHandler.source_files = []
    ReconstructionHandler.reconstructed_data = []
    ReconstructionHandler.reconstructed_service = []
    ReconstructionHandler.reconstructed_operation = []
    ReconstructionHandler.plugins = []


def fixtures() -> list[pathlib.Path]:
    return sorted(p for p in FIXTURE_ROOT.iterdir() if (p / "expected.json").is_file())


def pipeline_fixtures() -> list[pathlib.Path]:
    return sorted(
        p for p in FIXTURE_ROOT.iterdir() if (p / "expected_pipeline.json").is_file()
    )


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_reconstruction_matches_expected_output(fixture):
    expected = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))

    actual = reconstruct(fixture)

    difference = DeepDiff(expected, actual, ignore_order=True)
    assert not difference, f"reconstruction output changed:\n{difference.pretty()}"


@pytest.mark.golden
@pytest.mark.parametrize("fixture", pipeline_fixtures(), ids=lambda p: p.name)
def test_full_pipeline_matches_expected_output(fixture):
    expected = json.loads(
        (fixture / "expected_pipeline.json").read_text(encoding="utf-8")
    )

    actual = reconstruct_pipeline(fixture)

    difference = DeepDiff(expected, actual, ignore_order=True)
    assert not difference, f"reconstruction output changed:\n{difference.pretty()}"
