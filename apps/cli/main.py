import argparse
import signal
import sys
from typing import Any

from lib.logging import LogLevel, setup_logging

from .commands import dev, evaluate, ingest, search, setup, tokens, vectorize

COMMANDS = [
    dev,
    evaluate,
    ingest,
    search,
    setup,
    tokens,
    vectorize,
]

COMMON_ARGUMENTS = [
    {
        "name": "log-level",
        "type": str,
        "required": False,
        "choices": [level.value for level in LogLevel],
        "default": LogLevel.WARNING.value,
        "help": "Set the logging level (default: WARNING)",
    },
    {
        "name": "no-timestamp",
        "type": bool,
        "required": False,
        "default": False,
        "help": "Disable timestamps in log output",
    },
]


def signal_handler(sig: int, _: Any) -> None:
    """
    Handle Ctrl+C gracefully.

    Args:
        sig: Signal number
    """
    print("\n\nAborting...\n")
    sys.exit(0)


def validate_command_import(command):
    if not hasattr(command, "DEFINITION"):
        raise ValueError(f"Command {command} does not have DEFINITION")
    if not isinstance(command.DEFINITION, dict):
        raise ValueError(f"Command {command} DEFINITION is not a dictionary")

    if not hasattr(command, "main"):
        raise ValueError(f"Command {command} DEFINITION does not have main function")
    if not callable(command.main):
        raise ValueError(f"Command {command} DEFINITION main function is not callable")

    for argument in command.DEFINITION["arguments"]:
        if "name" not in argument:
            raise ValueError(
                f"Command {command} DEFINITION.arguments.{argument['name']} does not have a 'name' attribute"
            )
    return True


if __name__ == "__main__":
    # Set up signal handler for graceful interruption
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(
        description="OpenSearch CLI tool for data ingestion and search"
    )

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    for command in COMMANDS:
        validate_command_import(command)

        # Create subparser for this command
        command_parser = subparsers.add_parser(
            command.DEFINITION["name"],
            help=command.DEFINITION["description"],
        )

        # Add common arguments and command arguments and sort them alphabetically
        arguments = sorted(
            [*COMMON_ARGUMENTS, *command.DEFINITION["arguments"]],
            key=lambda x: x["name"],
        )

        # Add arguments to the subparser
        for argument in arguments:
            arg_name = argument["name"]
            # Extract kwargs, excluding "name" which is used for the flag name
            kwargs = {k: v for k, v in argument.items() if k != "name"}
            # Add the argument to the subparser
            command_parser.add_argument(f"--{arg_name}", **kwargs)

    args = parser.parse_args()

    # Setup logging based on CLI arguments
    setup_logging(level=args.log_level, include_timestamp=not args.no_timestamp)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    for command in COMMANDS:
        if args.command == command.DEFINITION["name"]:
            valid_argument_names = [
                arg["name"].replace("-", "_") for arg in command.DEFINITION["arguments"]
            ]
            command.main(
                **{key: value for key, value in vars(args).items() if key in valid_argument_names}
            )
            sys.exit(0)
