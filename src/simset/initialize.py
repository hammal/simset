import os
import logging
from typing import List
import jinja2
import simset
from itertools import chain
import simset

logger = logging.getLogger(__name__)

_filename = "main.py"


def init(path: str = os.getcwd(), force: bool = False):
    """
    Initialize a simulation folder

    Parameters
    ----------
    path: `str`
        path to the folder.
    force: `bool`
        if true overwrites exsisting files, defaults to False.
    """

    logger.info(f"initializing path: {path}")
    filename = os.path.join(path, _filename)
    if os.path.exists(filename) and not force:
        logger.info(f"{_filename} file already exsists. use --force to overwrite")
        exit(1)
    _env = jinja2.Environment(
        loader=jinja2.PackageLoader("simset", package_path="templates"),
        autoescape=jinja2.select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    readme_text = f"""
You successfully initialized the folder: { path }

Next step is to include your own simulation and post-processing code into the file

{ _filename }

List available commands by

python {_filename} -h

More information and a small tutorial can be found in the README.md file
included in the initialized folder.
    """

    # Create the simset_setup file
    template = _env.get_template('main.py.j2')
    with open(filename, 'w') as f:
        f.write(template.render({"path": path, "main_file": _filename}))
    template = _env.get_template('README.md.j2')
    with open(os.path.join(path, 'README.md'), 'w') as f:
        f.write(template.render({}))
    print(readme_text)

    # create .data folder if it does not exist
    simset.simulate._create_folder_if_does_not_exists(".data")
    with open(os.path.join(os.path.join(path, '.data'), 'README.md'), 'w') as f:
        f.write(
            "Please don't manually edit files in this folder. It is used by simset to store simulations and manage simulation scheduling"
        )


def _remove_folder_if_sure(path: str, exclude: List[str] = []):
    if os.path.exists(path):
        logger.info(f"removing: {path} and its contents")
        for root, dirs, files in os.walk(path, topdown=True):
            for file in files:
                if file not in exclude:
                    os.remove(os.path.join(root, file))
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                _remove_folder_if_sure(folder_path)
                os.removedirs(folder_path)


def clean(path: str = os.getcwd(), force: bool = False):
    """
    cleanup simset files
    """
    logger.info(f"cleaning path: {path}")
    if force:
        descision = str(
            input(f'\nAre you sure you want to delete {_filename}?\ny/n\n')
        ).lower()
        if descision.lower() == 'yes' or descision == 'y':
            logger.info("Use --force option to skip this validation step")
            pass
        else:
            logger.info("\nclean command aborted.")
            return

        # remove main.py
        filename = os.path.join(path, _filename)
        if os.path.exists(filename):
            logger.info(f"removing: {filename}")
            os.remove(filename)

    # Remove execution folders
    for folder in ['local', 'condor', 'euler', 'parallel', 'remote', 'bash_scripts']:
        _remove_folder_if_sure(os.path.join(path, folder))

    # Remove data files
    descision = str(
        input(f'\nAre you sure you want to delete all simulation data?\ny/n\n')
    ).lower()
    if descision.lower() == 'yes' or descision == 'y':
        _remove_folder_if_sure(simset.data_folders[0], ['README.md'])
        pass
    else:
        logger.info("data files not deleted")
        return


def copy(src_path: str, dest_path: str):
    "copy simset folder from src to dest."
    raise NotImplementedError


def _all_files(path: str):
    res = [""]
    if os.path.exists(path):
        for root, dirs, files in os.walk(path, topdown=True):
            for file in files:
                res.append(os.path.join(root, file))
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                res = res + _all_files(folder_path)
    return res


def _out_files():
    log_folders = ["local/out", "condor/out", "euler/out"]

    def out_files(filename: str):
        if filename.endswith(".out"):
            return True
        return False

    all_files = [_all_files(folder) for folder in log_folders]
    return list(filter(out_files, chain(*all_files)))


def _err_files():
    err_folders = ["local/err", "condor/err", "euler/err"]

    def out_files(filename: str):
        if filename.endswith(".err"):
            return True
        return False

    all_files = [_all_files(folder) for folder in err_folders]
    return list(filter(out_files, chain(*all_files)))


def out(index: int = -1):
    """Display simulation logs"""

    if index >= 0:
        # retrieve a specific log
        def file_with_index(filename: str):
            if filename.endswith(f"{index}.out"):
                return True
            return False

        candidates = list(filter(file_with_index, _out_files()))
        if len(candidates) == 1:
            with open(candidates[0], 'r') as f:
                print(f.read())
        else:
            logger.info("Multiple candidates for index: {index}\nNamely: {candidates}")
    else:
        number_of_out_files = len(_out_files())
        logger.info(f"{number_of_out_files} number of stdout files.")
        if number_of_out_files > 0:
            logger.info(
                f"\n\nTo display a specific output file use the index [0-{number_of_out_files-1}] option"
            )


def error(index: int = -1):
    """Display simulation errors"""

    if index >= 0:
        # retrieve a specific log
        def file_with_index(filename: str):
            if filename.endswith(f"{index}.err"):
                return True
            return False

        candidates = list(filter(file_with_index, _err_files()))
        if len(candidates) == 1:
            with open(candidates[0], 'r') as f:
                print(f.read())
        else:
            logger.info("Multiple candidates for index: {index}\nNamely: {candidates}")
    else:
        number_of_error_files = len(_err_files())
        logger.info(f"{number_of_error_files} number of stderr files.")
        if number_of_error_files > 0:
            logger.info(
                f"To display a specific error use the index [0-{number_of_error_files-1}] option"
            )


def info():
    """
    Summarize the simset folder
    """
    simset._data_folder_exist()
    simulated = simset._get_simulated_args()

    size = sum(
        [os.path.getsize(simset.data_path(item_hash)) for item_hash in simulated]
    )
    if size < (1 << 10):
        simulated_size = f"{size} B"
    elif size < (1 << 20):
        simulated_size = f"{size // (1 << 10)} kB"
    elif size > (1 << 30):
        simulated_size = f"{size // (1 << 20)} MB"
    else:
        simulated_size = f"{size // (1 << 30)} GB"

    unsimulated = simset._get_unsimulated_args()

    print(
        f"""
    {len(simulated)} - simulated ({simulated_size})
    {len(unsimulated)} - unsimulated
    """
    )


def info_unsimulated():
    """
    print parameter configurations of unfinished simulations
    """
    spacing = 10  # number of fixed width for value field
    unsimulated = simset._get_unsimulated_args()

    print("\nunsimulated simulations:")
    for key in unsimulated:
        pairs = zip(simset._hash_to_args[key][0], simset._hash_to_args[key][1])
        print(
            "...{}: ".format(key[-8:])
            + "\t".join(
                [
                    f"{key}: {value}" + " " * (spacing - len(str(value)))
                    for key, value in pairs
                ]
            )
        )

    print()
