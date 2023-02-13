import argparse
import logging
from typing import List, Set
from paramiko.ssh_exception import SSHException
from netmiko import ConnectHandler, NetmikoBaseException
from .loader import load_yaml, LoaderException, ConfigModel


logger = logging.getLogger('trawl.commands')


#
# Command implementation
#

def apply_cmd(cli_args: argparse.Namespace) -> None:
    """
    Apply commands as per spec file
    :param cli_args: Parsed CLI args
    :return: None
    """
    try:
        run_spec = load_yaml(ConfigModel, 'config', cli_args.file)
    except LoaderException as ex:
        logger.critical(f"Failed loading spec file: {ex}")
        return

    for prompt_arg in cli_args.prompt_arguments:
        if getattr(cli_args, prompt_arg.argument) is None:
            setattr(cli_args, prompt_arg.argument, prompt_arg())

    output_buffer: List[str] = []
    pattern_match_set: Set[str] = set()
    for node_name, node_info in run_spec.devices.items():
        logger.info(f"[{node_name}] Starting session to {node_info.address}")
        try:
            with ConnectHandler(device_type=node_info.device_type, host=str(node_info.address), username=cli_args.user,
                                password=cli_args.password) as session:
                for command in run_spec.commands:
                    logger.info(f"[{node_name}] Sending '{command.cmd}'")
                    output_buffer.append(f"### {node_name} - {command.cmd} ###")

                    cmd_output = session.send_command(command.cmd)
                    output_buffer.append(cmd_output)
                    output_buffer.append("")

                    if command.find is not None:
                        matches = command.find.findall(cmd_output)
                        if matches:
                            logger.info(f"[{node_name}] Pattern '{command.find.pattern}' matched {len(matches)} times, "
                                        f"first match: {matches[0]}")
                            pattern_match_set.add(node_name)
                        else:
                            logger.info(f"[{node_name}] Pattern '{command.find.pattern}' did not match")

        except (NetmikoBaseException, SSHException) as ex:
            logger.critical(f"[{node_name}] Connection error: {ex}")

        logger.info(f"[{node_name}] Closed session")
        output_buffer.append("")

    if pattern_match_set:
        logger.warning(f"Pattern matches found in the output from these devices: {', '.join(sorted(pattern_match_set))}")
    else:
        logger.info("No pattern matches found in any device command output")

    with open(cli_args.save, 'w') as f:
        f.write('\n'.join(output_buffer))
    logger.info(f"Saved output from commands to '{cli_args.save}'")


def preview_cmd(cli_args: argparse.Namespace) -> None:
    """
    Preview commands as per spec file
    :param cli_args: Parsed CLI args
    :return: None
    """
    try:
        run_spec = load_yaml(ConfigModel, 'config', cli_args.file)
    except LoaderException as ex:
        logger.critical(f"[Preview] Failed loading spec file: {ex}")
        return

    for node_name, node_info in run_spec.devices.items():
        logger.info(f"[Preview][{node_name}] Starting session to {node_info.address}")
        for command in run_spec.commands:
            logger.info(f"[Preview][{node_name}] Sending '{command.cmd}'")

            if command.find is not None:
                logger.info(f"[Preview][{node_name}] Check command output for pattern '{command.find.pattern}'")

        logger.info(f"[Preview][{node_name}] Closed session")


def schema_cmd(cli_args: argparse.Namespace) -> None:
    """
    Generate JSON schema for spec file
    :param cli_args: Parsed CLI args
    :return: None
    """
    with open(cli_args.save, 'w') as schema_file:
        schema_file.write(ConfigModel.schema_json(indent=2))

    logger.info(f"Saved spec file schema as '{cli_args.save}'")
