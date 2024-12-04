import argparse as arg_parser
from pathlib import Path

from mrf.plugins.reconstruction_plugin import PluginType


class SourceFile:
    def __init__(self, path, file, suffix):
        self.path = path
        self.file = file
        self.suffix = suffix


def handle_parameters():
    parser = arg_parser.ArgumentParser(
        description="Parse the command line arguments for the Microservice " +
                    "Reconstruction Framework.")
    parser.add_argument("-p", "--plugin", choices=["Java", "Docker"],
                        nargs='+', type=str, help="Plugins used by the MRF.")
    parser.add_argument("-t", "--target", type=str,
                        help="File path to the system's source code.")
    args = parser.parse_args()
    return args


def load_file(file_path):
    code = None
    try:
        with open(file_path, 'r') as file:
            code = file.read()
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
    except IOError:
        print(f"An error occurred while reading the file {file_path}.")
    except UnicodeDecodeError:
        print(f"An UnicodeError occurred while reading the file {file_path}.")
    return code


def load_files(file_path):
    directory = Path(file_path)
    files = [f for f in directory.rglob('*') if f.is_file()]
    return files


def files_to_source_files(files):
    source_files = []
    for f in files:
        path = str(f)
        file = load_file(path)
        source_file = SourceFile(path, file, f.suffix)
        source_files.append(source_file)
    return source_files


def args_to_plugins(args):
    plugins = []
    for a in args.plugin:
        plugin_type = PluginType(a)
        plugins.append(plugin_type)
    return plugins
