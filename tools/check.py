# SPDX-License-Identifier: MIT
"""Check the protocols: every schema is valid JSON Schema, its patterns keep to ADR-0010,
each keyword of one type has its type declared as Ajv's strictTypes asks, and each
uniqueItems has its bounds beside it; every example follows its schema, whose patterns are
read as ECMA-262 reads them, and holds only JSON that every side can hold (ADR-0014); each
protocol's README names the version of its schema's title, and each message of its tables has
a definition of its own in its sender's; and a new minor version still accepts the examples
of the version before it. Check the test vectors, against the check's own reading of
ADR-0014 and against the schemas; and the catalogs: their schema, their examples, and the
copy of MF2's test suite.

    python tools/check.py

Needs `jsonschema` (pip install jsonschema) and, for the compatibility check, the
repository's tags (in CI: fetch-depth 0).
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import warnings
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NoReturn

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ROOT / "protocols"
CATALOGS = ROOT / "catalogs"
VECTORS = ROOT / "vectors"
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


# What every side can hold (ADR-0014): I-JSON (RFC 7493, §2), without U+0000, at most 64 deep.
MAX_DEPTH = 64
# The integers that a double holds exactly, which are all that an I-JSON receiver must take as
# exact (RFC 7493, §2.2).
EXACT_INTEGERS = 2**53 - 1


def number_problem(token: str, integral: bool) -> str | None:
    """What puts the JSON number `token`, an integer if `integral`, past a double (RFC 7493,
    §2.2), if anything: a magnitude that no double reaches, either way, or an integer that no
    double holds exactly."""
    if integral and len(token) < len(str(EXACT_INTEGERS)):  # fewer digits: exact
        return None
    number = float(token)  # it reads any number of digits, where int() takes at most 4,300
    if not math.isfinite(number):
        return "a number past a double's range"
    if integral and abs(int(token)) > EXACT_INTEGERS:
        return "an integer that no double holds exactly"
    if number == 0 and any(digit in "123456789" for digit in token.lower().partition("e")[0]):
        return "a number nearer zero than any double but zero"
    return None


def survey(text: str) -> tuple[Any, list[str], list[str]]:
    """`text` read as JSON, then what ADR-0014 makes a receiver refuse in it, and what it lets
    a receiver refuse, but for its depth: found in every name, string and number, those of a
    value that a repeated name drops included. ValueError if `text` is not JSON, NaN and
    Infinity included."""
    must: list[str] = []
    may: list[str] = []

    def characters(string: str) -> None:
        for character in set(string):
            code = ord(character)
            if code == 0:
                must.append("U+0000 in a string")
            elif 0xD800 <= code <= 0xDFFF:  # a pair is one character once read: this one is alone
                must.append(f"a lone surrogate, U+{code:04X}")
            elif 0xFDD0 <= code <= 0xFDEF or code & 0xFFFE == 0xFFFE:
                may.append(f"a noncharacter, U+{code:04X}")

    def strings(value: Any) -> None:
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                characters(item)
            elif isinstance(item, dict):
                pending.extend(item)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value = dict(items)
        if len(value) < len(items):
            counts = Counter(name for name, _ in items)
            may.extend(f"`{name}` twice in an object" for name, count in counts.items()
                       if count > 1)
            for name, item in items:
                if value[name] is not item:  # dropped: the kept value is checked with the rest
                    strings(item)
        return value

    def number(token: str, integral: bool) -> Any:
        if problem := number_problem(token, integral):
            may.append(problem)
            return 0
        return int(token) if integral else float(token)

    def constant(name: str) -> NoReturn:
        raise ValueError(f"{name} is not JSON")

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant,
                       parse_float=lambda token: number(token, False),
                       parse_int=lambda token: number(token, True))
    strings(value)
    return value, sorted(set(must)), sorted(set(may))


def deepest(value: Any) -> int:
    """How deep the arrays and objects of `value` nest, the outermost counted."""
    most = 0
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if isinstance(item, (dict, list)):
            most = max(most, depth)
            pending.extend((each, depth + 1)
                           for each in (item.values() if isinstance(item, dict) else item))
    return most


def held(text: str) -> list[str]:
    """Problems with the JSON `text` of a file of the repository, against ADR-0014: anything
    that I-JSON forbids, a U+0000, or a message, in `messages`, that nests deeper than
    MAX_DEPTH."""
    try:
        data, must, may = survey(text)
    except ValueError as error:
        return [f"not JSON: {error}"]
    problems = must + may
    for step in data.get("messages", []) if isinstance(data, dict) else []:
        if isinstance(step, dict) and deepest(step.get("message")) > MAX_DEPTH:
            problems.append(f"a message nests deeper than {MAX_DEPTH}")
    return sorted(set(problems))


# Example files that the check of ADR-0014 must accept (True) and refuse (False). The escapes
# are made by json.dumps, which writes a lone surrogate and a noncharacter as \u escapes too.
PLANTED_TEXTS: tuple[tuple[str, bool], ...] = (
    (json.dumps({"messages": [{"message": {"a": "x"}}]}), True),
    (json.dumps({"messages": [{"message": {"a": chr(0x1F600)}}]}), True),  # a surrogate pair
    (json.dumps({"messages": [{"message": {"a": chr(0)}}]}), False),
    (json.dumps({"messages": [{"message": {chr(0): 1}}]}), False),
    (json.dumps({"messages": [{"message": {"a": chr(0xDEAD)}}]}), False),
    (json.dumps({"messages": [{"message": {"a": chr(0xFDD0)}}]}), False),
    (json.dumps({"messages": [{"message": {"a": chr(0x10FFFF)}}]}), False),
    ('{"messages": [{"message": {"a": 1, "a": 1}}]}', False),
    ('{"messages": [{"message": {"a": [1.7976931348623157e308, 5e-324, 0.0e9]}}]}', True),
    ('{"messages": [{"message": {"a": [9007199254740991, -9007199254740991]}}]}', True),
    ('{"messages": [{"message": {"a": 1e400}}]}', False),
    ('{"messages": [{"message": {"a": -1' + "0" * 400 + "}}]}", False),
    ('{"messages": [{"message": {"a": 9007199254740992}}]}', False),
    ('{"messages": [{"message": {"a": 1e-400}}]}', False),
    ('{"messages": [{"message": {"a": NaN}}]}', False),
    ("[", False),
    # ADR-0014's figure, written out so that a change to MAX_DEPTH alone fails the check.
    ('{"messages": [{"message": ' + "[" * 64 + "]" * 64 + "}]}", True),
    ('{"messages": [{"message": ' + "[" * 65 + "]" * 65 + "}]}", False),
)


def check_holding() -> list[str]:
    """Problems with the check of ADR-0014: it must accept and refuse the planted texts."""
    return [
        f"tools/check.py: {'refuses' if valid else 'accepts'} {text[:80]!r}"
        for text, valid in PLANTED_TEXTS
        if bool(held(text)) == valid
    ]


# The test vectors (vectors/README.md): each file holds the vectors of one definition of
# vectors/schema.json, its name.
VECTOR_FILES = ("reading", "validating")
# The longest vector: the largest message of any protocol, the cloud link's (its README, Sizes).
MAX_VECTOR = 1 << 20
# Strings, and the brackets outside them, as the sides' readers find them. A string that never
# closes runs to the end of the text, so that each character is read once.
NESTING = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"?|[\[\]{}]')
BYTE_ORDER_MARK = chr(0xFEFF)


def nesting(text: str) -> int:
    """How deep the arrays and objects of `text` nest, counted on the text."""
    depth = most = 0
    for token in NESTING.finditer(text):
        if token[0] in ("[", "{"):
            depth += 1
            most = max(most, depth)
        elif token[0] in ("]", "}"):
            depth -= 1
    return most


def reference(data: bytes) -> tuple[str, int, Any]:
    """How a side that reads MAX_DEPTH deep answers the text `data`, as ADR-0014 rules: "read",
    "refused", or "either", where a receiver may refuse it; how deep the text nests; and the
    value read, or None."""
    try:
        text = data.decode()
    except UnicodeDecodeError:
        return "refused", nesting(data.decode(errors="replace")), None
    if text.startswith(BYTE_ORDER_MARK):  # a reader may ignore it (RFC 8259, §8.1)
        result, depth, value = reference(data[3:])
        return "refused" if result == "refused" else "either", depth, value
    depth = nesting(text)
    if depth > MAX_DEPTH:
        return "refused", depth, None
    try:
        value, must, may = survey(text)
    except ValueError:
        return "refused", depth, None
    return "refused" if must else "either" if may else "read", depth, value


def vector_bytes(vector: dict[str, Any]) -> bytes:
    """A vector's text: its `text` or its `parts` in UTF-8, or its `hex`."""
    if "hex" in vector:
        return bytes.fromhex(vector["hex"])
    if "text" in vector:
        return vector["text"].encode()
    return "".join(
        part["text"] * part.get("times", 1) if "text" in part
        else "".join(f"{part['before']}{index}{part['after']}" for index in range(part["times"]))
        for part in vector["parts"]
    ).encode()


