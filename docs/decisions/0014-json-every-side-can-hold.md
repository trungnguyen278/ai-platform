# 0014 — JSON that every side can hold: I-JSON, no NUL, at most 64 deep

- **Status:** Accepted. A technical decision, delegated to the assistant (2026-11-12).
- **Date:** 2026-11-12

## Context

- **JSON allows more than every side can hold** ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)). Its escapes spell a lone surrogate, `"\uDEAD"`, which UTF-8 cannot encode. They also spell U+0000, which PostgreSQL stores in neither `text` nor `jsonb`. And JSON sets no limit on how deep arrays and objects nest.
- **The schemas cannot say it.** A pattern on every string would be one more rule to forget, and the schemas leave some values free: an event's `data`, an MCP payload.
- **The implementations met it** (ai-cloud#26, ai-cloud#27, 2026-11-11):
  - the cloud refuses lone surrogates, and JSON nested more than 64 deep, which RFC 8259 lets a reader limit (§9);
  - before that limit, Python's `json` stopped where the C stack did: 11,331 deep on Windows, past 20,000 on Linux (Python 3.14.5, measured by ai-cloud on 2026-11-12);
  - the cloud link named neither rule, so a device could not know what the cloud reads.
- **Prior art:**
  - [I-JSON](https://www.rfc-editor.org/rfc/rfc7493) is the IETF's profile of JSON for protocols. It allows no surrogate or noncharacter code point, escaped or not (§2.1), no number past a double (§2.2), and no repeated names in an object (§2.3). It lets a protocol require receivers to reject what breaks it, and asks the protocol to give the receiver a way to say so (§3).
  - [JMAP](https://www.rfc-editor.org/rfc/rfc8620) requires valid I-JSON in both directions (§1.5). It answers a request that is not I-JSON with an error of its own, `notJSON` (§3.6.1).
  - .NET's System.Text.Json reads 64 levels deep unless told otherwise ([`JsonReaderOptions.MaxDepth`](https://learn.microsoft.com/en-us/dotnet/api/system.text.json.jsonreaderoptions.maxdepth)).

## Decision

1. **I-JSON.** Every JSON text that a protocol carries is I-JSON ([RFC 7493](https://www.rfc-editor.org/rfc/rfc7493)): messages, request bodies and answers. This means UTF-8, with no surrogate or noncharacter code point, no number past a double, and no repeated name in an object.
2. **No U+0000** in any name or string, escaped or not. No value of the protocols needs it, and PostgreSQL cannot store it.
3. **At most 64 levels deep.** Arrays and objects nest at most 64 deep, counting the outermost.
   - A side never sends deeper.
   - Every side reads at least that deep.
   - The examples nest at most 9 deep: a capability's input schema, in an MCP payload, is the deepest.
4. **What a receiver refuses:**
   - **Must refuse:** a lone surrogate or a U+0000, which it cannot hold faithfully, and nesting deeper than it reads.
   - **May refuse:** the rest of what I-JSON forbids, namely noncharacters, numbers past a double and repeated names.
   - **How it refuses:** as a text that it cannot read, however far its reader got, so that the answer depends on the text and not on where a parser gives up:
     - the cloud link: `bye` `invalid_message`, which ends the session;
     - set-up: the error `protocol`, without `reply_to`, which ends the session;
     - the app API: `400`.
5. **Each protocol takes this rule in its next minor version:** the cloud link 3.1, set-up 2.1 and the app API 1.6.
   - Narrowing what a receiver takes would otherwise call for a new major version.
   - Here no side ever sent such JSON, and none could have stored it.

## Alternatives considered

| Alternative | Why not |
|---|---|
| JSON as RFC 8259 allows it | Each side then fails in its own way on what it cannot hold: PostgreSQL's error is a `500`, and Python's depth depends on the machine. |
| A pattern against U+0000 on every string of every schema | Values that the schemas leave free, such as an event's `data`, would escape it. It would also be one more rule for every review to check, where the reader's single check covers everything. |
| No control characters at all, as PRECIS's classes do ([RFC 8264](https://www.rfc-editor.org/rfc/rfc8264), §9.12) | Text that people read, such as an answer's, may hold line breaks. Names are already stricter, in their own patterns: the app API refuses control characters in a name. |
| A deeper limit, such as 1,000 | No message comes near 64. A bound that .NET reads by default, and that Python reads on any machine, is safer than one that some sides must raise. |
| Requiring receivers to refuse repeated names | JavaScript's `JSON.parse` keeps the last one silently: the app would need a parser of its own. Senders never repeat a name (decision 1). Each side reads a message once, with one parser, so it validates the very value that it then uses. |

## Consequences

- Positive:
  - every side holds what it accepts, and refuses the rest the same way;
  - a device knows how deep the cloud reads.
- Negative / accepted trade-offs:
  - each receiver checks strings and depth, beyond its schema;
  - repeated names may pass a receiver.
- Follow-up:
  - ai-cloud refuses U+0000 as it refuses lone surrogates;
  - ai-robot and ai-app check what they read the same way.

## References

Retrieved 2026-11-12:

- [RFC 7493](https://www.rfc-editor.org/rfc/rfc7493) (I-JSON), §2 and §3.
- [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), §9.
- [RFC 8620](https://www.rfc-editor.org/rfc/rfc8620) (JMAP), §1.5 and §3.6.1.
- PostgreSQL 18: [character types](https://www.postgresql.org/docs/current/datatype-character.html) ("the character with code zero (sometimes called NUL) cannot be stored") and [JSON types](https://www.postgresql.org/docs/current/datatype-json.html) ("The jsonb type also rejects \u0000").
- .NET: [`JsonReaderOptions.MaxDepth`](https://learn.microsoft.com/en-us/dotnet/api/system.text.json.jsonreaderoptions.maxdepth) ("the default (that is, 0) indicating a maximum depth of 64").
- [RFC 8264](https://www.rfc-editor.org/rfc/rfc8264) (PRECIS), §9.12.
