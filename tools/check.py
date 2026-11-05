# SPDX-License-Identifier: MIT
"""Check the protocols: every schema is valid JSON Schema, its patterns keep to ADR-0010,
every example follows its schema, whose patterns are read as ECMA-262 reads them, and a new
minor version still accepts the examples of the version before it. Check the catalogs too:
their schema, their examples, and the copy of MF2's test suite.

    python tools/check.py

Needs `jsonschema` (pip install jsonschema) and, for the compatibility check, the
repository's tags (in CI: fetch-depth 0).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import warnings
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NoReturn

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ROOT / "protocols"
CATALOGS = ROOT / "catalogs"
VERSION = re.compile(r"version (\d+)\.(\d+)")  # in each schema's title (CONTRIBUTING.md, rule 3)
TAG = re.compile(r"^(?P<name>[a-z]+)/v(?P<major>\d+)\.(?P<minor>\d+)$")


def ecma_end(pattern: str) -> str:
    r"""`pattern` for Python's `re`, whose `$` also matches before a last newline: JSON
    Schema's patterns are ECMA-262's, whose `$` matches at the very end only, as Python's `\Z`
    does. Only a final `$`, unescaped, is an anchor here: ADR-0010 allows no other. ai-cloud
    and ai-robot read patterns with the same function."""
    body = pattern.removesuffix("$")
    if body == pattern:
        return pattern
    backslashes = len(body) - len(body.rstrip("\\"))
    return pattern if backslashes % 2 else body + r"\Z"


def with_ecma_ends(node: Any) -> Any:
    """A copy of `node`, a schema, whose regular expressions end where ECMA-262 ends them:
    its patterns, and the keys of its patternProperties, found as `schema_patterns` finds
    them. jsonschema reads them with Python's `re`, in `pattern` and `patternProperties` and
    in the lookups of `additionalProperties` and `unevaluatedProperties`, and takes no other
    engine (python-jsonschema#1142): only a copy of the schema reaches all four."""
    if isinstance(node, list):
        return [with_ecma_ends(value) for value in node]
    if not isinstance(node, dict):
        return node
    copy: dict[str, Any] = {}
    for key, value in node.items():
        if key == "pattern" and isinstance(value, str):
            copy[key] = ecma_end(value)
        elif key == "patternProperties" and isinstance(value, dict):
            copy[key] = {
                ecma_end(expression): with_ecma_ends(subschema)
                for expression, subschema in value.items()
            }
        else:
            copy[key] = with_ecma_ends(value)
    return copy


def validators(schema: dict[str, Any]) -> dict[str, Draft202012Validator]:
    """One validator per sender, for the `from_<sender>` definitions of the schema, each
    reading its patterns as ECMA-262 does."""
    ecma = with_ecma_ends(schema)
    return {
        name.removeprefix("from_"): Draft202012Validator({**ecma, "$ref": f"#/$defs/{name}"})
        for name in schema.get("$defs", {})
        if name.startswith("from_")
    }


def check_examples(where: str, examples: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Problems with the messages of `examples`, against `schema`."""
    by_sender = validators(schema)
    problems = []
    for step in examples.get("messages", []):
        if "message" not in step:
            continue  # an audio step: what plays on a track, not a message
        sender = step.get("from")
        if sender not in by_sender:
            problems.append(f"{where}: no `from_{sender}` in the schema")
            continue
        for error in by_sender[sender].iter_errors(step["message"]):
            problems.append(f"{where}: {error.message} (at {list(error.absolute_path)})")
    return problems


# Values that the examples' check must accept, and must refuse, against the schema beside
# each: ECMA-262's `$` matches at the very end only (ECMA-262, §22.2.2.4), where Python's also
# matches before a last newline. The JSON Schema Test Suite has the second case, in
# optional/ecmascript-regex.json.
PLANTED_VALUES: tuple[tuple[dict[str, Any], Any, bool], ...] = (
    ({"pattern": "^[a-z]+$"}, "vi", True),
    ({"pattern": "^[a-z]+$"}, "vi\n", False),
    ({"pattern": "^cost\\$"}, "cost$", True),  # an escaped dollar is a dollar
    ({"pattern": "^a\\\\$"}, "a\\\n", False),  # an escaped backslash, then the end
    ({"anyOf": [{"pattern": "^[a-z]+$"}]}, "vi\n", False),
    # Properties named `pattern` and `patternProperties`, whose values are subschemas.
    (
        {"properties": {"pattern": {"pattern": "^[a-z]+$"}, "patternProperties": True}},
        {"pattern": "vi\n"},
        False,
    ),
    ({"patternProperties": {"^[a-z]+$": {}}, "additionalProperties": False}, {"vi\n": 1}, False),
    ({"patternProperties": {"^x": {"pattern": "^[a-z]+$"}}}, {"x": "vi\n"}, False),
)


def check_reading() -> list[str]:
    """Problems with how the examples' check reads a schema's patterns: it must accept and
    refuse the planted values."""
    problems = []
    for schema, value, valid in PLANTED_VALUES:
        exchange = {"messages": [{"from": "planted", "message": value}]}
        refused = check_examples("planted", exchange, {"$defs": {"from_planted": schema}})
        if bool(refused) == valid:
            verb = "refuses" if valid else "accepts"
            problems.append(f"tools/check.py: {verb} {value!r} against {schema}")
    return problems


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def previous_examples(name: str, major: int, minor: int) -> tuple[str, dict[str, Any]] | None:
    """The examples of the newest tagged version of `name` with the same major and a lower
    minor, by file name; None if there is none."""
    older = []
    for tag in git("tag", "--list", f"{name}/v*").split():
        match = TAG.match(tag)
        if match and int(match["major"]) == major and int(match["minor"]) < minor:
            older.append((int(match["minor"]), tag))
    if not older:
        return None
    tag = max(older)[1]
    files = git("ls-tree", "--name-only", f"{tag}:protocols/{name}/examples").split()
    return tag, {
        file: json.loads(git("show", f"{tag}:protocols/{name}/examples/{file}"))
        for file in files
        if file.endswith(".json")
    }


def check_catalogs() -> list[str]:
    """Problems with the catalogs: the example catalogs follow their schema and name only
    IDs that the English source has, and every file of MF2's test suite is JSON."""
    schema = json.loads((CATALOGS / "schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(with_ecma_ends(schema))
    examples = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((CATALOGS / "examples").glob("*.json"))
    }
    problems = []
    for tag, catalog in examples.items():
        for error in validator.iter_errors(catalog):
            problems.append(f"catalogs/examples/{tag}.json: {error.message}")
    if validator.is_valid({"setup.code.title\n": "Set-up"}):
        problems.append("tools/check.py: accepts a message ID that ends in a newline")
    source = examples.get("en")
    if source is None:
        problems.append("catalogs/examples: no en.json, the source")
    else:
        for tag, catalog in examples.items():
            for key in sorted(set(catalog) - set(source)):
                problems.append(f"catalogs/examples/{tag}.json: {key} is not in en.json")
    tests = sorted((CATALOGS / "mf2-tests" / "tests").rglob("*.json"))
    for path in tests:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            problems.append(f"{path.relative_to(ROOT).as_posix()}: {error}")
    if not tests:
        problems.append("catalogs/mf2-tests: no tests")
    print(f"catalogs: {len(examples)} examples, {len(tests)} files of MF2's tests")
    return problems


# ADR-0010: what every engine reads alike in a pattern, by RFC 9485's grammar (section 3).
# Outside a class, the characters to which I-Regexp gives a meaning: any other is itself.
SPECIAL = frozenset("()*+.?[\\]{|}")
# What a backslash may escape: I-Regexp's SingleCharEsc, but for "-" outside a class, which
# ECMA-262 refuses with the u flag.
ESCAPES = frozenset("()*+.?[\\]^{|}nrt")
CLASS_ESCAPES = ESCAPES | {"-"}
# Pairs in a class that Python warns may become set operations.
SET_OPERATIONS = ("&&", "||", "~~")
# Patterns that the reader must accept, and must refuse: it proves nothing until it has
# refused one.
PLANTED_GOOD = (
    "^[a-z]+$",
    "^https?://",
    "^(about:blank|/app/v[0-9]+/problems/[a-z][a-z0-9_]{0,63})$",
    "^\\.[a-z]{2,}$",
    "^[A-Za-z0-9_-]{43}$",
    "^[-a]$",
    "^[^\u0000-\u001f\u007f-\u009f]+$",
    "^([0-9a-f]{2}){1,32}$",
)
PLANTED_BAD = (
    "^\\d+$",
    "^[^@\\s]+@[^@\\s]+$",
    "^a.b$",
    "^\\p{L}+$",
    "^a\\-b$",
    "^a^b$",
    "^a$b$",
    "a$",
    "^[a&&b]$",
    "^[^]$",
    "^a**$",
    "^(a$",
    "^a)$",
    "^a{3,1}$",
    "^[z-a]$",
    "^(?:a)$",
    "^a*?$",
    "^a\\$",
    "^[a-z-0]$",
    "^{2}$",
    "^\\u00e9$",
)


class PatternError(ValueError):
    """Where a pattern leaves ADR-0010's rules."""


class PatternReader:
    """Reads the body of a pattern, between its anchors, by RFC 9485's grammar and within
    ADR-0010: no dot, no Unicode property, no anchor inside, no escaped "-" outside a class."""

    def __init__(self, body: str) -> None:
        self.body = body
        self.at = 0

    def fail(self, why: str) -> NoReturn:
        raise PatternError(f"{why}, at {self.at} of its body")

    def peek(self) -> str | None:
        return self.body[self.at] if self.at < len(self.body) else None

    def take(self) -> str:
        char = self.body[self.at]
        if 0xD800 <= ord(char) <= 0xDFFF:
            self.fail("a lone surrogate")
        self.at += 1
        return char

    def read(self) -> None:
        self.regexp()
        if self.at != len(self.body):
            self.fail("a ')' that closes no group")

    def regexp(self) -> None:
        # i-regexp = branch *( "|" branch )
        self.branch()
        while self.peek() == "|":
            self.take()
            self.branch()

    def branch(self) -> None:
        # branch = *piece, and piece = atom [ quantifier ]
        while self.peek() not in (None, "|", ")"):
            self.atom()
            self.quantifier()

    def atom(self) -> None:
        char = self.take()
        if char == "(":
            self.regexp()
            if self.peek() != ")":
                self.fail("a group that is not closed")
            self.take()
        elif char == "[":
            self.char_class()
        elif char == "\\":
            self.escape(ESCAPES)
        elif char == ".":
            self.fail("a dot, which engines read differently")
        elif char in "^$":
            self.fail(f"{char!r}, an anchor, inside the body")
        elif char in SPECIAL:
            self.fail(f"{char!r} where a character belongs")

    def escape(self, allowed: frozenset[str]) -> None:
        if self.peek() is None:
            self.fail("a backslash that escapes nothing")
        char = self.take()
        if char not in allowed:
            self.fail(f"the escape \\{char}")

    def quantifier(self) -> None:
        # quantifier = ( "*" / "+" / "?" ) / "{" QuantExact [ "," [ QuantExact ] ] "}"
        if self.peek() in ("*", "+", "?"):
            self.take()
        elif self.peek() == "{":
            self.take()
            low = high = self.number()
            if self.peek() == ",":
                self.take()
                high = None if self.peek() == "}" else self.number()
            if self.peek() != "}":
                self.fail("a range quantifier that is not closed")
            self.take()
            if high is not None and high < low:
                self.fail("a range quantifier whose bounds are reversed")
        else:
            return
        if self.peek() in ("*", "+", "?", "{"):
            self.fail("a second quantifier")

    def number(self) -> int:
        start = self.at
        while (char := self.peek()) is not None and "0" <= char <= "9":
            self.take()
        if self.at == start:
            self.fail("a range quantifier without its number")
        return int(self.body[start : self.at])

    def char_class(self) -> None:
        # charClassExpr = "[" [ "^" ] ( "-" / CCE1 ) *CCE1 [ "-" ] "]"
        start = self.at
        if self.peek() == "^":
            self.take()
        items = 0
        while True:
            char = self.peek()
            if char is None:
                self.fail("a class that is not closed")
            if char == "]" and items:
                self.take()
                break
            if char == "-":
                self.take()
                if items and self.peek() != "]":
                    self.fail("a '-' in a class that makes no range")
            else:
                self.class_char()
                if self.peek() == "-" and self.body[self.at + 1 : self.at + 2] not in ("]", ""):
                    self.take()
                    self.class_char()
            items += 1
        if any(pair in self.body[start : self.at] for pair in SET_OPERATIONS):
            self.fail("a pair in a class that Python reads as a set operation to come")

    def class_char(self) -> None:
        char = self.take()
        if char == "\\":
            self.escape(CLASS_ESCAPES)
        elif char in "[]":
            self.fail(f"{char!r} in a class, unescaped")


def pattern_problem(pattern: str) -> str | None:
    """Why `pattern` leaves ADR-0010's rules, or None if it keeps to them."""
    if not pattern.startswith("^"):
        return "it does not start with ^"
    body = pattern[1:-1] if pattern.endswith("$") else pattern[1:]
    try:
        PatternReader(body).read()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            re.compile(pattern)
    except (PatternError, re.error, FutureWarning) as error:
        return str(error)
    return None


def schema_patterns(node: Any, where: str = "") -> Iterator[tuple[str, str]]:
    """The regular expressions of a schema, with where they are: its patterns, and the keys
    of its patternProperties."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "pattern" and isinstance(value, str):
                yield f"{where}/pattern", value
            elif key == "patternProperties" and isinstance(value, dict):
                for expression, subschema in value.items():
                    yield f"{where}/patternProperties", expression
                    yield from schema_patterns(subschema, f"{where}/patternProperties")
            else:
                yield from schema_patterns(value, f"{where}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from schema_patterns(value, f"{where}/{index}")


def check_patterns(schemas: dict[str, Any]) -> list[str]:
    """Problems with the patterns of `schemas`, by file, against ADR-0010; and with the
    reader itself, which must accept and refuse the planted ones."""
    problems = [f"tools/check.py: refuses {p!r}" for p in PLANTED_GOOD if pattern_problem(p)]
    problems += [
        f"tools/check.py: accepts {p!r}" for p in PLANTED_BAD if pattern_problem(p) is None
    ]
    count = 0
    for file, schema in schemas.items():
        for where, pattern in schema_patterns(schema):
            count += 1
            if (problem := pattern_problem(pattern)) is not None:
                problems.append(f"{file}#{where}: {problem} (ADR-0010)")
    print(f"patterns: {count}, against ADR-0010")
    return problems


def main() -> int:
    problems: list[str] = check_catalogs()
    problems += check_reading()
    schemas = [*sorted(PROTOCOLS.glob("*/schema.json")), CATALOGS / "schema.json"]
    problems += check_patterns(
        {
            path.relative_to(ROOT).as_posix(): json.loads(path.read_text(encoding="utf-8"))
            for path in schemas
        }
    )
    for folder in sorted(path for path in PROTOCOLS.iterdir() if path.is_dir()):
        name = folder.name
        schema = json.loads((folder / "schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        version = VERSION.search(schema.get("title", ""))
        if not version:
            problems.append(f"{name}: the schema's title gives no version")
            continue
        major, minor = int(version[1]), int(version[2])
        examples = sorted((folder / "examples").glob("*.json"))
        if not examples:
            problems.append(f"{name}: no examples")
        for path in examples:
            data = json.loads(path.read_text(encoding="utf-8"))
            problems += check_examples(f"{name}/examples/{path.name}", data, schema)
        previous = previous_examples(name, major, minor)
        if previous:
            tag, old = previous
            for file, data in old.items():
                problems += check_examples(f"{tag} {file}, against {major}.{minor}", data, schema)
        print(f"{name} {major}.{minor}: {len(examples)} examples"
              + (f", and those of {previous[0]}" if previous else ""))
    for problem in problems:
        print("PROBLEM:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
