# 0007 — Catalogs: Unicode MessageFormat 2, one JSON file per language

- **Status:** Proposed
- **Date:** 2026-10-30

## Context

- **[ADR-0002](0002-languages.md) leaves one choice for before the first translated text:** one catalog format for every component.
  - It must follow CLDR's plural rules, and have libraries for Python, the browser and the app's platform.
  - It named the candidates: gettext, ICU MessageFormat, Fluent and Unicode's MessageFormat 2.
- **Where catalogs are read:**

  | Component | Runtime |
  |---|---|
  | The robot's software | Python |
  | The robot's renderer | JavaScript, in a browser |
  | ai-cloud: notifications, reminders, the fixed phrases it speaks | Python |
  | ai-app | TypeScript, in React Native on Hermes ([ai-app ADR-0001](https://github.com/trungnguyen278/ai-app/blob/main/docs/decisions/0001-platforms-and-framework.md)) |

- **What messages need beyond placeholders:**
  - plurals, by CLDR's rules: English has two forms, Vietnamese one, other languages more;
  - variants that one language needs and English does not. Vietnamese addresses a person by their age and relation (*anh*, *chị*, *em*, *bạn*…), so a sentence spoken to someone can change in Vietnamese and not in English. A new language is data (ADR-0002), so these variants belong in its catalog, not in code;
  - numbers and dates, formatted from CLDR.
- **The candidates** (as of 2026-10-30):

  | Format | Standing | JavaScript | Python |
  |---|---|---|---|
  | gettext (PO files) | The oldest and most widely supported. A variant beyond plurals is another message, with a context chosen by the code. | Lingui reads PO, with ICU MessageFormat 1 inside its messages | The standard library, and Babel (2.18.0, 2026-02-01) |
  | ICU MessageFormat 1 | The most used in JavaScript | FormatJS (released 2026-10-27) | PyICU only (2.17, 2026-10-23), built from source against ICU's C++ library |
  | Fluent | Mozilla's. Built for languages that need more variants than English. | `@fluent/bundle`: last release 2025-07-18 | `fluent.runtime`: last release 2023-09-19 |
  | MessageFormat 2 (MF2) | Unicode's standard, Stable since CLDR 47 (2025). In ICU 78.3 (2026-03-17), Java's core API is a draft and C++ is in preview. `Intl.MessageFormat` is at TC39's stage 1. | `messageformat` 4.1.0 (2026-10-12), the reference implementation. Its project also converts Fluent and MessageFormat 1 into MF2. | `messageformat2` 0.1.1 (2025-12-03): MIT, one maintainer, 47 commits in the past year |

- **MF2's working group publishes a test suite**, in JSON: syntax, the selection of variants, fallbacks, and the functions.
- **Translation platforms:** Weblate (2026.10.1) supports PO, Fluent and several JSON formats, but not MF2.
- **Hermes** implements part of `Intl`. FormatJS notes that React Native may need polyfills for `Intl.PluralRules` and `Intl.NumberFormat`.

## Decision

1. **Messages are written in Unicode MessageFormat 2.**
   - Placeholders, plurals (selectors on `:number`) and any variant a language needs (`.match` on a value the code passes) are in the message.
   - A language that needs more variants than English gets them in its own catalog, with no change to code.
2. **One JSON file per language and component**, named by its BCP 47 tag (`en.json`, `vi.json`), in the component's `locales/` folder.
   - Each file is one flat object, from message IDs to messages.
   - An ID is a dotted English name for where its message appears, such as `setup.code.title`.
   - `en.json` is the source (ADR-0002).
3. **Each component reads its catalogs through a module of its own**, which holds the library:
   - `messageformat` in the robot's renderer and in the app;
   - `messageformat2` in Python, in the robot's software and in the cloud.

   The rest of the component calls only that module, so the library can change without touching a message.
4. **CI checks every component's catalogs:**
   - every message parses as MF2;
   - each translation uses the same variables as its English source;
   - an ID missing from English is an error, and one missing from another language a warning (ADR-0002);
   - the pinned library passes the working group's tests for the syntax and the functions the component uses.
5. **Formatting falls back message by message** (ADR-0002): along the owner's languages, then to English.
   - A message that fails to format falls back the same way.
   - It is logged without its arguments, which may be personal.

## Alternatives considered

| Alternative | Why not |
|---|---|
| gettext | Mature everywhere, and Python reads it without a library. But a variant beyond plurals is another message chosen by the code, so the code would have to know a language's grammar, such as Vietnamese forms of address. In JavaScript, Lingui puts ICU MessageFormat 1 inside PO files, which Python's gettext does not format. |
| ICU MessageFormat 1 | The most used in JavaScript. In Python only PyICU formats it, built from source with ICU's C++ library. MF2 is Unicode's successor to it. |
| Fluent | Built for exactly the variants Vietnamese needs. But its Python runtime's last release was in 2023, and its JavaScript one in 2025-07, while Unicode's work went into MF2. |
| Each platform's own format: Android's XML, iOS's strings, gettext, JSON | Four formats with four sets of rules, where ADR-0002 asks for one. |
| MF2 messages in the resource syntax of `@messageformat/resource` | It is not a Unicode standard yet, and only JavaScript reads it. Every runtime reads JSON. |

## Consequences

- Positive:
  - Unicode's standard, the one its implementations are moving to;
  - one syntax for Python, browsers and the app;
  - a language's variants stay with its catalog, so adding a language stays data;
  - the JavaScript side is mature.
- Negative / accepted trade-offs:
  - Python's library is young (0.1.1, one maintainer). It is pinned, wrapped by each component, and held to the working group's tests. Should it stall, the wrapper changes library: to ICU's, through PyICU, once ICU's C++ implementation leaves its preview, or to a fork with fixes;
  - translation platforms do not check MF2 yet. CI does, and translators see MF2's syntax;
  - the app may need `Intl` polyfills on Hermes.
- Follow-up:
  - each component's catalog module, first in ai-app's skeleton;
  - the robot's English texts moved into catalogs (ADR-0002);
  - a translation platform, once other people translate.

## References

Retrieved 2026-10-30:

- Unicode: [CLDR 47](https://cldr.unicode.org/downloads/cldr-47) (MF2 Stable), [the MF2 specification](https://www.unicode.org/reports/tr35/tr35-messageFormat.html), [the working group and its test suite](https://github.com/unicode-org/message-format-wg/tree/main/test), [ICU](https://icu.unicode.org/) (78.3: MF2's state in Java and C++).
- [TC39's `Intl.MessageFormat` proposal](https://github.com/tc39/proposal-intl-messageformat): stage 1.
- JavaScript: [messageformat](https://github.com/messageformat/messageformat), [FormatJS](https://github.com/formatjs/formatjs) and its [runtime requirements](https://formatjs.io/docs/guides/runtime-requirements), [Lingui](https://github.com/lingui/js-lingui), [fluent.js](https://github.com/projectfluent/fluent.js).
- Python: [messageformat2](https://github.com/tomasr8/messageformat2) ([PyPI](https://pypi.org/project/messageformat2/)), [Babel](https://github.com/python-babel/babel), [PyICU](https://pypi.org/project/PyICU/), [python-fluent](https://github.com/projectfluent/python-fluent).
- [Weblate's file formats](https://docs.weblate.org/en/latest/formats.html); [Hermes's Intl APIs](https://github.com/facebook/hermes/blob/main/doc/IntlAPIs.md).