def keyword_problem(validator: Draft202012Validator, value: Any, keyword: str) -> str | None:
    """None if `value` breaks `keyword` and nothing else, else what it breaks. A keyword counts
    where it is broken, through `$ref`, `allOf` and `if`; `anyOf`, `oneOf` and `not` count
    themselves, as jsonschema reports them."""
    kinds = sorted({error.validator for error in validator.iter_errors(value)})
    if kinds == [keyword]:
        return None
    return f"breaks {', '.join(kinds) or 'nothing'}, not {keyword} alone"


# Values, each with a schema, a keyword, and whether the value breaks that keyword alone.
PLANTED_KEYWORDS: tuple[tuple[dict[str, Any], Any, str, bool], ...] = (
    ({"maxItems": 2, "uniqueItems": True}, [1, 1], "uniqueItems", True),
    ({"maxItems": 2, "uniqueItems": True}, [1, 1, 1], "uniqueItems", False),
    ({"maxItems": 2, "uniqueItems": True}, [1, 1, 1], "maxItems", False),
    ({"maxItems": 2, "uniqueItems": True}, [1, 2], "uniqueItems", False),
    ({"$ref": "#/$defs/a", "$defs": {"a": {"allOf": [{"if": {"type": "array"},
                                                   "then": {"uniqueItems": True}}]}}},
     [1, 1], "uniqueItems", True),
    ({"anyOf": [{"maxItems": 1}, {"uniqueItems": True}]}, [1, 1], "uniqueItems", False),
)


