# SPDX-License-Identifier: MIT
"""Check the protocols: every schema is valid JSON Schema, every example follows its
schema, and a new minor version still accepts the examples of the version before it.
Check the catalogs too: their schema, their examples, and the copy of MF2's test suite.

    python tools/check.py

Needs `jsonschema` (pip install jsonschema) and, for the compatibility check, the
repository's tags (in CI: fetch-depth 0).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ROOT / "protocols"
CATALOGS = ROOT / "catalogs"
VERSION = re.compile(r"version (\d+)\.(\d+)")  # in each schema's title (CONTRIBUTING.md, rule 3)
TAG = re.compile(r"^(?P<name>[a-z]+)/v(?P<major>\d+)\.(?P<minor>\d+)$")


def validators(schema: dict[str, Any]) -> dict[str, Draft202012Validator]:
    """One validator per sender, for the `from_<sender>` definitions of the schema."""
    return {
        name.removeprefix("from_"): Draft202012Validator({**schema, "$ref": f"#/$defs/{name}"})
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
    validator = Draft202012Validator(schema)
    examples = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((CATALOGS / "examples").glob("*.json"))
    }
    problems = []
    for tag, catalog in examples.items():
        for error in validator.iter_errors(catalog):
            problems.append(f"catalogs/examples/{tag}.json: {error.message}")
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


def main() -> int:
    problems: list[str] = check_catalogs()
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
