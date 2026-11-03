# 0010 — Patterns: regular expressions that every engine reads alike

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

- **JSON Schema's patterns are ECMA-262's regular expressions,** built with the `u` flag ([JSON Schema core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core), §6.4). The sides read them with two engines:
  - ai-app with ajv, in JavaScript: ECMA-262, with the `u` flag;
  - ai-cloud and ai-robot with jsonschema, in Python: Python's `re`.
- **The two engines disagree,** as measured on 2026-11-03 over every code point, with Node 24 and Python 3.14:
  - Python's `$` also matches before a last newline, so `"vi\n"` passed every pattern on the Python sides. ai-cloud and ai-robot now read a final `$` as the end ([ai-cloud#20](https://github.com/trungnguyen278/ai-cloud/pull/20), [ai-robot#42](https://github.com/trungnguyen278/ai-robot/pull/42));
  - Python's `\d` and `\w` take in every script's digits and letters. Its `\s` takes U+001C to U+001F and U+0085, where ECMA-262's takes U+FEFF;
  - with the `u` flag, ECMA-262 refuses `\-` outside a class, which Python accepts.
- **Of the protocols' 41 patterns,** one used such a class: the email's `\s`, on which the engines disagreed for six characters.
- **Two standards name what engines read alike:**
  - JSON Schema asks schema authors to keep to single characters, classes, quantifiers, the `^` and `$` anchors, grouping and alternation (core 2020-12, §6.4);
  - [RFC 9485](https://www.rfc-editor.org/rfc/rfc9485), I-Regexp, is the IETF's format for regular expressions that interoperate across engines. It has no multi-character escapes such as `\s` and `\w`.

## Decision

1. **A pattern is `^`, a body, then `$`.** One that checks only a prefix, such as `^https?://`, has no `$`.
2. **The body is an I-Regexp** (RFC 9485, §3) that keeps to what JSON Schema recommends. It has none of:
   - `\p{…}` and `\P{…}`, which Python's `re` cannot read;
   - the dot, which engines read differently: a class names what it allows;
   - `^` and `$`, which both engines read as anchors;
   - `\-` outside a class, which ECMA-262 refuses with the `u` flag;
   - `&&`, `||` or `~~` in a class, which Python warns may become set operations.
3. **A character is written as itself,** through JSON's escapes where it has to be (`\u001f` in the JSON text), never through a regular expression's own `\u`.
4. **ai-platform's CI checks every pattern** against these rules. The sides that read patterns with Python read a final `$` as the very end.

The app API 1.2 rewrites the two patterns outside these rules: the email's and the name's.

## Alternatives considered

| Alternative | Why not |
|---|---|
| An ECMA-262 engine on the Python sides | A compiled dependency on each Python side, the Pi's included. The schemas would still hold what a later side's engine reads otherwise. |
| Each side copes with every difference itself | Every side keeps the same list of differences, and each new side meets them one by one. |
| I-Regexp as it stands | Python's `re` has no `\p{…}`, and ECMA-262 refuses I-Regexp's `\-` outside a class with the `u` flag. |
| Leave the patterns as they are | The sides go on accepting different values, and nothing shows it. |

## Consequences

- Positive:
  - a pattern accepts the same values on every side, and the rule is checked where the schemas are written;
  - the rule rests on two published standards, not on a list of our own.
- Negative / accepted trade-offs:
  - classes are written out: the email's names every character it refuses;
  - a pattern that needs Unicode's categories, such as "any letter", reopens this decision: Python's `regex` module, or an ECMA-262 engine.
- Follow-up:
  - the app API 1.2;
  - ai-cloud moves its pin to it, and its test's list of patterns outside these rules empties.

## References

Retrieved 2026-11-03:

- [JSON Schema core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core), §6.4, Regular Expressions.
- [RFC 9485](https://www.rfc-editor.org/rfc/rfc9485), I-Regexp: an interoperable regular expression format.
- [ECMA-262](https://tc39.es/ecma262/), regular expressions; [Python's `re`](https://docs.python.org/3/library/re.html).
- The measurements: ai-cloud's dev log of 2026-11-03.
