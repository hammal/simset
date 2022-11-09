import argparse
import time
from typing import Callable, Dict, List
import simset
import logging
import os
import jinja2


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


def _create_folder_if_does_not_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def _bash_script(
    configuration_file_name: str,
    command_list: List[Dict[str, str]],
    description: str = '',
):

    _create_folder_if_does_not_exists('bash_scripts')

    if not os.path.splitdrive(configuration_file_name)[0] == "bash_scripts":
        configuration_file_name = os.path.join("bash_scripts", configuration_file_name)

    if not os.path.splitext(configuration_file_name)[1] == ".sh":
        configuration_file_name += ".sh"

    template = env.get_template('bash.sh.j2')

    if os.path.exists(configuration_file_name):
        os.remove(configuration_file_name)

    with open(configuration_file_name, 'w', encoding='utf-8') as f:
        f.write(template.render({"commands": command_list}))

    # make file readable and executable for user and group
    os.chmod(configuration_file_name, 0o550)

    return {"command": f"./{configuration_file_name}", "description": description}


def _rsync(
    configuration_file_name: str,
    path: str,
    dest: str,
    description: str = '',
    delete: bool = False,
):

    command_list = ["rsync", "-auzP"]

    if delete:
        command_list += ["--delete"]

    command_list += [
        f"'{path}'",
        f"'{dest}'",
    ]

    return _bash_script(
        configuration_file_name,
        [{"command": " ".join(command_list), "description": description}],
        description=description,
    )


def _ssh(remote: str, command: List[Dict[str, str]]):
    return [
        {
            "command": " ".join(
                [
                    "ssh",
                    f"{remote}",
                    f"'{command['command']}'",
                ]
            ),
            "description": command['description'],
        }
        for command in command
    ]


def _remote(
    configuration_file_name: str,
    remote: str,
    commands: List[Dict[str, str]],
    description: str = '',
    wait_to_return_data: bool = True,
):

    cwd = os.getcwd()
    cwd_basename = os.path.basename(cwd)

    command_list = [
        _rsync(
            'upload',
            cwd,
            f"{remote}:~/",
            description="copy data to remote",
            delete=True,
        )
    ]

    temp = [
        {
            "command": f"cd {cwd_basename}; {command['command']}",
            "description": command['description'],
        }
        for command in commands
    ]

    command_list += _ssh(remote, temp)

    command_list.append(
        _rsync(
            'download',
            f"{remote}:~/{cwd_basename}",
            '../',
            description="copy data from remote",
            delete=False,
        )
    )
    if not wait_to_return_data:
        command_list[-1][
            "command"
        ] = f"echo run '{command_list[-1]['command']}' when simulations have finished"

    return _bash_script(
        configuration_file_name,
        command_list,
        description=description,
    )


def simulate(simulation_function: Callable, index: int, save: Callable):
    """
    Execute simulation for index
    """
    if index < 1:
        raise Exception("Simulation index must be greater than 0")

    unsimulated_list = _load_unsimulated_file()
    if not index < (len(unsimulated_list) + 1) or index < 1:
        raise Exception(
            f"index {index} not within range 1 <= index < {len(unsimulated_list) + 1}"
        )
    item_hash = str(unsimulated_list[index - 1])
    args = simset._hash_to_args[item_hash]
    pretty_print_args = " ".join([f"{a} = {b}," for (a, b) in zip(args[0], args[1])])
    logger.info(f"Arguments: {pretty_print_args}")
    filename = unsimulated_list[index - 1]
    starting_time = time.time()
    res = simulation_function(*args[1][::-1])
    ending_time = time.time()
    res.time = {
        "time": ending_time - starting_time,
        "started": starting_time,
        "ended": ending_time,
    }

    # delete if target file exists
    full_filename = os.path.join(simset.data_folder, filename + ".data")
    if os.path.exists(full_filename):
        os.remove(full_filename)

    # save results
    save(res, full_filename)

    # set default permission to read only
    os.chmod(full_filename, 0o440)


