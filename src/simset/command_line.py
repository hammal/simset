from typing import Callable
from simset.initialize import init, clean, info, out, error
from simset.parser import _parse_arguments, simulate_process_parser
from simset.simulate import simulate, simulate_setup, _get_unsimulated_args
from simset.post_processing import post_processing
import logging
import time

# Set logging level
logger = logging.getLogger(__name__)


def main():
    """
    The main command line function
    """
    args = _parse_arguments()
    logger.debug(f"command line args where: {args}")

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="")

    if args.action == 'init':
        init(path=args.path, force=args.force)
        exit(0)

    if args.action == 'clean':
        clean(path=args.path, force=args.force)
        exit(0)

    # if args.action == 'copy':
    #     copy(src=args.path, dest=args.path)
    #     exit(0)

    logger.debug("No suitable action was found")
    exit(1)


def command_line_simulate_process(
    simulate_function: Callable,
    process_function: Callable,
    save: Callable,
    load: Callable,
):
    """
    The simulate or process command line function

    Parameters
    ----------
    simulate_function: (args) -> res
        the simulation function to which each argument combination should be passed in simulation.
    process_function: (res1, ...)
        the function which will process the result
    """
    args = simulate_process_parser()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="")

    if args.action == 'process':
        post_processing(process_function, load)
        exit(0)
    elif args.action == 'simulate':
        if args.command == "execute":
            simulate(simulate_function, args.index, save)
        elif args.command == "setup":
            simulate_setup(simulate_function, args)
        else:
            # debug
            if len(_get_unsimulated_args()) > 1:
                logger.info("Dryrun, testing a simulation")
                tic = time.perf_counter()
                simulate(simulate_function, 0, save)
                toc = time.perf_counter()
                logger.info(
                    f"Time: the simulation took {toc - tic:0.2f} seconds to complete"
                )
            else:
                logger.error("No unsimulated argument configurations to simulate")
                exit(1)
        exit(0)
    elif args.action == 'output':
        out(args.index)
        exit(0)
    elif args.action == 'error':
        error(args.index)
        exit(0)
    elif args.action == 'info':
        info()
        exit(0)
    else:
        logger.debug("No suitable action was found")
        exit(1)