def check_vectors(schemas: dict[str, Any]) -> list[str]:
    """Problems with the test vectors: their files, against vectors/schema.json and ADR-0014;
    and each vector, which must be unique, at most MAX_VECTOR long, and get its result from
    the check's own reader and from the protocols' schemas, and break its `keyword` alone.
    The check of a keyword must answer the planted values as written."""
    form = json.loads((VECTORS / "schema.json").read_text(encoding="utf-8"))
    problems = [
        f"tools/check.py: {'refuses' if alone else 'accepts'} {value} as breaking {keyword} alone"
        for schema, value, keyword, alone in PLANTED_KEYWORDS
        if (keyword_problem(Draft202012Validator(schema), value, keyword) is None) != alone
    ]
    ids: set[str] = set()
    validating: dict[tuple[str, str], Draft202012Validator] = {}
    for name in VECTOR_FILES:
        where = f"vectors/{name}.json"
        text = (VECTORS / f"{name}.json").read_text(encoding="utf-8")
        found = [f"{where}: {problem} (ADR-0014)" for problem in held(text)]
        if not found:
            validator = Draft202012Validator(with_ecma_ends({**form, "$ref": f"#/$defs/{name}"}))
            found = [f"{where}: {error.message} (at {list(error.absolute_path)})"
                     for error in validator.iter_errors(json.loads(text))]
        problems += found
        for vector in [] if found else json.loads(text)["vectors"]:
            label = f"{where}: {vector['id']}"
            if vector["id"] in ids:
                problems.append(f"{label}: its id is another vector's")
            ids.add(vector["id"])
            data = vector_bytes(vector)
            if len(data) > MAX_VECTOR:
                problems.append(f"{label}: {len(data)} bytes, more than {MAX_VECTOR}")
            result, depth, value = reference(data)
            if name == "reading":
                if vector.get("depth") != (depth if depth > MAX_DEPTH else None):
                    problems.append(f"{label}: nests {depth} deep, which `depth` must say past "
                                    f"{MAX_DEPTH} only")
                if result != vector["result"]:
                    problems.append(f"{label}: {result} as ADR-0014 rules, not {vector['result']}")
                continue
            if result != "read":
                problems.append(f"{label}: {result} as ADR-0014 rules, where a message is read")
                continue
            key = (vector["protocol"], vector["definition"])
            schema = schemas.get(f"protocols/{key[0]}/schema.json", {})
            if key[1] not in schema.get("$defs", {}):
                problems.append(f"{label}: no {key[1]} in protocols/{key[0]}/schema.json")
                continue
            if key not in validating:
                validating[key] = Draft202012Validator(
                    {**with_ecma_ends(schema), "$ref": f"#/$defs/{key[1]}"})
            valid = validating[key].is_valid(value)
            if valid != (vector["result"] == "valid"):
                problems.append(
                    f"{label}: {'valid' if valid else 'invalid'}, not {vector['result']}")
            elif "keyword" in vector:
                problem = keyword_problem(validating[key], value, vector["keyword"])
                if problem:
                    problems.append(f"{label}: {problem}")
    return problems


