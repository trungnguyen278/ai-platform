# Catalogs

How every component writes the texts that people see, in every language ([ADR-0002](../docs/decisions/0002-languages.md), [ADR-0007](../docs/decisions/0007-catalogs.md)).

## Files

- **Each component keeps its catalogs** in its own `locales/` folder: one file per language, named by its BCP 47 tag, as short as it can be (`en.json`, `vi.json`, `pt-BR.json`).
- **`en.json` is the source.** Every other language is a translation of it, Vietnamese included.
- **A file is one flat JSON object**, from message IDs to messages. [`schema.json`](schema.json) checks it.

## Message IDs

- **An ID says where its message appears**, in dotted, lowercase English: `<module>.<place>.<what>`, such as `setup.code.title`. It has two parts at least.
- **An ID names one meaning.** When a message's meaning changes, its ID changes too, so that no translation of the old meaning lives on under the new one.

## Messages

- **Messages are Unicode MessageFormat 2** ([the specification](https://www.unicode.org/reports/tr35/tr35-messageFormat.html)).
- **Variables have English names**, such as `$count` and `$relation`.
- **The English source names every variable the code passes**, in a declaration (`.input`) if its own text does not use it. Another language may then use it.
- **A translation uses only the variables its English source names.** It may add variants (`.match`) on any of them.
- **Numbers and dates are formatted by MF2's functions** (`:number`, `:integer`, `:datetime`…), from the runtime's CLDR data, never by hand.

[`examples/`](examples/) has an English source and its Vietnamese translation. They show plurals in English, numbers formatted in Vietnamese, and Vietnamese forms of address, which English does not need:

```
.input {$relation :string}
.match $relation
elder_male {{Chào anh!}}
elder_female {{Chào chị!}}
younger {{Chào em!}}
* {{Chào bạn!}}
```

## Fallbacks

- **A message is looked up along the owner's languages, in order, then in English** (ADR-0002).
- **A message that fails to format falls back the same way.** The failure is logged without the message's arguments, which may be personal.

## Checks, in each component's CI

1. Every file follows [`schema.json`](schema.json), and every message parses as MF2.
2. A translation uses only the variables its English source names.
3. An ID missing from English is an error, and one missing from another language a warning.
4. The component's MF2 library passes [the working group's tests](mf2-tests/), for the syntax and the functions the component uses.

## The working group's tests

[`mf2-tests/`](mf2-tests/) holds Unicode MessageFormat's test suite, as its working group publishes it. A component's runner:

- **skips the tests whose message calls a `:test:` function.** Those functions exist only for the suite, and each implementation would have to provide them;
- **formats each test's `src`** in its `locale`, with its `params`. The defaults come from the file's `defaultTestProperties`, and `bidiIsolation` is `none` unless the test says otherwise;
- **expects** the errors of `expErrors` when it is not empty, none otherwise, and the text of `exp` when there is one.

Measured on 2026-10-30 (ADR-0007), on the tests that apply:
- `messageformat` 4.1.0, in JavaScript, passes all 434;
- `messageformat2` 0.1.1, in Python, passes 294, and does not read `.match $x`.
