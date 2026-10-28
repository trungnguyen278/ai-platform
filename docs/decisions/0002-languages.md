# 0002 — Languages: Vietnamese first, any language added as data

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

- The products are for Vietnamese speakers first. Other languages are to come, and adding one must not mean changing code or protocols across the repositories.
- Language reaches every part of a product, the robot's for example:
  - **the screen:** settings, set-up, status scenes, and dates, times and numbers;
  - **the voice:** what it understands and how it answers, which the cloud does: speech recognition, the language model, speech synthesis (ai-robot [ADR-0009](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0009-cloud-link-webrtc.md));
  - **the wake word**, spotted on the device (ai-robot [ADR-0013](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0013-listening-on-the-robot.md));
  - **the app**, and what the cloud writes, such as reminders.
- Everything in the repositories is written in English. Today the robot's texts are English, written in its code: the settings' titles, the set-up scene's lines.
- Vietnamese speakers often mix in English words, and a family may want a device to speak both.
- How others handle it:

| Product | Languages |
|---|---|
| Amazon Alexa | A device language, and a multilingual mode with two languages, in which Alexa answers in the language it is spoken to. |
| Google Assistant | Two languages chosen in its settings (bilingual, from 2018); it answers in the language spoken, though each request had to be in one language. |
| Home Assistant | Texts are keys, with one JSON file of translations per language; the frontend shows them, and volunteers translate on a platform. |
| Android, iOS | Texts in a catalog per locale; dates, times and numbers formatted by the system from Unicode's CLDR data. |

## Decision

1. **Languages are named with BCP 47 tags** ([RFC 5646](https://www.rfc-editor.org/rfc/rfc5646)) everywhere: settings, protocols, catalogs. Tags are as short as they can be (`vi`, `en`); a region is added only where it changes something (`pt-BR`).

2. **The owner chooses each device's languages**, as one of its settings (for the robot, ai-robot [ADR-0016](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0016-settings.md)): an ordered list.
   - The first is the language the device shows, and speaks when it starts a conversation.
   - The device understands every language in the list, and answers in the one it is spoken to, as Alexa's multilingual mode and Google's bilingual mode do.
   - As shipped, the list is Vietnamese alone. During set-up, the app offers the phone's own languages.

3. **The source texts are English, and every language is a translation**, Vietnamese included.
   - Code never holds a text that people see: it names a message, and each language's catalog gives its text.
   - Each component translates the texts it writes, from catalogs of its own: a device's software, its renderer, the cloud, the app.
   - A message missing from a language falls back along the owner's list, then to English.
   - Dates, times and numbers are formatted from Unicode's CLDR data, in the browser by `Intl` and elsewhere by the platform's library, never by hand.

4. **The protocols carry languages**, in versions that only add:
   - the cloud link: the device's languages when a session opens and whenever they change, and the language of each turn and of each text the cloud sends to be shown;
   - set-up: the phone's languages, offered to the device;
   - the robot's screen protocol (ai-robot's own): the language the renderer shows, so that it picks its catalog and formats dates and numbers.

   Data a device draws carries codes and numbers where it can, not sentences. A weather scene gets the condition's code and the temperature, and the device writes them in its language. What a person said or wrote, such as a reminder's title, passes through unchanged.

5. **Devices speak only through the cloud.** Their own cues stay without words: faces, sounds and lights, which need no translation.

6. **The cloud supports a language only if it handles every step of a conversation in it**: recognition, mixed with English as people speak it, the language model, and a voice for the device. Vietnamese is the first. The cloud's conversation pipeline is chosen for that, in ai-cloud's own decision.

7. **A wake word is the device's name**, the same in every language. Its model is trained on speakers of every language the device supports.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Vietnamese only, written in the code | Each new language would mean finding every text in every repository. The repositories are in English, so the code's texts would be in a language their readers may not read. |
| One language per device | A family that speaks Vietnamese and English would have to choose. Alexa and Google Assistant both moved to two languages at once. |
| A device's software sends message keys, and its renderer translates every text (Home Assistant's frontend) | The robot's settings come from the modules that offer them. A module would need to place its texts in the renderer's catalogs, so the catalogs would no longer follow the components. |
| Detect the language of each turn, with no setting | A device still needs a language for its screen, and for what it says first. A list also bounds what the recognizer listens for. |

## Consequences

- Positive:
  - a new language is a set of catalogs and a cloud that supports it: no change to code or protocols;
  - Vietnamese is built the same way as any later language, so nothing assumes it;
  - the protocols carry what the cloud needs to answer in the language spoken.
- Negative / accepted trade-offs:
  - every visible text goes through a catalog, Vietnamese included, even while it is the only translation;
  - a language is only as good as the cloud's recognition and voice for it, so some languages may wait for good services;
  - the catalogs must stay in step with the code, which tests check: a message missing from English is an error, one missing elsewhere a warning.
- Follow-up:
  - the catalogs' format, one for every component: it needs CLDR plural rules and libraries for Python, the browser and the app's platform. The candidates are gettext, ICU MessageFormat, Fluent and Unicode's MessageFormat 2. It is settled before the first translated text;
  - the robot's `languages` setting, and its English texts moved into catalogs: its software and its renderer;
  - the protocols' additions: the cloud link and set-up here, the screen in ai-robot;
  - the cloud's conversation pipeline, in ai-cloud;
  - the robot's name, then its wake word's model.

## References

- [RFC 5646](https://www.rfc-editor.org/rfc/rfc5646), tags for identifying languages (BCP 47); [RFC 4647](https://www.rfc-editor.org/rfc/rfc4647), matching them.
- [Unicode CLDR](https://cldr.unicode.org/), locale data: dates, numbers, plural rules.
- Retrieved 2026-10-28:
  - Amazon: [Ask Alexa to speak in multiple languages](https://www.amazon.com/gp/help/customer/display.html?nodeId=G9JFV7VRANZDKKWG), and [how Alexa is bringing multilingual households closer together](https://www.aboutamazon.com/news/devices/how-alexa-is-bringing-multilingual-households-closer-together);
  - [Google's Assistant becomes bilingual](https://www.cnbc.com/2018/08/30/googles-assistant-home-smart-speaker-multiple-languages-bilingual-.html), CNBC, 2018-08-30;
  - [Home Assistant's translations](https://developers.home-assistant.io/docs/internationalization/core/).
