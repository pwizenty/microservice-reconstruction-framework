"""
Main module of the Microservice Reconstruction Framework (MAF)
"""

import mrf.utilities.command_line as line
from mrf.modules.reconstruction_handler import ReconstructionHandler


def main():
    """
    Main method of the mrf.
    """

    print("Microservice Reconstruction Framework")
    print("Reconstruction: Start!")
    args = line.handle_parameters()
    if args.plugin is None or args.target is None:
        print("Plugins and target folder must be selected for execution")
        return None

    plugins = line.args_to_plugins(args)
    files = line.load_files(args.target)
    source_files = line.files_to_source_files(files)
    hdl = ReconstructionHandler(source_files, plugins)
    hdl.reconstruct_start()
    hdl.reconstruct_save()
    print("Reconstruction:  End!")


if __name__ == "__main__":
    main()
