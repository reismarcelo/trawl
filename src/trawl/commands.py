import argparse
import logging
import re
from typing import List, Set, Iterable, Optional, Pattern, NamedTuple
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
import yaml
from paramiko.ssh_exception import SSHException
from netmiko import ConnectHandler, NetmikoBaseException, SCPConn, BaseConnection
from .loader import load_yaml, LoaderException, ConfigModel, StateModel


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

    downloaded_set: Set[DownloadedFileInfo]
    try:
        downloaded_set = {file_info for file_info in load_yaml(StateModel, 'state', cli_args.state_file).downloads}
    except LoaderException:
        downloaded_set = set()

    for prompt_arg in cli_args.prompt_arguments:
        if getattr(cli_args, prompt_arg.argument) is None:
            setattr(cli_args, prompt_arg.argument, prompt_arg())

    # Temporary directory
    base_path = Path(str(uuid4()))
    base_path.mkdir(parents=True)

    output_buffer: List[str] = []
    pattern_match_set: Set[str] = set()
    for node_name, node_info in run_spec.devices.items():
        logger.info(f"[{node_name}] Starting session to {node_info.address}")
        session_args = {
            'device_type': node_info.device_type,
            'host':  str(node_info.address),
            'username': cli_args.user,
            'password': cli_args.password,
            'ssh_config_file': cli_args.ssh_config_file
        }
        try:
            with ConnectHandler(**session_args) as session:
                for command in run_spec.commands:
                    logger.info(f"[{node_name}] Sending '{command.send}'")
                    output_buffer.append(f"### {node_name} - {command.send} ###")

                    cmd_output = session.send_command(command.send,
                                                      expect_string=command.prompt_pattern,
                                                      read_timeout=command.timeout)
                    session.find_prompt()
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
                    if download.file_pattern is None:
                        logger.info(f"[{node_name}] Downloading all files in '{download.directory}'")
                    else:
                        logger.info(f"[{node_name}] Downloading files matching "
                                    f"'{download.directory}/{download.file_pattern.pattern}'")

                    download_path = Path(base_path, node_name)
                    download_path.mkdir(parents=True, exist_ok=True)
                    session.find_prompt()
                    dir_output = session.send_command(f"dir {download.directory}",
                                                      expect_string=cli_args.download_prompt_pattern,
                                                      read_timeout=download.timeout)

                    for filename in match_files(dir_output, file_pattern=download.file_pattern):
                        download_info = DownloadedFileInfo(node_name, download.directory, filename)
                        if download_info in downloaded_set:
                            logger.debug(f"[{node_name}] Download '{download.directory}/{filename}' skipped")
                            continue

                        succeeded = scp_get_file(session,
                                                 src_file=f'{download.directory}/{filename}',
                                                 dst_file=str(Path(download_path, filename)),
                                                 timeout=download.timeout)
                        if succeeded:
                            downloaded_set.add(download_info)
                            logger.info(f"[{node_name}] Download '{download.directory}/{filename}' complete")
                        else:
                            logger.warning(f"[{node_name}] Download '{download.directory}/{filename}' failed")

        except (NetmikoBaseException, SSHException) as ex:
            logger.critical(f"[{node_name}] Connection error: {ex}")

        logger.info(f"[{node_name}] Closed session")
        output_buffer.append("")

    if pattern_match_set:
        logger.warning(f"Search pattern found in the output from these devices: {', '.join(sorted(pattern_match_set))}")
    else:
        logger.info("Search patterns not found in any device command output")

    with open(Path(base_path, 'command_output.txt'), 'w') as f:
        f.write('\n'.join(output_buffer))

    with open(cli_args.state_file, 'w') as state_f:
        yaml.safe_dump(StateModel(downloads=list(downloaded_set)).dict(), state_f)

    archive_create(cli_args.save, base_path)
    if not cli_args.keep_tmp:
        rmtree(base_path, ignore_errors=True)

    logger.info(f"Saved output to '{cli_args.save}'")


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
                options += f", timeout: {command.timeout:.0f}s"
            logger.info(f"[Preview][{node_name}] Sending '{command.send}'{options}")

            if command.find is not None:
                logger.info(f"[Preview][{node_name}] Check command output for pattern '{command.find.pattern}'")

        for download in (d for d in run_spec.downloads if not d.devices or node_name in d.devices):
            options = ""
            if 'timeout' in download.__fields_set__:
                options += f", timeout: {download.timeout:.0f}s"

            if download.file_pattern is None:
                logger.info(f"[Preview][{node_name}] Downloading all files in '{download.directory}'{options}")
            else:
                logger.info(f"[Preview][{node_name}] Downloading files matching "
                            f"'{download.directory}/{download.file_pattern.pattern}'{options}")

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


#
# Utility functions
#

def match_files(dir_cmd_output: str, file_pattern: Optional[Pattern] = None) -> Iterable[str]:
    dir_cmd_pattern = re.compile(r'^\s*\d+\s+-(?:\S+\s+)+?(\S+)\s*$', flags=re.MULTILINE)
    return (
        file for file in dir_cmd_pattern.findall(dir_cmd_output) if file_pattern is None or file_pattern.search(file)
    )


def scp_get_file(ssh_con: BaseConnection, src_file: str, dst_file: str, timeout: float) -> bool:
    scp_session = SCPConn(ssh_con, socket_timeout=timeout)
    try:
        scp_session.scp_get_file(source_file=src_file, dest_file=dst_file)
    except EOFError:
        pass
    finally:
        scp_session.close()

    return Path(dst_file).exists()


def archive_create(archive_filename: str, src_dir: Path) -> None:
    """
    Create a zip archive with the contents of src_dir
    @param archive_filename: zip archive filename
    @param src_dir: directory to be archived, as Path object
    """
    with ZipFile(archive_filename, mode='w', compression=ZIP_DEFLATED) as archive_file:
        for member_path in src_dir.rglob("*"):
            archive_file.write(member_path, arcname=member_path.relative_to(src_dir))

    return


class DownloadedFileInfo(NamedTuple):
    device: str
    directory: str
    filename: str

