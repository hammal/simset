import os as _os
from typing import Dict, Tuple, List

data_folders = [_os.path.join(_os.getcwd(), ".data")]

_arguments_list: List[Tuple] = []
_hash_to_args: Dict = {}

from dataclasses import dataclass
from . import initialize
from . import post_processing
from .simulate import _get_unsimulated_args
from .post_processing import _get_simulated_args
from .command_line import main
import logging as _logging
import hashlib

logger = _logging.getLogger(__name__)

# _simulations_file = _os.path.join()


def hash_to_filename(hashable: Tuple) -> str:
    """hash an args list into a hash hex"""
    return hashlib.sha256(str(hashable).encode()).hexdigest()


def data_path(filename: str):
    "return absolute path for filename"
    return _os.path.join(data_folders[0], filename + ".data")


def _get_simulated_arg_hashes():
    hashes = []
    for folder in data_folders:
        files = _os.listdir(folder)
        for file in files:
            basename = _os.path.basename(file)
            if basename.endswith(".data"):
                hashes.append(basename.split('.')[0])
    return hashes


def _data_folder_exist():
    if not _os.path.exists(data_folders[0]):
        _os.makedirs(data_folders[0])


def arg(name: str, list_of_args: List):
    """
    a decorator function which adds new arguments to simset
    """
    global _arguments_list
    global _hash_to_args
    _hash_to_args = {}
    if len(_arguments_list) > 0:
        temp = []
        for old_args in _arguments_list:  # type: ignore
            for new_arg in list_of_args:
                arg_tuple = ((name, *old_args[0]), (new_arg, *old_args[1]))
                temp.append(arg_tuple)
                _hash_to_args[hash_to_filename(arg_tuple)] = arg_tuple
        _arguments_list = temp
    else:
        for new_arg in list_of_args:
            arg_tuple = ((name,), (new_arg,))
            _arguments_list.append(arg_tuple)
            _hash_to_args[hash_to_filename(arg_tuple)] = arg_tuple

    def decorator(func):
        def inner(*args, **kwargs):
            if len(kwargs) > 0:
                raise Exception(f"all args must be positional not keywords: {kwargs}")
            return func(*args)

        return inner

    return decorator
