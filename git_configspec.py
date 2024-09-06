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
                                (?P<pattern>(?:\".+\"|.+?))\s+
                                (?P<selector>\S+)
                                ([\t ]+(?P<optional>.*))?""",
                            re.X)

@dataclass
class ConfigSpecRule:
    scope: str
    pattern: str
    selector: str

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
                    data.append(
                        ConfigSpecRule(
                            scope=matches.group("scope"),
                            pattern=matches.group("pattern").strip("\""),
                            selector=matches.group("selector")))
                else:
                    logger.debug("No rule match on line %d", line_no)
    return data

if __name__ == "__main__":
    parser = ArgumentParser(description="Git ConfigSpec impersonator. Mimics "
                            "the ClearCase ConfigSpec behaviour for a set of "
                            "repositories.",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("CONFIG_SPEC", type=str, help="The config spec to use.")
    parser.add_argument("--apply", action="store_true",
                        help="Apply the config spec by performing checkout "
                        "based on the rules.")

    logging.basicConfig(level=logging.DEBUG, format="")
    logger.setLevel(level=logging.DEBUG)

    args = parser.parse_args()
    print(parse_file(args.CONFIG_SPEC))
