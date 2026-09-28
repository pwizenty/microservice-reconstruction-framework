"""Golden-fixture regression tests for the reconstruction plugins.

Each fixture under ``tests/fixtures/<system>/`` holds a minimal source tree and
the expected reconstruction output. The comparison runs against the in-memory
model returned by the plugins, so no MongoDB is involved.

``expected.json`` is reviewed by a human. When a change alters the output, show
the diff and confirm it before updating the file - never regenerate it just to
make the test pass.
"""

import json
import pathlib
from enum import Enum

import pytest
from deepdiff import DeepDiff
from mrf.plugins.data.java.java_plugin import JavaPlugin
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
    paths = sorted((fixture / "src").rglob("*.java"))
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


def fixtures() -> list[pathlib.Path]:
    return sorted(p for p in FIXTURE_ROOT.iterdir() if (p / "expected.json").is_file())


@pytest.mark.golden
@pytest.mark.parametrize("fixture", fixtures(), ids=lambda p: p.name)
def test_reconstruction_matches_expected_output(fixture):
    expected = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))

    actual = reconstruct(fixture)

    difference = DeepDiff(expected, actual, ignore_order=True)
    assert not difference, f"reconstruction output changed:\n{difference.pretty()}"
