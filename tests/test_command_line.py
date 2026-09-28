"""Unit tests for the command line support."""

import subprocess
import sys

import pytest
from mrf.plugins.reconstruction_plugin import PluginType
from mrf.utilities.command_line import (
    args_to_plugins,
    files_to_source_files,
    load_file,
    load_files,
)


class _Args:
    """Stand-in for the argparse namespace."""

    def __init__(self, plugin):
        self.plugin = plugin


def test_args_to_plugins_maps_names_to_plugin_types():
    plugins = args_to_plugins(_Args(["Java", "Spring"]))

    assert plugins == [PluginType.JAVA, PluginType.SPRING]


def test_args_to_plugins_rejects_unknown_plugin():
    with pytest.raises(ValueError):
        args_to_plugins(_Args(["Rust"]))


def test_load_file_returns_none_for_missing_file(tmp_path):
    assert load_file(str(tmp_path / "nope.java")) is None


def test_load_file_reads_content(tmp_path):
    target = tmp_path / "A.java"
    target.write_text("class A {}", encoding="utf-8")

    assert load_file(str(target)) == "class A {}"


def test_load_files_collects_files_recursively(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "A.java").write_text("class A {}", encoding="utf-8")
    (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")

    found = {p.name for p in load_files(str(tmp_path))}

    assert found == {"A.java", "pom.xml"}


def test_files_to_source_files_keeps_path_content_and_suffix(tmp_path):
    target = tmp_path / "A.java"
    target.write_text("class A {}", encoding="utf-8")

    source_files = files_to_source_files(load_files(str(tmp_path)))

    assert len(source_files) == 1
    assert source_files[0].suffix == ".java"
    assert source_files[0].file == "class A {}"
    assert source_files[0].path == str(target)


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "mrf.main", "-h"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--plugin" in result.stdout


def test_cli_without_arguments_exits_with_status_two():
    # Regression test: previously raised TypeError in args_to_plugins.
    result = subprocess.run(
        [sys.executable, "-m", "mrf.main"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
