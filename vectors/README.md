# Test vectors

Texts and messages, each with the answer that every side must give: what [ADR-0014](../docs/decisions/0014-json-every-side-can-hold.md) rules on JSON, and what the protocols' schemas accept. Each side's tests run all of them, so that the cloud, a device and the app take and refuse the same texts, each in a bounded time.

They follow prior art: [JSONTestSuite](https://github.com/nst/JSONTestSuite)'s parsing tests, which a parser must accept, must refuse, or may do either, and [Wycheproof](https://github.com/C2SP/wycheproof)'s test vectors, which are valid, invalid or acceptable, each with an identifier and a comment. Like [MF2's test suite](../catalogs/README.md) here, they are data that every side runs with its own library.

## Files

- [`reading.json`](reading.json): texts for a side's JSON reader. It covers what every side once got wrong:
  - a repeated name whose dropped value hides a U+0000, a lone surrogate or a deeper nesting;
  - strings of escaped quotes, which made a depth count quadratic;
  - numbers past a double, taken in one spelling and refused in another;
  - nesting just past 64, and far past it, which a recursive reader cannot reach;
  - 1 MiB texts, which a reader that takes quadratic time cannot finish.
- [`validating.json`](validating.json): messages for a side's schema validation, with 1 MiB arrays of objects that a quadratic `uniqueItems` cannot finish.
- [`schema.json`](schema.json): the format of both files, in JSON Schema (draft 2020-12).

`tools/check.py` checks them:
- each file against `schema.json`, and against ADR-0014 itself;
- each `id`, unique among both files' vectors;
- each text, at most 1 MiB, the largest message of any protocol (the cloud link's);
- each reading vector's `result` and `depth`, against the check's own reading of ADR-0014;
- each validating vector's `result`, against its protocol's schema, read as ECMA-262 reads patterns.

## A vector

| Field | In | What it is |
|---|---|---|
| `id` | both | Unique among both files' vectors |
| `comment` | both | What the vector tries |
| `text` | both | The text |
| `hex` | reading | The bytes, in hexadecimal: for bytes that are not UTF-8, or a raw U+0000, which no file of this repository holds |
| `parts` | both | The text, made of parts in order, for a text too long to write out. `{"text", "times"}` is `text`, `times` times over (once without `times`); `{"before", "after", "times"}` is `before`, then n in decimal digits, then `after`, for each n from 0 to `times` − 1 |
| `result` | reading | `read`, `refused`, or `either`, where ADR-0014 lets a receiver refuse the text |
| `group` | reading | Vectors that a side answers alike, whichever answer it gives: a number past a double, for one, is refused in every spelling or in none |
| `depth` | reading | How deep the text nests, when deeper than 64 |
| `protocol` | validating | The protocol's folder in `protocols/` |
| `definition` | validating | A definition of the protocol's `schema.json`, in `$defs` |
| `result` | validating | `valid` or `invalid` |

Each file's `seconds` is the longest that a side may take over one of its vectors.

## Running them

Every repository pins this one at `platform/`, so its tests read `platform/vectors/`. For each vector, a side's test:
1. Makes the vector's bytes: `text` or `parts` in UTF-8, or `hex`.
2. **Reading:** gives the bytes to the reader as the transport does. A WebSocket text frame and an HTTP body are decoded as UTF-8 first, and bytes that are not UTF-8 fail there: that failure counts as `refused`.
   - `read`: the reader returns the value that the platform's standard parser returns, such as Python's `json.loads` or JavaScript's `JSON.parse`.
   - `refused`: the reader refuses the text, as it refuses any that it cannot hold, without naming a value.
   - `either`: the reader may do either, but answers each vector of a `group` alike.
   - A vector whose `depth` the side reads, if it reads deeper than 64, is `either` for it: ADR-0014 asks every side to read at least 64 deep.
3. **Validating:** reads the text with the side's reader, which must read it, and validates the value against `$defs/<definition>` of `protocols/<protocol>/schema.json`, as the side validates what it receives. The side runs the vectors of each protocol that it validates.
4. **Time:** takes at most the file's `seconds` over each vector, read and validation together, on the machine that runs the tests. A reader or a validation that is linear in the text takes well under a second on a desktop PC; a quadratic one takes hours at 1 MiB.

Where each side runs them:
- **ai-cloud:** `read_json` and `protocol_schema(protocol, definition).problem` (`src/ai_cloud/shared/protocols.py`), for the cloud link, set-up and the app API.
- **ai-robot:** `read_json` and its `Schema` (`software/src/ai_robot/core/data.py`), for the cloud link and set-up.
- **ai-app:** `readJson` (`src/shared/protocols/json.ts`) and the generated checks of each definition, for the app API and set-up.

## Changing them

A vector is added for each bug class that a side meets in reading or validating, in the pull request that finds it, so that every side runs it. The files are written for review: one field to a line, and a long text as `parts`. An `id` is never reused for another text, since the sides' test reports name it.
