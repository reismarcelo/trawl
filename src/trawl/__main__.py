"""
Trawl - Capture CLI commands and search for configurable patterns

"""
import os
import argparse
import logging
from datetime import datetime
from getpass import getpass
from pathlib import Path
from .__version__ import __version__ as version
from .commands import preview_cmd, apply_cmd, schema_cmd
from . import app_config


logger = logging.getLogger('trawl.main')


#
# Argparse utils
#

def non_empty_type(src_str: str) -> str:
    out_str = src_str.strip()
    if len(out_str) == 0:
        raise argparse.ArgumentTypeError('Value cannot be empty.')

    return out_str


def non_existing_file_type(filename: str) -> str:
    if Path(filename).exists():
        raise argparse.ArgumentTypeError(f'File "{filename}" already exists.')

    return filename


def existing_file_type(filename: str) -> str:
    if not Path(filename).exists():
        raise argparse.ArgumentTypeError(f'File "{filename}" not found.')

    return filename


class EnvVar(argparse.Action):
    def __init__(self, nargs=None, envvar=None, required=True, default=None, **kwargs):
        if nargs is not None:
            raise ValueError('nargs not allowed')
        if envvar is None:
            raise ValueError('envvar is required')

        default = os.environ.get(envvar) or default
        required = required and default is None
        super().__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class PromptArg:
    def __init__(self, argument, prompt, secure_prompt=False, validate=non_empty_type):
        self.argument = argument
        self.prompt = prompt
        self.prompt_func = getpass if secure_prompt else input
        self.validate = validate

    def __call__(self):
        while True:
            try:
                value = self.validate(self.prompt_func(self.prompt))
            except argparse.ArgumentTypeError as ex:
                print(f'{ex} Please try again, or ^C to terminate.')
            else:
                return value


#
# Entrypoint
#

def main():
    cli_parser = argparse.ArgumentParser(description=__doc__)
    cli_parser.add_argument("--version", action="version", version=f"Trawl Version {version}")
    commands = cli_parser.add_subparsers(title="commands")
    commands.required = True

    apply_parser = commands.add_parser("apply", help="apply commands as per spec file")
    apply_parser.set_defaults(cmd_handler=apply_cmd)
    apply_parser.add_argument('-u', '--user', metavar='<user>', action=EnvVar, required=False,
                              envvar='TRAWL_USER', type=non_empty_type,
                              help='username, can also be defined via TRAWL_USER environment variable. '
                                   'If neither is provided prompt for username.')
    apply_parser.add_argument('-p', '--password', metavar='<password>', action=EnvVar, required=False,
                              envvar='TRAWL_PASSWORD', type=non_empty_type,
                              help='password, can also be defined via TRAWL_PASSWORD environment variable. '
                                   ' If neither is provided prompt for password.')
    apply_parser.add_argument("-f", "--file", metavar="<filename>", default=app_config.loader_config.spec_file,
                              help="spec file containing instructions to execute (default: %(default)s)")
    apply_parser.add_argument("-s", "--save", metavar="<filename>", type=non_existing_file_type,
                              default=f"data_{datetime.now():%Y%m%d_%H%M%S}.zip",
                              help="save output to file (default: %(default)s)")
    apply_parser.add_argument("--keep-tmp", action='store_true', help="keep temporary directories")
    apply_parser.add_argument("--state-file", metavar="<filename>", default=app_config.loader_config.state_file,
                              help="state file (default: %(default)s)")
    apply_parser.add_argument("--ssh-config-file", metavar="<filename>", type=existing_file_type,
                              help="custom ssh configuration file to use")
    apply_parser.set_defaults(prompt_arguments=[
        PromptArg('user', 'Device username: '),
        PromptArg('password', 'Device password: ', secure_prompt=True)
    ])

    preview_parser = commands.add_parser("preview", help="preview commands as per spec file")
    preview_parser.add_argument("-f", "--file", metavar="<filename>", default=app_config.loader_config.spec_file,
                                help="spec file containing instructions to execute (default: %(default)s)")
    preview_parser.set_defaults(cmd_handler=preview_cmd)

    schema_parser = commands.add_parser("schema", help="generate spec file JSON schema")
    schema_parser.set_defaults(cmd_handler=schema_cmd)
    schema_parser.add_argument("-s", "--save", metavar="<filename>", default=f"spec_file_schema.json",
                               help="schema export filename (default: %(default)s)")

    cli_args = cli_parser.parse_args()
    try:
        cli_args.cmd_handler(cli_args)
    except KeyboardInterrupt:
        logger.critical("Interrupted by user")


if __name__ == '__main__':
    main()
