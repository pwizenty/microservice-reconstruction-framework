"""Command line support for the Microservice Reconstruction Framework.

Handles the configuration and execution of a reconstruction run.
"""

import argparse as arg_parser
import logging
from dataclasses import dataclass
from pathlib import Path

from mrf.plugins.reconstruction_plugin import PluginType

logger = logging.getLogger(__name__)


@dataclass
class SourceFile:
    """Data class for structuring information about source code artifacts.

    Args:
        path (str): Relative path to the file
        file (File): Source code artifact of the software system
        suffix (str): Suffix of the file
    """

    def __init__(self, path, file, suffix):
        self.path = path
        self.file = file
        self.suffix = suffix


def handle_parameters() -> arg_parser.Namespace:
    """Handle the command line parameters of a reconstruction run.

    Returns:
        argparse.Namespace: Parsed arguments with ``plugin`` (selected plugins)
        and ``target`` (path to the folder with the system's source code)
    """
    parser = arg_parser.ArgumentParser(
        description="Parse the command line arguments for the Microservice "
        + "Reconstruction Framework."
    )
    parser.add_argument(
        "-p",
        "--plugin",
        choices=["Java", "Docker", "Spring"],
        nargs="+",
        type=str,
        help="Plugins used by the MRF.",
    )
    parser.add_argument(
        "-t", "--target", type=str, help="File path to the system's source code."
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Drop the reconstruction of earlier runs before saving this one. "
        + "Without it a run updates what it finds and leaves the rest, so "
        + "several systems can share a database.",
    )
    args = parser.parse_args()
    return args


def load_file(file_path: str) -> str | None:
    """Read a single source code file.

    Args:
        file_path (str): Path to the file to read.

    Returns:
        str | None: Content of the file, or ``None`` if it could not be read.
    """
    code = None
    try:
        with open(file_path, encoding="utf-8") as file:
            code = file.read()
    except FileNotFoundError:
        logger.warning("The file %s was not found.", file_path)
    except OSError:
        logger.warning("An error occurred while reading the file %s.", file_path)
    except UnicodeDecodeError:
        logger.warning("An UnicodeError occurred while reading the file %s.", file_path)
    return code


def load_files(file_path: str) -> list[Path]:
    """Collect all files below a directory.

    Args:
        file_path (str): Path to the folder with the system's source code

    Returns:
        [Path]: Paths of all files found below the folder
    """
    directory = Path(file_path)
    files = [f for f in directory.rglob("*") if f.is_file()]
    return files


def files_to_source_files(files) -> list[SourceFile]:
    """Transform a list of files into a list of :class:`SourceFile`.

    Args:
        files ([Path]): Paths of the files to read

    Returns:
        [SourceFile]: Source files including their content and suffix
    """
    source_files = []
    for f in files:
        path = str(f)
        file = load_file(path)
        source_file = SourceFile(path, file, f.suffix)
        source_files.append(source_file)
    return source_files


def args_to_plugins(args) -> list[PluginType]:
    """Select the plugins from the command line arguments.

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Returns:
        [PluginType]: Plugins selected for the reconstruction process
    """
    plugins: list[PluginType] = []
    for a in args.plugin:
        plugin_type = PluginType(a)
        plugins.append(plugin_type)
    return plugins
