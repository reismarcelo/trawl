import argparse
import logging
from typing import List, Set
from pathlib import Path
from paramiko.ssh_exception import SSHException
from netmiko import ConnectHandler, NetmikoBaseException, file_transfer, SCPConn
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

    base_dir = Path(cli_args.save)
    base_dir.mkdir(parents=True, exist_ok=True)

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

                for download in (d for d in run_spec.downloads if not d.devices or node_name in d.devices):
                    logger.info(f"[{node_name}] Downloading '{download.directory}/{download.filename}'")

                    download_dir = Path(base_dir, node_name)
                    download_dir.mkdir(parents=True, exist_ok=True)

                    if download.alt_method:
                        scp_session = SCPConn(session, socket_timeout=download.timeout)
                        try:
                            scp_session.scp_get_file(source_file=f'{download.directory}/{download.filename}',
                                                     dest_file=f"{download_dir}/{download.filename}")
                        except EOFError:
                            pass
                        finally:
                            scp_session.close()

                        logger.info(f"[{node_name}] Download complete")
                    else:
                        try:
                            transfer_result = file_transfer(session,
                                                            direction='get',
                                                            file_system=download.directory,
                                                            source_file=download.filename,
                                                            dest_file=f"{download_dir}/{download.filename}",
                                                            socket_timeout=download.timeout,
                                                            verify_file=download.checksum,
                                                            overwrite_file=download.overwrite)
                            logger.info(f"[{node_name}] Download "
                                        f"{'complete' if transfer_result['file_transferred'] else 'not needed'}")
                        except EOFError:
                            pass

        except (NetmikoBaseException, SSHException) as ex:
            logger.critical(f"[{node_name}] Connection error: {ex}")
        except ValueError as ex:
            logger.critical(f"[{node_name}] Execution error: {ex}")

        logger.info(f"[{node_name}] Closed session")
        output_buffer.append("")

    if pattern_match_set:
        logger.warning(f"Search pattern found in the output from these devices: {', '.join(sorted(pattern_match_set))}")
    else:
        logger.info("Search patterns not found in any device command output")

    with open(Path(base_dir, 'command_output.txt'), 'w') as f:
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
            options = ""
            if 'prompt_pattern' in command.__fields_set__:
                options += f", prompt pattern: {command.prompt_pattern.pattern}"
            if 'timeout' in command.__fields_set__:
                options += f", timeout: {command.timeout}"
            logger.info(f"[Preview][{node_name}] Sending '{command.send}'{options}")

            if command.find is not None:
                logger.info(f"[Preview][{node_name}] Check command output for pattern '{command.find.pattern}'")

        for download in (d for d in run_spec.downloads if not d.devices or node_name in d.devices):
            options = ""
            if 'checksum' in download.__fields_set__:
                options += f", checksum: {download.checksum}"
            if 'overwrite' in download.__fields_set__:
                options += f", overwrite: {download.overwrite}"
            if 'timeout' in download.__fields_set__:
                options += f", timeout: {download.timeout}"
            logger.info(f"[Preview][{node_name}] Downloading '{download.directory}/{download.filename}'{options}")

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
