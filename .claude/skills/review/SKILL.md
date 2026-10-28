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
- **Errors:** each failure has a code, and the specification says which side sends it and what the other then does.
- **Devices:** nothing assumes one product; what one kind of device needs is a capability it declares.
- **Security:** nothing secret travels in clear or reaches a log; replays have no effect (SEC-12); the requirements in `protocols/cloud/requirements.md` §9 still hold.
- **Examples:** made-up values only; each exchange is whole and in order.
- **Sources:** what the protocol relies on (an RFC, a Bluetooth specification) is cited, with the section.

### A decision

- Alternatives considered, each with why not; sources, dated; `Proposed` unless explicitly agreed; the index updated.

### Repository rules

- English; `<type>(<scope>): <summary>`; one commit per pull request; the dev log at the end of a session.

## 4. Report

Say in the conversation what the review found and how each item was fixed, and what was not checked (for example, that no side implements a change yet). Keep it out of the commit message and the pull request description.
