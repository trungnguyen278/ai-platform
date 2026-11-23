---
name: protocol-change
description: Change a protocol between the project's repositories — add or change a message, a field, an error, a limit or a sequence in the cloud link or set-up, or add a protocol. Use whenever a change touches protocols/, and when a side (a device, the cloud or the app) needs something a protocol does not carry yet.
---

# Changing a protocol

1. **Decide.** If the change decides something new — a new capability, a different flow, a security mechanism — write or update an ADR first (the `adr` checklist), as `Proposed`. A change that only adds detail to a decided design needs no ADR.
2. **Specify** in the protocol's `README.md`: the messages, who sends them and when, the errors, the limits, and what each side does on receipt. Speak of devices, not of one product (CONTRIBUTING.md, rule 5).
3. **Version.** Bump *major.minor* (rule 3) in the README, in the schema's `title` and in the root README's table, and add a line to the version notes at the top of the README: what the version adds or changes. `tools/check.py` checks that the four name the same version.
4. **Schema.** Update `schema.json`: every new field typed and bounded (lengths, ranges, patterns), and `additionalProperties` as the rest of the schema has it. An array of `uniqueItems` has its `maxItems` and `items` beside it, in the same schema: the sides compare the items only when those allow them. A pattern keeps to ADR-0010: `^`, an I-Regexp without the dot or `\p{…}`, then `$`; its characters written as themselves, through JSON's escapes.
5. **Examples.** Update or add a whole exchange in `examples/` that shows the change, with made-up values only.
6. **Check** what CI checks: every schema is valid, every example validates against its schema, and each message that the README's tables list has a definition of its own in its sender's (`python tools/check.py`).
7. **Requirements.** If the change touches identity, keys, tokens or what leaves a device, say in the README how it meets `protocols/cloud/requirements.md` §9.
8. **Pull request**, one commit (`feat(cloud): …`). After the merge, tag the merge commit `<protocol>/v<major>.<minor>`.
9. **The sides.** In ai-robot and ai-cloud (and the app), a pull request moves the pin to the tag, implements the change, and tests against the new examples and the test vectors (`vectors/`).
