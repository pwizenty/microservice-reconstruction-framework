"""Main module of the Microservice Reconstruction Framework (MRF)."""

import logging

import mrf.utilities.command_line as line
from mrf.modules.reconstruction_handler import ReconstructionHandler

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the reconstruction process from the command line.

    Raises:
        SystemExit: With status 2 if ``-p``/``--plugin`` or ``-t``/``--target``
            is missing.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Microservice Reconstruction Framework")
    logger.info("Reconstruction: Start!")
    args = line.handle_parameters()
    if args.plugin is None or args.target is None:
        logger.error("Plugins and target folder must be selected for execution")
        raise SystemExit(2)

    plugins = line.args_to_plugins(args)
    files = line.load_files(args.target)
    source_files = line.files_to_source_files(files)
    hdl = ReconstructionHandler(source_files, plugins)
    hdl.reconstruct_start()
    hdl.reconstruct_save()
    logger.info("Reconstruction: End!")


if __name__ == "__main__":
    main()