# The tables of a protocol's README that list its messages: a column of their types, and one
# of who sends them.
TYPE_COLUMNS = ("Type", "Message")
DEFINITION = re.compile(r"\$defs/(from_\w+)")


def dispatches(schema: dict[str, Any], definition: str, kind: str) -> bool:
    """Whether `definition` of `schema` sends a message of type `kind` on to a definition of
    its own: an entry of its `allOf` whose `if` takes the bare `{"type": kind}`, and whose
    `then` is a definition of the schema."""
    definitions = schema.get("$defs", {})
    for entry in definitions.get(definition, {}).get("allOf", []):
        condition, then = entry.get("if"), entry.get("then")
        if (isinstance(condition, dict) and isinstance(then, dict)
                and then.get("$ref", "").removeprefix("#/$defs/") in definitions
                and Draft202012Validator({"$defs": definitions, **condition})
                .is_valid({"type": kind})):
            return True
    return False


def undispatched(readme: str, schema: dict[str, Any]) -> tuple[list[str], int]:
    """Problems with the messages that the tables of a protocol's README list, against its
    schema, and how many it lists. Each sender's definition, which the table's section names as
    `$defs/from_<sender>…`, or else `from_<sender>`, must dispatch each message to one of its
    own. `both` stands for each other sender of its table."""
    problems: list[str] = []
    listed = 0
    lines = readme.splitlines()
    named: set[str] = set()
    for index, line in enumerate(lines):
        if line.startswith("#"):
            named = set()
        named.update(DEFINITION.findall(line))
        header = [cell.strip() for cell in line.strip("| ").split("|")]
        columns = [header.index(column) for column in TYPE_COLUMNS if column in header]
        if not line.startswith("|") or "From" not in header or not columns:
            continue
        rows = []
        for row in lines[index + 2:]:
            if not row.startswith("|"):
                break
            rows.append([cell.strip() for cell in row.strip("| ").split("|")])
        sent = [[sender.strip().lower() for sender in row[header.index("From")].split(",")]
                for row in rows]
        others = sorted({sender for senders in sent for sender in senders} - {"both"})
        for row, senders in zip(rows, sent, strict=True):
            for sender in others if "both" in senders else senders:
                found = sorted(name for name in named
                               if name == f"from_{sender}" or name.startswith(f"from_{sender}_"))
                definition = found[0] if len(found) == 1 else f"from_{sender}"
                for kind in re.findall(r"`([^`]+)`", row[columns[0]]):
                    listed += 1
                    if not dispatches(schema, definition, kind):
                        problems.append(f"`{kind}`, from {sender}, has no definition of its own "
                                        f"in {definition}")
    return problems, listed


