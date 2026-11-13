---
name: review
description: Review a pull request or the current branch of this repository before handing it over; run it inline, without subagents, to keep the cost low. Use before telling the user a pull request is ready, and when asked to review a PR, a branch or a diff here.
---

# Reviewing a change

Goal: find what would break a side, before a side finds it. Work in the main conversation: no subagents. Read the diff once, run the checks, then walk the list below. Add to it each kind of mistake the project meets, so that it is not met twice.

## 1. Scope it

```sh
git fetch -q origin
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

## 2. Run the checks

What CI runs: every schema is valid JSON Schema, and every example validates against its schema. A failing check is a finding; fix it before reading further.

## 3. Walk the change

### A protocol

- **Together:** the specification, the schema, the examples and the version notes say the same thing.
- **Versions:** the bump matches the change. Could an old side still talk to a new one, as the version promises? A minor version that makes a field required, narrows a range or changes a meaning is a major one.
- **Bounds:** every new string has a length, every number a range, every list a size, so that each side can refuse what is too big (SEC-14, SEC-15). Numbers are finite: JSON has no NaN.
- **Unknowns:** what does each side do with a message, a field or a value it does not know? The specification says.
- **Dispatch:** in `from_app` and `from_cloud`, a new body must not set off another definition's `if`, and the catch-all must leave it out: a device's `kind` would have read it as a member. Two requests whose bodies have one shape, such as a home's and a device's new `name`, cannot be told apart: one definition reads both, and it must agree with each on every field, as `from_app`'s description says. Plant good and broken bodies through the dispatch, and against their own definition, which a side may use alone.
- **Optional for the previous tag:** the check validates the previous minor version's tagged examples against the new schema, so a field that a minor version adds stays optional in the schema. The specification says from which version a side sends it, and what the other does when it is absent.
- **Interruptions:** for a sequence across sides, such as set-up, walk each point where it can stop, and say what starting again finds there, and what the app then does.
- **Limits and retries:** a limit refuses only what a request adds. A retry, or a thing already there, still gets its answer at the limit.
- **Matching:** a thing found by one of its keys must match the others too, such as a device's key and its identifier. Identifiers compare as their type does: a UUID in any case.
- **Errors:** each failure has a code, and the specification says which side sends it and what the other then does.
- **Devices:** nothing assumes one product; what one kind of device needs is a capability it declares.
- **Security:** nothing secret travels in clear or reaches a log; replays have no effect (SEC-12); the requirements in `protocols/cloud/requirements.md` §9 still hold.
- **Examples:** made-up values only; each exchange is whole and in order.
- **Sources:** what the protocol relies on (an RFC, a Bluetooth specification) is cited, with the section.
- **Conventions** ([ADR-0004](../../../docs/decisions/0004-conventions.md)): UUIDs, RFC 3339 instants, durations in seconds, IANA time zones for civil times, snake_case fields, Problem Details for HTTPS errors.
- **Compatibility** ([ADR-0003](../../../docs/decisions/0003-compatibility.md)): a breaking change is a new major, with a plan for both majors to run side by side; the update path does not change.
- **JSON every side can hold** ([ADR-0014](../../../docs/decisions/0014-json-every-side-can-hold.md)): a free value, such as an event's `data`, is still I-JSON, without U+0000, and at most 64 deep. An example never needs more than a dozen levels.
- **A type for every typed keyword:** a schema that uses `properties`, `required`, `items`, `pattern` or another keyword of one type says that type itself, or in a schema for the same value above it (`allOf`, `oneOf`, `if`…), even when it is reached only through a `$ref` to a definition that does. Ajv's strictTypes does not follow `$ref` to find a type, and ai-app compiles the schemas with it; `tools/check.py` asks the same. Adding `"type": "object"` changes no outcome, since every message is an object.
- **A frame that cannot be answered:** an `error` needs a number to answer. For every frame without one (unreadable, unnumbered, held only partly by a parser that gave up), the text says how the session ends, and the rule depends on the frame, never on how far a reader got. A size limit is met by the WebSocket library, which closes with 1009 before the application sees anything.
- **`reply_to` whenever the answered `seq` can be read,** in an exchange or a handshake too: an error that answers a `hello` or a `confirm` carries it. Only a message that could not be read, or held (ADR-0014), goes without.
- **To whom a message goes:** with several peers connected, such as two apps over Bluetooth, an answer reaches the peer it answers only. BlueZ indicates a changed `Value` to every subscribed device; one device's own channel comes from `AcquireNotify` since BlueZ 5.80 (Ubuntu 26.04 has 5.85); before it, 5.69 to 5.79 included, an acquired channel still reached every subscribed device.
- **Every way a framing can fail:** for fragments or frames, the text lists each case that does not fit (flags, a length out of range, too short to hold the length, out of order, too many or too few bytes) and what the receiver holds at most, empty fragments included.
- **A size within every layer's limit:** a fragment fits the ATT MTU minus 3 and an attribute's 512 bytes too, which an MTU of 517, Android 14's, would pass. Look up each layer's limit, in the stack's source too, such as BlueZ's `BT_ATT_MAX_VALUE_LEN`.
- **Bytes that a text cannot hold:** a value that comes as bytes, such as a network's name, can hold a NUL byte, which ADR-0014 keeps out of every text. The protocol gives it another form, such as `ssid_hex`, and says when a side uses it.

### The check

- **Patterns as ECMA-262 reads them:** its `$` is the very end, where Python's also matches before a last newline. `tools/check.py` validates against `with_ecma_ends(schema)`, a copy of the schema that reaches every place jsonschema reads a regular expression, the keys of `patternProperties` included. A new validation in the check goes through it, and plants a value ending in a newline that it must refuse. ai-cloud and ai-robot read only `pattern` so: a protocol that comes to use `patternProperties` needs their reading of its keys too.

### A decision

- Alternatives considered, each with why not; sources, dated; `Proposed` unless explicitly agreed; the index updated.

### Repository rules

- English; `<type>(<scope>): <summary>`; one commit per pull request; the dev log at the end of a session.

## 4. Report

Say in the conversation what the review found and how each item was fixed, and what was not checked (for example, that no side implements a change yet). Keep it out of the commit message and the pull request description.
