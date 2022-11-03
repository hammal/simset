import argparse
import os


def _parse_arguments() -> argparse.Namespace:
    """
    helper function for parsing input arguments
    """
    parser = argparse.ArgumentParser(
        prog='simset', description="configure simset environment."
    )
    parser.add_argument(
        "action",
        help="determine action",
        choices=['init', 'clean', 'copy'],
    )

    parser.add_argument(
        "-f",
        "--force",
        help="overwrite existing files",
        default=False,
        action='store_true',
    )
    parser.add_argument(
        "-p",
        "--path",
        help="specify folder for init action",
        default=os.getcwd(),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        default=False,
        action='store_true',
    )
    # parser.add_argument("--verbosity", help="increase output verbosity")

    return parser.parse_args()


def simulate_process_parser() -> argparse.Namespace:
    """
    The simulate and process command line program
    """
    parser = argparse.ArgumentParser(
        prog='simset', description="simulate or post-process HPC computations"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        default=False,
        action='store_true',
    )

    subparsers = parser.add_subparsers(
        title="action",
        description="determine which action to invoke",
        dest="action",
        required=True,
        help="choose an action...",
    )

    # create the parser for the "a" command
    simulate = subparsers.add_parser(
        'simulate', help='setup or execute the required simulations'
    )
    # The simulate subcommand
    simulate_subparsers = simulate.add_subparsers(
        title="simulate",
        dest="command",
        required=True,
        description="choose whether to setup or execute the simulations",
        help="setup or execute the required simulations?",
    )
    # The execute command
    simulate_execute_parser = simulate_subparsers.add_parser(
        'execute',
        help="execute a particular simulation",
        description="invoke a particular simulation setup"
    )
    simulate_execute_parser.add_argument(
        "-i",
        "--index",
        help="specify simulation index",
        type=int,
        nargs='?',
        required=True,
    )
    # The local simulation
    simulate_setup_parser = simulate_subparsers.add_parser(
        'setup',
        help="setup simulation files",
        description="instantiate the required simulation files for a particular computation backend"
    )
    simulate_setup_parser.add_argument('backend', choices=['local', 'parallel', 'condor', 'euler', 'remote'], help="choose a computation backed")
    simulate_setup_parser.add_argument('host', type=str, nargs="?", default="localhost", help="ssh remote host if applicable")

    subparsers.add_parser(
        'process', help='execute the post-processing function', description="runs the post_processing_function(...) function in the main.py file sequentially over all available argument combinations"
    )

    subparsers.add_parser(
        'info', help="display information about current state of simulations"
    )

    log = subparsers.add_parser(
        'output', help="display simulation output"
    )
    log.add_argument(
        "index",
        help="specify file index",
        type=int,
        nargs='?',
        default=-1
    )

    err = subparsers.add_parser(
        'error', help="display and mange simulation errors"
    )
    err.add_argument(
        "index",
        help="specify file index",
        type=int,
        nargs='?',
        default=-1
    )

    return parser.parse_args()
