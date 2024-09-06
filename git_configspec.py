#!/usr/bin/env python3

import re
import sys

import logging

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
    scope: str
    pattern: str
    selector: str

    def __lt__(self, other) -> bool:
        # If the pattern is shorter OR is the asterisk (*), then this rule
        # shall be sorted first
        return len(self.pattern) < len(other.pattern) or self.pattern == "*"

@dataclass
class PreparedCommand:
    gitroot: Path
    rule: ConfigSpecRule

def parse_file(path: Path) -> list:
    with open(path, 'r', encoding="utf8") as config_spec:
        return parse_iterable(config_spec)

def parse_iterable(config_spec: Iterable[str]) -> Iterable[ConfigSpecRule]:
    data = []
    for line_no, line in enumerate(config_spec, start=1):
        if line:
            if not _COMMENT.match(line):
                matches = _CS_SCOPE_RULE.match(line)

                if matches:
                    data.append(
                        ConfigSpecRule(
                            scope=matches.group("scope"),
                            pattern=matches.group("pattern").strip("\""),
                            selector=matches.group("selector")))
                else:
                    # Its not a comment nor a blank line.
                    logger.warning("Expected rule on line %d: %s",
                                   line_no, line)
    return data

def prepare_cmd(spec: Iterable[ConfigSpecRule]) -> Iterable[tuple[str]]:
    """ Generates the equivalent git commands from the config spec rules. """
    commands = []
    for r in spec:
        path = Path(r.pattern)

        if path.is_file() or path.name == "*":
            logger.debug("Pattern targets a file: %s", path)
            gitroot = path.parent
        else:
            logger.debug("Pattern targets a directory: %s", path)
            gitroot = path

        commands.append(PreparedCommand(gitroot, r))

    return commands

def to_git_command(prepared_cmd: PreparedCommand) -> tuple[str]:
    return ('git', '-C', str(prepared_cmd.gitroot),
            'checkout', prepared_cmd.rule.selector, '--',
            prepared_cmd.rule.pattern)

def apply(spec: Iterable[ConfigSpecRule], dry_run: bool,
          ignore_nonexisting: bool = False):
    for cmd in prepare_cmd(spec):
        if cmd.gitroot.exists() or ignore_nonexisting:
            gitcmd = to_git_command(cmd)
            if dry_run:
                print(f"Would run: {' '.join(gitcmd)}", file=sys.stderr)
            else:
                print("SHARP.")
                #sp.run(*gitcmd)
        else:
            raise FileNotFoundError(f"Non-existing directory: {cmd.gitroot}")

if __name__ == "__main__":
    parser = ArgumentParser(description="Git ConfigSpec impersonator. Mimics "
                            "the ClearCase ConfigSpec behaviour for a set of "
                            "repositories.",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("CONFIG_SPEC", default="CONFIG_SPEC", nargs="?",
                        type=str, help="The config spec to use.")
    parser.add_argument("--apply", action="store_true",
                        help="Apply the config spec by performing checkout "
                        "based on the rules.")
    parser.add_argument("--ignore-nonexisting", action="store_true",
                        help="Do not check whether target patterns exist (i.e. "
                        "files and folders).")

    logging.basicConfig(level=logging.DEBUG, format="")
    logger.setLevel(level=logging.DEBUG)

    args = parser.parse_args()
    parsed = sorted(parse_file(args.CONFIG_SPEC))

    # By default, do a dry-run.
    try:
        apply(parsed, not args.apply, args.ignore_nonexisting)
    except FileNotFoundError as Err:
        print(Err, file=sys.stderr)
        sys.exit(1)