# A schema, and READMEs that the check of their tables must accept (True) and refuse (False)
# against it.
PLANTED_SCHEMA: dict[str, Any] = {"$defs": {
    "is_a": {"type": "object", "required": ["type"], "properties": {"type": {"const": "a"}}},
    "is_b": {"type": "object", "required": ["type"], "properties": {"type": {"const": "b"}}},
    "a": {"type": "object"},
    "from_x": {"allOf": [{"if": {"$ref": "#/$defs/is_a"}, "then": {"$ref": "#/$defs/a"}}]},
    "from_y": {"allOf": [{"if": {"$ref": "#/$defs/is_a"}, "then": {"$ref": "#/$defs/a"}},
                         {"if": {"$ref": "#/$defs/is_b"}, "then": {"$ref": "#/$defs/a"}}]},
    "from_w": {"allOf": [{"if": {"$ref": "#/$defs/is_a"}, "then": {"type": "object"}}]},
    "from_y_in_room": {"allOf": [{"if": {"$ref": "#/$defs/is_b"}, "then": {"$ref": "#/$defs/a"}}]},
}}
TABLE = "## Messages\n\n| Type | From | Purpose |\n|---|---|---|\n"
ROOM = "## The room\n\nAgainst `$defs/from_y_in_room`.\n\n" + TABLE.removeprefix("## Messages\n\n")
PLANTED_TABLES: tuple[tuple[str, bool], ...] = (
    (TABLE + "| `a` | x | A |\n| `a` | y | A |\n", True),
    (TABLE + "| `a` | both | A |\n| `a` | x | A |\n| `a` | y | A |\n\nText.\n", True),
    (TABLE + "| `a` | X, Y | A |\n", True),
    ("## Session\n\n| From | Message | Fields |\n|---|---|---|\n| X | `a` | f |\n", True),
    (ROOM + "| `b` | y | B |\n", True),
    (ROOM + "| `b` | y | B |\n\n" + TABLE + "| `a` | y | A |\n", True),
    (TABLE + "| `b` | y | B |\n", True),
    (TABLE + "| `b` | x | B |\n", False),  # from_x has no `b`
    (TABLE + "| `a` | w | A |\n", False),  # its `then` is no definition
    (TABLE + "| `a`, `b` | x | A, B |\n", False),
    (TABLE + "| `b` | both | B |\n| `a` | x | A |\n| `a` | y | A |\n", False),
    (TABLE + "| `a` | z | A |\n", False),  # no from_z
    (ROOM + "| `a` | y | A |\n", False),  # from_y_in_room has no `a`
    ("## Session\n\n| From | Message | Fields |\n|---|---|---|\n| X | `c` | f |\n", False),
)


def check_dispatch() -> list[str]:
    """Problems with the check of a README's tables: it must accept and refuse the planted
    READMEs."""
    return [
        f"tools/check.py: {'refuses' if valid else 'accepts'} the planted README {readme!r}"
        for readme, valid in PLANTED_TABLES
        if bool(undispatched(readme, PLANTED_SCHEMA)[0]) == valid
    ]


# Where a protocol's README names its version, which must be its schema's title's: the line
# "Version **M.m**:", and the first of its version notes, "- **M.m** adds…".
README_VERSIONS = (
    ("its version", re.compile(r"^Version \*\*(\d+)\.(\d+)\*\*:", re.MULTILINE)),
    (
        "its first version note",
        re.compile(r"^\*\*Version notes:\*\*\n- \*\*(\d+)\.(\d+)\*\*", re.MULTILINE),
    ),
)


