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
- **Versions:** the bump matches the change. Could an old side still talk to a new one, as the version promises? A minor version that makes a field required, narrows a range or changes a meaning is a major one, unless no side of the version before can send what it refuses, which its note shows, as the app API 1.2 and 1.8 do. The README's version, its first version note, the schema's title and the root README's table name the same one, which `tools/check.py` checks: the check takes the version from the title alone, to find the tag before it.
- **Bounds:** every new string has a length, every number a range, every list a size, so that each side can refuse what is too big (SEC-14, SEC-15). Numbers are finite: JSON has no NaN. An array of `uniqueItems` has its `maxItems` and `items` beside it, in the same schema: jsonschema and Ajv compare objects each with every other, and the sides compare only an array that those two allow.
- **Unknowns:** what does each side do with a message, a field or a value it does not know? The specification says.
- **Each listed message dispatched:** every type in a README's table of messages has a definition of its own in its sender's `from_*`, which the check finds through an `allOf` entry whose `if` takes `{"type": …}`. A table of messages has a `From` column and a `Type` or `Message` one, one type and its senders to a row, and its section names the `$defs/from_…` that it is validated against when that is not `from_<sender>`.
- **Dispatch:** in `from_app` and `from_cloud`, a new body must not set off another definition's `if`, and the catch-all must leave it out: a device's `kind` would have read it as a member. Two requests whose bodies have one shape, such as a home's and a device's new `name`, cannot be told apart: one definition reads both, and it must agree with each on every field, as `from_app`'s description says. Plant good and broken bodies through the dispatch, and against their own definition, which a side may use alone.
- **Optional for the previous tag:** the check validates the previous minor version's tagged examples against the new schema, so a field that a minor version adds stays optional in the schema. The specification says from which version a side sends it, and what the other does when it is absent.
- **Interruptions:** for a sequence across sides, such as set-up, walk each point where it can stop, and say what starting again finds there, and what the app then does.
- **Limits and retries:** a limit refuses only what a request adds. A retry, or a thing already there, still gets its answer at the limit.
- **An act that ends the session,** such as a device's `leave`: its answer can be lost with the connection, and nothing resumes the session after it. The answer comes only once the act is done, and the text says how the sender learns the outcome afterwards, such as from the refusal it then meets. A restart of the sender between the act and what follows it, such as a device's erase, still leads where the act meant to.
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
- **A bound that libraries count each their own way:** the text says what a receiver accepts, the bound itself included, and the library's comparison is looked up in its source. aiohttp refuses a message of its `max_msg_size` already, where websockets and uvicorn refuse only a larger one. Compression changes the counts: a library may compare the compressed bytes, the decompressed ones, or each in turn.
- **The first message of a handshake:** the text says what a side does when the other's first message is of another type. Nothing has named a version yet, so the rule cannot depend on one.
- **`reply_to` whenever the answered `seq` can be read,** in an exchange or a handshake too: an error that answers a `hello` or a `confirm` carries it. Only a message that could not be read, or held (ADR-0014), goes without.
- **To whom a message goes:** with several peers connected, such as two apps over Bluetooth, an answer reaches the peer it answers only. BlueZ indicates a changed `Value` to every subscribed device; one device's own channel comes from `AcquireNotify` since BlueZ 5.80 (Ubuntu 26.04 has 5.85); before it, 5.69 to 5.79 included, an acquired channel still reached every subscribed device.
- **Every way a framing can fail:** for fragments or frames, the text lists each case that does not fit (flags, a length out of range, too short to hold the length, out of order, too many or too few bytes) and what the receiver holds at most, empty fragments included.
- **A size within every layer's limit:** a fragment fits the ATT MTU minus 3 and an attribute's 512 bytes too, which an MTU of 517, Android 14's, would pass. Look up each layer's limit, in the stack's source too, such as BlueZ's `BT_ATT_MAX_VALUE_LEN`.
- **Bytes that a text cannot hold:** a value that comes as bytes, such as a network's name, can hold a NUL byte, which ADR-0014 keeps out of every text. The protocol gives it another form, such as `ssid_hex`, and says when a side uses it.
- **A condition on a weak tag:** RFC 9110 compares `If-Match` strongly, so that a weak tag never passes it (§13.1.1), and a tag that does not change with every change of what `GET` answers is weak (§8.8.3). A condition on what people change goes in the body, as the app API's `etag` since 1.7, after Google's AIP-154.
- **Every limit that a side refuses past:** the specification names it, with its answer and whether the bound itself passes, such as the app API's 64 KiB body and its `413`. A limit that only a side's configuration holds is one that the other side meets unwarned.
- **A bound in bytes on what the schema counts in characters:** `maxLength` counts code points, which UTF-8 writes in up to 4 bytes, a JSON escape in 6, or 12 for a pair, and a form in up to 12, percent-encoded. A field that a limit in bytes must hold, a body's or a message's, has a pattern for its characters, from its own grammar (RFC 6749's Appendix A, JWS's base64url), and the sum is computed at the maxima, every character at its widest. The app API's tokens had none until 1.8, so a form that `schema.json` allowed could pass the cloud's 64 KiB.
- **Each close code, from both sides:** for every code that ends a connection (1007, 1008, 1009), the specification says what the side that closes does with the session, and what the side that receives the close does. The cloud link named no 1007 until 3.5, and the robot ends its session on its own 1009 but resumes it after the cloud's 1008 (ai-robot 625976a).
- **A limit on what a sender may cut as it likes:** a receiver that counts frames, pings or chunks closes legal senders unless the protocol bounds how finely they come. RFC 6455 lets a message come in fragments of any size, so a frame limit closed 1 MiB messages in 1 KiB fragments, which ESP-IDF's client sends (the cloud link 3.4). The text says what a sender may do, that a receiver lets all of it through at whatever pace it reads, and what comes past it; the library's defaults are looked up in its source.