def _local(number_of_simulations: int):

    configuration_file_name = "local_simulation.sh"

    error_folder = os.path.join('local', "err")
    output_folder = os.path.join('local', "out")

    _create_folder_if_does_not_exists('local')
    _create_folder_if_does_not_exists(error_folder)
    _create_folder_if_does_not_exists(output_folder)

    return [
        _bash_script(
            configuration_file_name,
            [
                {
                    "command": " ".join(
                        [
                            "time",
                            f"{simset.python_interpreter}",
                            f"{simset.script_name}",
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
                    "description": "execute on local",
                }
                for index in range(1, number_of_simulations + 1)
            ],
            description="local simulation",
        )
    ]


def _parallel(number_of_simulations: int):

    configuration_file_name = "parallel_simulation"

    error_folder = os.path.join('parallel', "err")
    output_folder = os.path.join('parallel', "out")

    _create_folder_if_does_not_exists('parallel')
    _create_folder_if_does_not_exists(error_folder)
    _create_folder_if_does_not_exists(output_folder)

    return [
        _bash_script(
            configuration_file_name,
            [
                {
                    "command": " ".join(
                        [
                            "parallel",
                            f"--jobs {simset.concurrent_jobs}",
                            f'"{simset.python_interpreter}',
                            f"{simset.script_name}",
                            "simulate",
                            "execute",
                            "-i",
                            "{}",
                            "1>",
                            os.path.join(output_folder, "{}.out"),
                            "2>",
                            os.path.join(error_folder, '{}.err"'),
                            ":::",
                            *[
                                str(index)
                                for index in range(1, number_of_simulations + 1)
                            ],
                        ]
                    ),
                    "description": "execute using gnu parallel command",
                }
            ],
            description="local simulation",
        )
    ]


def _remote_parallel(number_of_simulations: int, remote: str):

    configuration_file_name = "remote_parallel_simulation"

    return [
        _remote(
            configuration_file_name,
            remote,
            _parallel(number_of_simulations),
            description="remote parallel simulation",
        )
    ]


def _euler(number_of_simulations: int):

    configuration_file_name = "euler_simulation"

    error_folder = os.path.join('euler', "err")
    output_folder = os.path.join('euler', "out")

    _create_folder_if_does_not_exists('euler')
    _create_folder_if_does_not_exists(error_folder)
    _create_folder_if_does_not_exists(output_folder)

    output_file_name = os.path.join(output_folder, "%I.out")
    error_file_name = os.path.join(error_folder, "%I.err")

    euler_command = [
        f'bsub -J "{os.path.basename(os.getcwd())}[1-{number_of_simulations}]"',
        f'-oo "{output_file_name}"',
        f'-eo "{error_file_name}"',
        f'-R "rusage[mem={simset.memory_requirement}]"',
    ]

    if simset.euler_email:
        euler_command.append('-B')
        euler_command.append('-N')

    if simset.euler_number_of_cores:
        euler_command.append(f'-n {simset.euler_number_of_cores}')

    if simset.euler_wall_time:
        euler_command.append(
            f"-W {simset.euler_wall_time['hours']}:{simset.euler_wall_time['minutes']}"
        )

    euler_command.append(
        f'"{simset.python_interpreter} {simset.script_name} simulate execute -i \$LSB_JOBINDEX"'
    )

    return [
        _remote(
            configuration_file_name,
            "euler",
            [
                {
                    "command": " ".join(euler_command),
                    "description": "submit batch job to bsub command",
                }
            ],
            description="simulate on euler",
            wait_to_return_data=False,
        )
    ]


def _condor(number_of_simulations: int):
    configuration_file_name = "condor_simulation"

    return [
        _remote(
            configuration_file_name,
            "isitux",
            _condor_submit(number_of_simulations),
            description="simulate on condor",
            wait_to_return_data=False,
        )
    ]


def _condor_submit(number_of_simulations: int):

    configuration_file_name = os.path.join('condor', 'configuration.condor')

    _create_folder_if_does_not_exists('condor')
    _create_folder_if_does_not_exists('condor/log')
    _create_folder_if_does_not_exists('condor/err')
    _create_folder_if_does_not_exists('condor/out')

    # condor script

    command = _bash_script(
        "condor_executable",
        [
            # {
            #     "description": "check python",
            #     "command": " ".join(
            #         [
            #             "which",
            #             f"{simset.python_interpreter}",
            #         ]
            #     ),
            # },
            # {
            #     "description": "echo condor execution command",
            #     "command": " ".join(
            #         [
            #             "echo",
            #             "/home/merik/miniconda3/bin/python3",
            #             "main.py",
            #             "simulate",
            #             "execute",
            #             "-i",
            #             "$(1)",
            #         ]
            #     ),
            # },
            # {
            #     "description": "echo process",
            #     "command": " ".join(
            #         [
            #             "echo",
            #             "$(Process)"
            #         ]
            #     ),
            # },
            {
                "description": "condor simulation",
                "command": " ".join(
                    [
                        # f"{simset.python_interpreter}",
                        "/home/merik/miniconda3/bin/python3",
                        f"{simset.script_name}",
                        "simulate",
                        "execute",
                        "-i",
                        "$(Process)",
                    ]
                ),
            }
        ],
        "condor simulation",
    )

    # Create the simset_setup file
    template = env.get_template('configuration.condor.j2')

    if os.path.exists(configuration_file_name):
        os.remove(configuration_file_name)

    with open(configuration_file_name, 'w', encoding='utf-8') as f:
        f.write(
            template.render(
                {
                    # "directory": os.getcwd(),
                    "executable": command['command'][2:],
                    "arguments": "$(Process)",
                    "condor_log_folder": "condor/log",
                    "condor_out_folder": "condor/out",
                    "condor_err_folder": "condor/err",
                    "number_of_simulations": str(int(number_of_simulations)),
                    "configuration_file_name": configuration_file_name,
                    "memory_requirement": simset.memory_requirement,
                }
            )
        )

    os.chmod(configuration_file_name, 0o440)

    return [
        {
            "description": "submit batch job to condor",
            "command": f"condor_submit {configuration_file_name}",
        }
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
    elif parser.backend == "parallel":
        commands += _parallel(number_of_simulations)
    elif parser.backend == "remote":
        commands += _remote_parallel(number_of_simulations, parser.host)
    else:
        raise NotImplementedError
    for command in commands:
        print(command['description'], '\n')
        print(command['command'], '\n\n')
