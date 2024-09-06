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
_COMMENT = re.compile(r"\s*#")
_CS_SCOPE_RULE = re.compile(r"""(?P<scope>element)\s+
                           (?P<pattern>(?:[^\"].+?|\".+\"))\s+
                           (?P<versionSelector>\S+)
                           (?:\s+(?P<optionalClause>.*))?""",
                       re.X)

@dataclass
class ConfigSpecRule:
    scope: str
    pattern: str
    version_selector: str

def parse_file(path: Path) -> list:
    with open(path, 'r', encoding="utf8") as config_spec:
        return parse_iterable(config_spec)

def parse_iterable(config_spec: Iterable[str]) -> Iterable[ConfigSpecRule]:
    data = []
    for line_no, line in enumerate(config_spec, start=1):
        if line:
            if _COMMENT.match(line):
                logger.debug("Line %d is a comment", line_no)
            else:
                matches = _CS_SCOPE_RULE.match(line)

                if matches:
                    data.append(ConfigSpecRule(
                                    scope=matches.group("scope"),
                                    pattern=matches.group("pattern"),
                                    version_selector=
                                    matches.group("versionSelector"))
                    )
                else:
                    logger.debug("No rule match on line %d", line_no)
    return data

if __name__ == "__main__":
    parser = ArgumentParser(description="Git ConfigSpec impersonator. Mimics "
                            "the ClearCase ConfigSpec behaviour for a set of "
                            "repositories.")
    parser.add_argument("CONFIG_SPEC", type=str, help="The config spec to use.")
    parser.add_argument("--verify-paths", action="store_true",
                        help="Verify the the config spec paths.")
    parser.add_argument("--verify", action="store_true",
                        help="Verify the consistency of the config spec paths.")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Dont do anything")

    logging.basicConfig(level=logging.DEBUG, format="")
    
    logger.setLevel(level=logging.DEBUG)

    args = parser.parse_args()
    print(parse_file(args.CONFIG_SPEC))
