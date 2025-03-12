"""
Command line support for the Microservice Reconstruction Framework to handle
its configuration and execution.
"""

import argparse as arg_parser
from dataclasses import dataclass
from pathlib import Path

from mrf.plugins.reconstruction_plugin import PluginType


@dataclass
class SourceFile:
    """
    Data class for structuring information about source code artifacts.
    Args:
        path (str): Relative path to the file
        file (File): Source code artifact of the software system
        suffix (str): Suffix of the file
    """

    def __init__(self, path, file, suffix):
        self.path = path
        self.file = file
        self.suffix = suffix


def handle_parameters():
    """
    Handle command line parameter to configure the execution of the Microservice
    reconstruction framework.
    Returns:
        plugin: Selected plugins for the reconstruction process
        target: File path to the folder with the source code of the system
    """
    parser = arg_parser.ArgumentParser(
        description="Parse the command line arguments for the Microservice "
        + "Reconstruction Framework."
    )
    parser.add_argument(
        "-p",
        "--plugin",
        choices=["Java", "Docker"],
        nargs="+",
        type=str,
        help="Plugins used by the MRF.",
    )
    parser.add_argument(
        "-t", "--target", type=str, help="File path to the system's source code."
    )
    args = parser.parse_args()
    return args


def load_file(file_path: str) -> str | None:
    """
    [TODO:description]

    :param file_path: [TODO:description]
    :return: [TODO:description]
    """
    code = None
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            code = file.read()
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except IOError:
        print(f"An error occurred while reading the file {file_path}.")
    except UnicodeDecodeError:
        print(f"An UnicodeError occurred while reading the file {file_path}.")
    return code


def load_files(file_path) -> list[Path]:
    directory = Path(file_path)
    files = [f for f in directory.rglob("*") if f.is_file()]
    return files


def files_to_source_files(files) -> list[SourceFile]:
    """
    Transforms a list of files to a list of :class: `SourceFile`.
    Args:
        files (File):

    Returns:
        source_files: a list of source files
    """
    source_files = []
    for f in files:
        path = str(f)
        file = load_file(path)
        source_file = SourceFile(path, file, f.suffix)
        source_files.append(source_file)
    return source_files


def args_to_plugins(args) -> list[PluginType]:
    """
    Select the plugins from the command line arguments and transform them into
    a list pf :class: `PluginType`s.

    Args:
        args ([str]): List of command line arguments

    Returns:
        [PluginType]: List of PluginType

    """
    plugins: list[PluginType] = []
    for a in args.plugin:
        plugin_type = PluginType(a)
        plugins.append(plugin_type)
    return plugins
