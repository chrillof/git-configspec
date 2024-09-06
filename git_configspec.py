#!/usr/bin/env python3

import re
import sys

import logging
import traceback
import subprocess

from typing import Iterable
from dataclasses import dataclass
from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

logger = logging.getLogger(__name__)

# Regexes
_COMMENT = re.compile(r"(\s*|\#.*)$")
_CS_SCOPE_RULE = re.compile(r"""(?P<scope>element)\s+
                                (?P<pattern>(?:\".+\"|.+?))\s+
                                (?P<selector>\S+)
                                ([\t ]+(?P<optional>.*))?""",
                            re.X)

@dataclass
class ConfigSpecRule:
    """ A config spec rule that can be transformed into a git command. """

    scope: str
    pattern: str
    selector: str

    def __lt__(self, other) -> bool:
        # If the pattern is shorter OR is the asterisk (*), then this rule
        # shall be sorted first
        return len(self.pattern) < len(other.pattern) or self.pattern == "*"

@dataclass
class PreparedCommand:
    """ A command to be executed. """

    gitdir: Path
    selector: str
    pattern: Path

    def __str__(self) -> str:
        return ' '.join(self.as_tuple())

    def as_tuple(self) -> tuple[str]:
        """ Retrieve this command as a tuple, ready to execute by e.g. 
            subprocess.run.
        """

        return ('git', '-C', str(self.gitdir), 'checkout',
                '--recurse-submodules',
                self.selector, '--', str(self.pattern))

def parse_file(path: Path) -> Iterable[ConfigSpecRule]:
    """ Parses the file at the given location and extracts the rules. """

    with open(path, 'r', encoding="utf8") as config_spec:
        return parse_iterable(config_spec)

def parse_iterable(config_spec: Iterable[str]) -> Iterable[ConfigSpecRule]:
    """ Parses the given iterable as a sequence of config spec rules. """

    data = []
    logger.info("Parsing config spec rules.")
    for line_no, line in enumerate(config_spec, start=1):
        if line:
            if not _COMMENT.match(line):
                matches = _CS_SCOPE_RULE.match(line)

                if matches:
                    logging.debug("Match @ %2d: %s", line_no, line.strip())
                    rule = ConfigSpecRule(
                            scope=matches.group("scope"),
                            pattern=matches.group("pattern").strip("\""),
                            selector=matches.group("selector"))
                    data.append(rule)
                    logging.info("Rule: %s", rule)
                else:
                    # Its not a comment nor a blank line.
                    logger.warning("Expected rule on line %d: %s",
                                   line_no, line)
    return data

def to_commands(spec: Iterable[ConfigSpecRule],
                relative_root: Path = Path("."),
                ignore_nonexisting: bool = False) -> Iterable[PreparedCommand]:
    """ Transforms the set of rules to the appropriate git commands.

        relative_root: Path
            describes the location of the config spec, to which all commands
            are relative to if the patterns are relative.

        ignore_nonexisting: bool
            determines whether to ignore nonexisting paths in the pattern.
    """

    logger.debug("Relative root (config spec location): %s", relative_root)
    command_list = []
    for rule in spec:
        pattern = Path(rule.pattern)
        gitdir = (relative_root / pattern).parent
        if ignore_nonexisting or gitdir.exists():
            command_list.append(
                PreparedCommand(gitdir=gitdir,
                                selector=rule.selector,
                                pattern=pattern.relative_to(gitdir)))
        else:
            raise FileNotFoundError(f"Non-existing directory: {gitdir}")

    return command_list

def apply(commands_to_apply: Iterable[PreparedCommand],
          dry_run: bool = True) -> None:
    """ Executes the sequence of commands in order. 

        If the dry_run flag is True, the output will print to stderr what it
        would do.
    """

    for cmd in commands_to_apply:
        if dry_run:
            print(f"Would run: {str(cmd)}", file=sys.stderr)
        else:
            logger.info("Executing: %s ", cmd)
            subprocess.run(cmd.as_tuple(), check=True)


if __name__ == "__main__":
    parser = ArgumentParser(description="Git ConfigSpec impersonator. Mimics "
                            "the ClearCase ConfigSpec behaviour for a set of "
                            "repositories.",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("CONFIG_SPEC", default="CONFIG_SPEC", nargs="?",
                        type=Path, help="The config spec to use.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--apply", action="store_true",
                        help="Apply the config spec by performing checkout "
                        "based on the rules.")
    grp.add_argument("--stdout", action="store_true",
                        help="Print git commands to stdout instead of "
                        "executing them.")
    parser.add_argument("--ignore-nonexisting", action="store_true",
                        help="Do not check whether target patterns exist (i.e. "
                        "files and folders) before applying commands.")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Set verbosity of messages.")

    # Define error codes
    E_NO_CONFIG_SPEC = 1
    E_FILE_PATTERN_NONEXISTENT = 2

    args = parser.parse_args()

    # Set loglevel
    LOG_LEVEL = logging.ERROR
    if args.verbose == 1:
        LOG_LEVEL = logging.INFO
    elif args.verbose > 1:
        LOG_LEVEL = logging.DEBUG

    logging.basicConfig(format="%(levelname)-8s %(message)s")
    logger.setLevel(level=LOG_LEVEL)

    try:
        commands = to_commands(spec=sorted(parse_file(args.CONFIG_SPEC)),
                               relative_root=args.CONFIG_SPEC.parent,
                               ignore_nonexisting=args.ignore_nonexisting)
    except FileNotFoundError as Err:
        if args.CONFIG_SPEC.exists():
            print(Err, file=sys.stderr)
            logger.error(Err)
            logger.debug(traceback.format_exc())
            sys.exit(E_FILE_PATTERN_NONEXISTENT)
        else:
            print(f"Unable to find config spec: {Err}", file=sys.stderr)
            sys.exit(E_NO_CONFIG_SPEC)

    if args.stdout:
        for c in commands:
            print(str(c), file=sys.stdout)
    else:
        try:
            apply(commands,
                not args.apply)
        except subprocess.CalledProcessError as Err:
            print(f"Git command invokation failed: {Err}", file=sys.stderr)
            logger.error(Err)
            logger.debug(traceback.format_exc())