### The check

- **Patterns as ECMA-262 reads them:** its `$` is the very end, where Python's also matches before a last newline. `tools/check.py` validates against `with_ecma_ends(schema)`, a copy of the schema that reaches every place jsonschema reads a regular expression, the keys of `patternProperties` included. A new validation in the check goes through it, and plants a value ending in a newline that it must refuse. ai-cloud and ai-robot read only `pattern` so: a protocol that comes to use `patternProperties` needs their reading of its keys too.

- **A check that is itself quadratic:** the check reads 1 MiB vectors. `list.count` inside a loop, or a regular expression tried again at each place of a string that never closes, takes hours on them. Count with `Counter`, read each string once, as `NESTING` does, and see that the check still takes seconds.
- **Every error collected before one is chosen:** jsonschema's `best_match(iter_errors(…))` builds an error for each wrong item before it picks one, 3 to 5 s for a 1 MiB array in ai-cloud and ai-robot (2026-11-20), where `is_valid` and Ajv stop at the first. The check validates the vectors with `is_valid`.
- **A vector for each bug class:** a bug that a side meets in reading or validating JSON gets a vector in `vectors/`, in the pull request that finds it, so that every side runs it.
- **A vector that reaches its keyword:** a validator that stops at its first error never reaches a keyword behind one that the message breaks already, such as `uniqueItems` behind `maxItems` or `items`. A vector for a keyword breaks it alone, and says so in `keyword`, which the check holds to.

### A decision

- Alternatives considered, each with why not; sources, dated; `Proposed` unless explicitly agreed; the index updated.

### Repository rules

- English; `<type>(<scope>): <summary>`; one commit per pull request; the dev log at the end of a session.

## 4. Report

Say in the conversation what the review found and how each item was fixed, and what was not checked (for example, that no side implements a change yet). Keep it out of the commit message and the pull request description.
