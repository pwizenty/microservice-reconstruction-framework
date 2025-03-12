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
    plugins = line.args_to_plugins(args)
    files = line.load_files(args.target)
    source_files = line.files_to_source_files(files)
    hdl = ReconstructionHandler(source_files, plugins)
    hdl.reconstruct_start()
    hdl.reconstruct_save()
    print("Reconstruction:  End!")


if __name__ == "__main__":
    main()