def named_versions(readme: str, major: int, minor: int) -> list[str]:
    """Problems with the versions that a protocol's README names, against `major.minor`."""
    problems = []
    for what, pattern in README_VERSIONS:
        found = [".".join(pair) for pair in pattern.findall(readme)]
        if found != [f"{major}.{minor}"]:
            named = ", ".join(found) or "no version"
            problems.append(
                f"the README names {named} as {what}, the schema's title {major}.{minor}"
            )
    return problems


# READMEs that the check of their versions must accept, and refuse, against a version.
PLANTED_READMES: tuple[tuple[str, int, int, bool], ...] = (
    ("Version **2.2**:\n\n**Version notes:**\n- **2.2** adds.\n- 2.1 adds.\n", 2, 2, True),
    ("Version **12.10**:\n\n**Version notes:**\n- **12.10** adds.\n", 12, 10, True),
    ("Version **2.2**:\n\n**Version notes:**\n- **2.2** adds.\nVersion **2.1** came first.\n", 2, 2,
     True),
    ("Version **2.1**:\n\n**Version notes:**\n- **2.2** adds.\n", 2, 2, False),
    ("Version **2.2**:\n\n**Version notes:**\n- **2.1** adds.\n", 2, 2, False),
    ("Version **2.2**:\n\n**Version notes:**\n- 2.1 adds.\n- **2.2** adds.\n", 2, 2, False),
    ("Version **2.20**:\n\n**Version notes:**\n- **2.2** adds.\n", 2, 2, False),
    ("Version **12.2**:\n\n**Version notes:**\n- **2.2** adds.\n", 2, 2, False),
    ("Version **2.2**:\nVersion **2.1**:\n\n**Version notes:**\n- **2.2** adds.\n", 2, 2, False),
    ("**Version notes:**\n- **2.2** adds.\n", 2, 2, False),
    ("Version **2.2**:\n", 2, 2, False),
)


def check_naming() -> list[str]:
    """Problems with the check of a README's versions: it must accept and refuse the planted
    READMEs."""
    return [
        f"tools/check.py: {'refuses' if valid else 'accepts'} {readme!r} for {major}.{minor}"
        for readme, major, minor, valid in PLANTED_READMES
        if bool(named_versions(readme, major, minor)) == valid
    ]


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


