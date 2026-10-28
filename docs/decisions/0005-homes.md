# 0005 — Homes: a device belongs to a home, and people are its members

- **Status:** Proposed
- **Date:** 2026-10-28

## Context

- Set-up binds a device to "the owner's account" (the set-up protocol; ai-robot [ADR-0015](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0015-set-up.md)). A family is several people, though:
  - one person sets the robot up, and the whole family talks to it;
  - two parents both manage it;
  - a guest uses it for a week;
  - a device changes hands, which needs a reset (PROV-4).
- How others model it:

| Platform | Unit of ownership |
|---|---|
| Google Home | A home, with members. An admin manages people and devices; a member uses the devices. |
| SmartThings | A location, whose owner invites members. |

- Changing the unit of ownership after launch means migrating every binding, changing what set-up's registration means, and redoing the app. Before any device ships, it costs a decision.

## Decision

1. **A home owns devices.** People are its members:
   - an account with a role: one owner, any number of admins and members;
   - or a profile without an account, for someone who uses the device but never signs in, such as a grandparent or a guest.
2. **Set-up registers a device into a home**, which the app chooses, by a member allowed to add devices (the owner or an admin). The registration names the home, from set-up 2.0.
3. **A home has a time zone and default languages** ([ADR-0002](0002-languages.md), [ADR-0004](0004-conventions.md)). A device's own settings can differ, such as its languages.
4. **What the cloud keeps belongs to the home, or to a person in it**: memories, reminders, conversations.
   - Deleting a person, or the home, deletes what is theirs (PRIV-4).
   - A device moved to another home is reset first (PROV-4), and the old home keeps nothing of it.
5. **Every record that grows with use carries its home**, so that the cloud can partition or shard its data by home.
6. **Organizations** (a care home, an office) can own homes later, as a kind of owner above them, without changing devices or protocols.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Devices owned by one account, as set-up says today | A family would share one sign-in, or sharing would be bolted on later. Then every binding, the set-up protocol and the app would change. |
| Organizations from the start | Nothing needs them yet. The home leaves room for them (decision 6). |

## Consequences

- Positive:
  - families, sharing and guests fit without special cases;
  - privacy follows people: each one's memories and data are theirs to delete;
  - the cloud's data partitions naturally by home.
- Negative / accepted trade-offs:
  - set-up and the app gain a choice of home, even when there is only one;
  - roles and invitations are to be built from the start.
- Follow-up:
  - set-up 2.0: the registration names the home, alongside ADR-0001's rename to devices;
  - the app's API: homes, members, invitations and roles ([ADR-0004](0004-conventions.md));
  - in the cloud, the `accounts` module owns homes and memberships, and every module's growing tables carry `home_id`;
  - what the cloud may keep for a profile without an account, settled with the law on personal data (ai-cloud ADR-0006) before the first real users.

## References

Retrieved 2026-10-28:

- Google Home Help: [manage people and permissions](https://support.google.com/googlehome/answer/9155535).
- Samsung: [invite members using the SmartThings app](https://www.samsung.com/us/support/answer/ANS10002634/).
