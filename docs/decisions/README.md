# Architecture decision records (ADRs)

Each significant decision is a short file: context, decision, alternatives considered and consequences — so that years from now we still know **why**.

- Template: [0000-template.md](0000-template.md). How to write one: the `adr` checklist (`.claude/skills/adr/SKILL.md`).
- Never edit an old ADR to change a decision; write a new one and mark the old one "Superseded by …".
- These are the decisions that span repositories or bind every product. A repository's own decisions stay in it.

| # | Decision | Status | Date |
|---|---|---|---|
| [0001](0001-repositories.md) | Repositories: a family of AI products, sharing one platform | Accepted | 2026-10-28 |
| [0002](0002-languages.md) | Languages: Vietnamese first, any language added as data | Accepted | 2026-10-28 |
| [0003](0003-compatibility.md) | Compatibility: every device in the field keeps working | Accepted | 2026-10-28 |
| [0004](0004-conventions.md) | Conventions: one way to write identifiers, time, errors and APIs | Accepted | 2026-10-28 |
| [0005](0005-homes.md) | Homes: a device belongs to a home, and people are its members | Accepted | 2026-10-28 |
| [0006](0006-two-channels.md) | The cloud link in two channels: control always on, media only to talk | Accepted | 2026-10-28 |
| [0007](0007-catalogs.md) | Catalogs: Unicode MessageFormat 2, one JSON file per language | Proposed | 2026-10-30 |

## Earlier decisions, in ai-robot

Made before this repository existed, while the robot was the only product. They stay where they were written.

| ai-robot ADR | Decision |
|---|---|
| [0003](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0003-neutral-repo-naming.md) | Repository names; superseded by 0001 here, but for its rule against product names |
| [0007](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0007-cloud-link-transport.md) | The cloud link over a WebSocket; superseded by 0009 |
| [0008](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0008-cloud-link-messages.md) | The cloud link's messages: MCP-shaped capabilities and events |
| [0009](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0009-cloud-link-webrtc.md) | The cloud link over WebRTC, through LiveKit; amended by 0006 here: a room only to talk |
| [0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md) | A device's identity: a key in a TPM, short-lived tokens |
| [0012](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0012-end-of-speech.md) | The end of the user's speech: the cloud decides; its fallback amended by 0006 here: the device ends a conversation after a silence |
| [0014](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0014-updates.md) | Updates: whole signed images, announced by the cloud |
| [0015](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0015-set-up.md) | Set-up: the app over Bluetooth LE, secured by a code on the screen |