# The keywords that apply to one type of value only (JSON Schema 2020-12, Validation §6 and
# Core §10). Ajv's strict mode asks that a schema using one declare that type, in itself or
# in a schema for the same value, and never through a $ref ("strictTypes"), so that an app
# compiles every schema here strictly.
TYPED_KEYWORDS: dict[str, frozenset[str]] = {
    "object": frozenset({
        "properties", "patternProperties", "additionalProperties", "propertyNames",
        "unevaluatedProperties", "required", "minProperties", "maxProperties",
        "dependentRequired", "dependentSchemas",
    }),
    "array": frozenset({
        "items", "prefixItems", "contains", "minContains", "maxContains", "unevaluatedItems",
        "minItems", "maxItems", "uniqueItems",
    }),
    "string": frozenset({"minLength", "maxLength", "pattern", "format"}),
    "number": frozenset({
        "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    }),
}
SAME_VALUE = frozenset({"allOf", "anyOf", "oneOf", "if", "then", "else", "not", "dependentSchemas"})
SUBSCHEMA_MAPS = frozenset({"properties", "patternProperties", "dependentSchemas", "$defs"})
SUBSCHEMA_LISTS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
SUBSCHEMAS = frozenset({
    "if", "then", "else", "not", "items", "contains", "additionalProperties",
    "unevaluatedProperties", "unevaluatedItems", "propertyNames",
})


def subschemas(node: dict[str, Any], where: str) -> Iterator[tuple[str, Any, str]]:
    """The keyword, the schema and the place of each schema right inside `node`."""
    for key, value in node.items():
        if key in SUBSCHEMA_MAPS and isinstance(value, dict):
            for name, subschema in value.items():
                yield key, subschema, f"{where}/{key}/{name}"
        elif key in SUBSCHEMA_LISTS and isinstance(value, list):
            for index, subschema in enumerate(value):
                yield key, subschema, f"{where}/{key}/{index}"
        elif key in SUBSCHEMAS:
            yield key, value, f"{where}/{key}"


def untyped(node: Any, declared: frozenset[str] = frozenset(), where: str = "") -> Iterator[str]:
    """The places in a schema that use a keyword of a type which neither they nor a schema for
    the same value above them declare."""
    if not isinstance(node, dict):
        return
    own = node.get("type", ())
    types = declared | frozenset([own] if isinstance(own, str) else own)
    if "integer" in types:
        types |= {"number"}
    for kind, keywords in TYPED_KEYWORDS.items():
        if kind not in types and (used := sorted(keywords & node.keys())):
            yield f"{where or '/'}: {', '.join(used)}, without \"type\": \"{kind}\""
    for key, subschema, place in subschemas(node, where):
        inherited = types if key in SAME_VALUE else frozenset()
        if key == "propertyNames":  # a property's name is a string, as Ajv knows
            inherited = frozenset({"string"})
        yield from untyped(subschema, inherited, place)


# Schemas that the check of declared types must accept (True) and refuse (False).
PLANTED_SCHEMAS: tuple[tuple[dict[str, Any], bool], ...] = (
    ({"type": "object", "properties": {"a": {"type": "string", "pattern": "^a$"}}}, True),
    ({"type": "object", "oneOf": [{"required": ["a"]}, {"not": {"required": ["b"]}}]}, True),
    ({"type": "object", "properties": {"required": {"type": "array"}}}, True),
    ({"type": "integer", "minimum": 1}, True),
    ({"type": ["array", "null"], "items": {"type": "string"}}, True),
    ({"type": "object", "propertyNames": {"pattern": "^a$"}}, True),
    ({"required": ["a"]}, False),
    ({"type": "string", "required": ["a"]}, False),
    ({"type": "object", "properties": {"a": {"pattern": "^a$"}}}, False),
    ({"type": "object", "oneOf": [{"properties": {"a": {"pattern": "^a$"}}}]}, False),
    ({"type": "object", "additionalProperties": {"minimum": 1}}, False),
    ({"type": "object", "properties": {"a": {"required": ["b"]}}}, False),  # not its own type
    ({"type": "array", "items": {"maxLength": 2}}, False),
    ({"$defs": {"a": {"type": "object"}}, "allOf": [{"$ref": "#/$defs/a"}], "required": []}, False),
    ({"type": "object", "then": {"properties": {"a": {"minItems": 1}}}}, False),
)


def check_types(schemas: dict[str, Any]) -> list[str]:
    """Problems with the declared types of `schemas`, by file; and with the check itself, which
    must accept and refuse the planted schemas."""
    problems = [
        f"tools/check.py: {'refuses' if valid else 'accepts'} the planted schema {schema}"
        for schema, valid in PLANTED_SCHEMAS
        if valid != (next(untyped(schema), None) is None)
    ]
    for file, schema in schemas.items():
        problems += [f"{file}#{place} (Ajv's strictTypes)" for place in untyped(schema)]
    return problems


def unbounded(node: Any, where: str = "") -> Iterator[str]:
    """The places in a schema whose uniqueItems has no maxItems or no items beside it.

    Comparing the items is quadratic when they cannot be sorted: jsonschema 4.26.0 compares
    each with every other (`_utils.uniq`), and so does Ajv 8.20.0 unless `items` declares only
    scalar types (`vocabularies/validation/uniqueItems.js`, `loopN2`). Ajv checks maxItems
    first and stops at the first error; ai-cloud and ai-robot compare the items only when the
    array's own maxItems and items allow them. Both count on those two keywords standing beside
    uniqueItems, in the same schema."""
    if not isinstance(node, dict):
        return
    if node.get("uniqueItems") is True and not {"maxItems", "items"} <= node.keys():
        yield f"{where or '/'}: uniqueItems without maxItems and items beside it"
    for _, subschema, place in subschemas(node, where):
        yield from unbounded(subschema, place)


# Schemas that the check of uniqueItems must accept (True) and refuse (False).
PLANTED_BOUNDS: tuple[tuple[dict[str, Any], bool], ...] = (
    ({"type": "array", "items": {"type": "string"}, "maxItems": 2, "uniqueItems": True}, True),
    ({"type": "array", "uniqueItems": False}, True),
    ({"type": "object", "properties": {"uniqueItems": {"type": "boolean"}}}, True),
    ({"type": "array", "items": {"type": "string"}, "uniqueItems": True}, False),
    ({"type": "array", "maxItems": 2, "uniqueItems": True}, False),
    ({"$defs": {"a": {"type": "array", "uniqueItems": True}}}, False),
    ({"type": "object", "properties": {"a": {"type": "array", "uniqueItems": True}}}, False),
    ({"allOf": [{"maxItems": 2, "items": {}}, {"uniqueItems": True}]}, False),
    ({"type": "array", "items": {"type": "array", "uniqueItems": True}}, False),
)


def check_bounds(schemas: dict[str, Any]) -> list[str]:
    """Problems with the arrays of unique items of `schemas`, by file; and with the check
    itself, which must accept and refuse the planted schemas."""
    problems = [
        f"tools/check.py: {'refuses' if valid else 'accepts'} the planted schema {schema}"
        for schema, valid in PLANTED_BOUNDS
        if valid != (next(unbounded(schema), None) is None)
    ]
    for file, schema in schemas.items():
        problems += [f"{file}#{place}" for place in unbounded(schema)]
    return problems


def main() -> int:
    problems: list[str] = check_catalogs()
    problems += check_reading()
    problems += check_holding()
    problems += check_naming()
    problems += check_dispatch()
    schemas = {
        path.relative_to(ROOT).as_posix(): json.loads(path.read_text(encoding="utf-8"))
        for path in [*sorted(PROTOCOLS.glob("*/schema.json")), CATALOGS / "schema.json",
                     VECTORS / "schema.json"]
    }
    Draft202012Validator.check_schema(schemas["vectors/schema.json"])
    problems += check_patterns(schemas)
    problems += check_types(schemas)
    problems += check_bounds(schemas)
    problems += check_vectors(schemas)
    for folder in sorted(path for path in PROTOCOLS.iterdir() if path.is_dir()):
        name = folder.name
        schema = json.loads((folder / "schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        version = VERSION.search(schema.get("title", ""))
        if not version:
            problems.append(f"{name}: the schema's title gives no version")
            continue
        major, minor = int(version[1]), int(version[2])
        readme = (folder / "README.md").read_text(encoding="utf-8")
        problems += [f"{name}/README.md: {problem}" for problem in
                     named_versions(readme, major, minor)]
        missing, listed = undispatched(readme, schema)
        problems += [f"{name}/README.md: {problem}" for problem in missing]
        examples = sorted((folder / "examples").glob("*.json"))
        if not examples:
            problems.append(f"{name}: no examples")
        for path in examples:
            text = path.read_text(encoding="utf-8")
            problems += [
                f"{name}/examples/{path.name}: {problem} (ADR-0014)" for problem in held(text)
            ]
            data = json.loads(text)
            problems += check_examples(f"{name}/examples/{path.name}", data, schema)
        previous = previous_examples(name, major, minor)
        if previous:
            tag, old = previous
            for file, data in old.items():
                problems += check_examples(f"{tag} {file}, against {major}.{minor}", data, schema)
        print(f"{name} {major}.{minor}: {listed} messages in its tables, {len(examples)} examples"
              + (f", and those of {previous[0]}" if previous else ""))
    for problem in problems:
        print("PROBLEM:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
