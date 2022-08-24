from typing import Callable, List
import simset
import logging
import os
import jinja2
import argparse
from simset.initialize import _filename as _executable_name

logger = logging.getLogger(__name__)

_simulated_list_filename = os.path.join(".data", "unsimulated_list.txt")

env = jinja2.Environment(
    loader=jinja2.PackageLoader("simset", package_path="templates"),
    autoescape=jinja2.select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _save_unsimulated_file(list: List[str], filename: str = _simulated_list_filename):
    with open(filename, "w", encoding='utf-8') as f:
        f.writelines([l + "\n" for l in list])
        # pickle.dump(list, f, protocol=-1)
    # set default permission to read only
    os.chmod(filename, 0o660)


def _load_unsimulated_file(filename: str = _simulated_list_filename) -> List[str]:
    result_list = []
    with open(filename, "r", encoding='utf-8') as f:
        for line in f.readlines():
            result_list.append(line.split('\n')[0])
    return result_list


def _get_unsimulated_args():
    unsimulated = []
    simulated_hashes = simset._get_simulated_arg_hashes()
    for key in simset._hash_to_args:
        item_hash = key
        if item_hash not in simulated_hashes:
            unsimulated.append(item_hash)
    return unsimulated


def simulate(simulation_function: Callable, index: int, save: Callable):
    """
    Execute simulation for index
    """
    if index < 0:
        raise Exception("Simulation index must be greater than 0")

    unsimulated_list = _load_unsimulated_file()
    if not index < len(unsimulated_list) or index < 0:
        raise Exception(
            f"index {index} not within range 0 <= index < {len(unsimulated_list)}"
        )
    item_hash = str(unsimulated_list[index])
    args = simset._hash_to_args[item_hash]
    pretty_print_args = " ".join([f"{a} = {b}," for (a, b) in zip(args[0], args[1])])
    logger.info(f"Arguments: {pretty_print_args}")
    filename = unsimulated_list[index]
    res = simulation_function(*args[1])

    # delete if target file exists
    full_filename = os.path.join(simset.data_folders[0], filename + ".data")
    if os.path.exists(full_filename):
        os.remove(full_filename)

    # save results
    save(res, full_filename)

    # set default permission to read only
    os.chmod(full_filename, 0o440)


def _local(number_of_simulations: int):

    configuration_file_name = os.path.join("local", "simulate.sh")

    error_folder = os.path.join('local', "err")
    output_folder = os.path.join('local', "out")

    _create_folder_if_does_not_exists('local')
    _create_folder_if_does_not_exists(error_folder)
    _create_folder_if_does_not_exists(output_folder)

    template = env.get_template('bash.sh.j2')

    command_line = []
    for index in range(number_of_simulations):
        command_line.append(
            {
                "command": " ".join(
                    [
                        "python3",
                        f"{_executable_name}",
                        "simulate",
                        "execute",
                        "-i",
                        f"{index}",
                        "1>",
                        os.path.join(output_folder, f"{index}.out"),
                        "2>",
                        os.path.join(error_folder, f"{index}.err"),
                    ]
                ),
            }
        )

    if os.path.exists(configuration_file_name):
        os.remove(configuration_file_name)

    with open(configuration_file_name, 'w', encoding='utf-8') as f:
        f.write(
            template.render(
                {
                    "commands": command_line,
                }
            )
        )

    # make file readable and executable for user and group
    os.chmod(configuration_file_name, 0o550)

    return [
        "# Start simulations by typing the following into your terminal\n",
        f"./{configuration_file_name}\n",
    ]


def _create_folder_if_does_not_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def _condor(number_of_simulations: int):
    configuration_file_name = os.path.join('condor', 'configuration.condor')

    _create_folder_if_does_not_exists('condor')
    _create_folder_if_does_not_exists('condor/log')
    _create_folder_if_does_not_exists('condor/err')
    _create_folder_if_does_not_exists('condor/out')

    # Create the simset_setup file
    template = env.get_template('configuration.condor.j2')

    if os.path.exists(configuration_file_name):
        os.remove(configuration_file_name)

    with open(configuration_file_name, 'w', encoding='utf-8') as f:
        f.write(
            template.render(
                {
                    # "directory": os.getcwd(),
                    "executable": "python3",
                    "arguments": " ".join(
                        [_executable_name, "simulate", "execute", "-i", "$(Process)"]
                    ),
                    "condor_log_folder": "condor/log",
                    "condor_out_folder": "condor/out",
                    "condor_err_folder": "condor/err",
                    "number_of_simulations": str(int(number_of_simulations)),
                    "configuration_file_name": configuration_file_name,
                }
            )
        )

    os.chmod(configuration_file_name, 0o440)

    return [
        "# Start simulations by typing the following into your terminal\n",
        f"condor_submit {configuration_file_name}\n",
    ]


def _euler(number_of_simulations: int):

    configuration_file_name = os.path.join("euler", "simulate.sh")

    error_folder = os.path.join('euler', "err")
    output_folder = os.path.join('euler', "out")

    _create_folder_if_does_not_exists('euler')
    _create_folder_if_does_not_exists(error_folder)
    _create_folder_if_does_not_exists(output_folder)

    template = env.get_template('bash.sh.j2')

    command_line = [
        {
            "command": f"python {_executable_name} simulate execute -i \$LSB_JOBINDEX",
        }
    ]

    if os.path.exists(configuration_file_name):
        os.remove(configuration_file_name)

    with open(configuration_file_name, 'w', encoding='utf-8') as f:
        f.write(
            template.render(
                {
                    "commands": command_line,
                }
            )
        )

    # make file readable and executable for user and group
    os.chmod(configuration_file_name, 0o550)
    name = "simset"
    mem = 1024

    bsub_command = " ".join(
        [
            f"bsub -J {name}[0-{number_of_simulations - 1}]",
            f"-oo {os.path.abspath(output_folder)}/%I.out",
            f"-eo {os.path.abspath(output_folder)}/%I.err",
            f'-R "rusage[mem={mem}]"',
            f"< {os.path.abspath(configuration_file_name)}",
        ]
    )

    return [
        "# Start simulations by typing the following into your terminal\n",
        bsub_command,
        "\n",
    ]


def simulate_setup(simulation_function: Callable, parser: argparse.Namespace):
    """
    Configure simulation setup by plattform.
    """
    # check such that data folder exist
    simset._data_folder_exist()

    # check for unsimulated args combinations
    unsimulated = _get_unsimulated_args()
    _save_unsimulated_file(unsimulated)

    # local execution
    number_of_simulations = len(unsimulated)
    commands = []
    if parser.backend == "condor":
        commands += _condor(number_of_simulations)
    elif parser.backend == "euler":
        commands += _euler(number_of_simulations)
    elif parser.backend == "local":
        commands += _local(number_of_simulations)
    else:
        raise NotImplementedError
    print("\n".join(commands))
