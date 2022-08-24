import logging
from typing import Callable
import os
import simset

logger = logging.getLogger(__name__)


def _get_simulated_args():
    simulated = []
    simulated_hashes = simset._get_simulated_arg_hashes()
    for key in simset._hash_to_args:
        if key in simulated_hashes:
            simulated.append(key)
    return simulated


def post_processing(processing_function, load: Callable):
    """
    load and pass results to processing_function
    """
    finished_simulated = _get_simulated_args()

    def _results():
        filenames = [simset.data_path(item_hash) for item_hash in finished_simulated]
        for filename in filenames:
            yield load(filename)

    processing_function(_results())
