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
        session_args = {
            'device_type': node_info.device_type,
            'host':  str(node_info.address),
            'username': cli_args.user,
            'password': cli_args.password
        }
        try:
            with ConnectHandler(**session_args) as session:
                for command in run_spec.commands:
                    logger.info(f"[{node_name}] Sending '{command.send}'")
                    output_buffer.append(f"### {node_name} - {command.send} ###")

                    cmd_output = session.send_command(command.send,
                                                      expect_string=command.prompt_pattern,
                                                      read_timeout=command.timeout)
                    if command.find is not None:
                        matches = command.find.findall(cmd_output)
                        if matches:
                            match_info = (f"Pattern '{command.find.pattern}' found: {len(matches)} hits, first: "
                                          f"{'| '.join(matches[0]) if isinstance(matches[0], tuple) else matches[0]}")
                            pattern_match_set.add(node_name)
                        else:
                            match_info = f"Pattern '{command.find.pattern}' not found"

                        logger.info(f"[{node_name}] {match_info}")
                        output_buffer.append(f"- {match_info}")

                    output_buffer.append(cmd_output)
                    output_buffer.append("")

        except (NetmikoBaseException, SSHException) as ex:
            logger.critical(f"[{node_name}] Connection error: {ex}")

        logger.info(f"[{node_name}] Closed session")
        output_buffer.append("")

    if pattern_match_set:
        logger.warning(f"Search pattern found in the output from these devices: {', '.join(sorted(pattern_match_set))}")
    else:
        logger.info("Search patterns not found in any device command output")

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
            extra_info = ""
            if 'prompt_pattern' in command.__fields_set__:
                extra_info += f", prompt pattern: {command.prompt_pattern.pattern}"
            if 'timeout' in command.__fields_set__:
                extra_info += f", timeout: {command.timeout}"
            logger.info(f"[Preview][{node_name}] Sending '{command.send}'{extra_info}")

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
