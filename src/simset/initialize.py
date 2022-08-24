import os
import logging
import jinja2
import simset
from itertools import chain

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
    template = _env.get_template('simset_setup.py.j2')
    with open(filename, 'w') as f:
        f.write(template.render({"path": path, "main_file": _filename}))
    template = _env.get_template('README.md.j2')
    with open(os.path.join(path, 'README.md'), 'w') as f:
        f.write(template.render({}))
    print(readme_text)


def _remove_folder_if_sure(path: str):
    if os.path.exists(path):
        logger.info(f"removing: {path} and its contents")
        for root, dirs, files in os.walk(path, topdown=True):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir_name in dirs:
                folder_path = os.path.join(root, dir_name)
                _remove_folder_if_sure(folder_path)
                os.removedirs(folder_path)


def clean(path: str = os.getcwd(), force: bool = False):
    """
    cleanup simset files
    """
    if not force:
        descision = str(
            input(
                f'\nAre you sure you want to delete {_filename} and all simulation data?\ny/n\n'
            )
        ).lower()
        if descision.lower() == 'yes' or descision == 'y':
            logger.info("Use --force option to skip this validation step")
            pass
        else:
            logger.info("\nclean command aborted.")
            return

    logger.info(f"cleaning path: {path}")
    # remove main.py
    filename = os.path.join(path, _filename)
    if os.path.exists(filename):
        logger.info(f"removing: {filename}")
        os.remove(filename)

    # remove data files
    data_folder = os.path.join(path, simset.data_folders[0])
    _remove_folder_if_sure(data_folder)

    # remove local executables
    local_folder = os.path.join(path, 'local')
    _remove_folder_if_sure(local_folder)

    # remove condor files
    condor_folder = os.path.join(path, 'condor')
    _remove_folder_if_sure(condor_folder)

    # remove euler files
    euler_folder = os.path.join(path, 'euler')
    _remove_folder_if_sure(euler_folder)


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
        logger.info(f"{len(_out_files())} number of stdout files")


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
        logger.info(f"{len(_err_files())} number of stderr files")


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