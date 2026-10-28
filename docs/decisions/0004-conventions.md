# 0004 — Conventions: one way to write identifiers, time, errors and APIs

- **Status:** Proposed
- **Date:** 2026-10-28

## Context

- Every protocol and API between the repositories carries identifiers, times, errors and lists. Written one way in one protocol and another way elsewhere, they cost every side a converter. They also cannot be unified later without a major version.
- The protocols so far already share some habits: snake_case fields, durations in seconds, BCP 47 languages ([ADR-0002](0002-languages.md)). The app's API, the next one, will add resources, pages and errors.
- Google publishes its API Improvement Proposals for the same purpose: one design for thousands of APIs.

## Decision

1. **Identifiers are UUIDs**, in their text form.
   - Those the cloud makes are UUIDv7 ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562)): time-ordered, so they index well, and safe to make in several places at once.
   - A device keeps the identifier it makes for itself (ai-robot ADR-0010).
   - Nothing on the wire is a sequential number.
2. **Time:**
   - an instant is [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339), in UTC with `Z`;
   - a duration is a number of seconds;
   - a civil time, such as a reminder's or an alarm's, is a local date and time with an [IANA time zone](https://www.iana.org/time-zones) name (`Asia/Ho_Chi_Minh`), so that it follows daylight saving where there is any. Every home has a time zone ([ADR-0005](0005-homes.md)).
3. **Names:** fields in snake_case; message types in lower case, with dots (`turn.speech_end`); a number's unit in its name or its schema's description.
4. **Errors:**
   - an HTTPS API answers with Problem Details ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)), each kind of error with its own stable `type`;
   - OAuth endpoints keep OAuth's error format;
   - a message on a link carries a code from its protocol's list.
5. **HTTPS APIs** follow Google's API Improvement Proposals where they apply:
   - resources with stable names, and the major version in the path (`/v1/`);
   - lists in pages, with page tokens;
   - an `Idempotency-Key` header on requests that create something, so that a retry does not create it twice;
   - ETags for updates that may race.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Each protocol its own way | Every side converts between them, and unifying them later takes a major version of each. |
| Sequential integer identifiers | They give away counts, can be guessed, and clash when made in two places (two regions, a device offline). |
| Times as numbers (Unix time) | Ambiguous in milliseconds or seconds, unreadable in logs, and without a zone for civil times. |
| Errors as free text | A side cannot act on them, and translating them needs a code anyway ([ADR-0002](0002-languages.md)). |

## Consequences

- Positive:
  - every protocol and API reads the same, for people and for generated code;
  - the app's API starts with pages, retries and errors settled.
- Negative / accepted trade-offs:
  - a rule to follow in every review; the `review` checklist gains it.
- Follow-up:
  - the app's API, the first to apply all of it;
  - the cloud link's next major version, which aligns what differs.

## References

Retrieved 2026-10-28:

- [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562) (UUIDs, version 7), [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339), [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457), [IANA time zone database](https://www.iana.org/time-zones).
- Google's [API Improvement Proposals](https://google.aip.dev/).
- IETF: [the Idempotency-Key HTTP header field](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) (draft).
