import argparse as arg_parser


def handle_reconstruction_parameter():
    parser = arg_parser.ArgumentParser(
        description="Parse the command line arguments for the Microservice Reconstruction Framework."
    )
    parser.add_argument("-p", "--plugin", nargs='+', type=str, help="Plugins used by the MRF.")
    parser.add_argument("-t", "--target", type=str, help="File path to the system's source code.")
    args = parser.parse_args()
    return args
