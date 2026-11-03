# 0009 — People in a home: what roles allow, how people join, how a home changes hands

- **Status:** Proposed
- **Date:** 2026-11-03

## Context

- [ADR-0005](0005-homes.md) decided that a home owns devices, and that its people are one owner, any admins and members, and profiles without an account. It left to the app's API what each role may do, how a home begins, how people join, and how a home changes hands or ends. The app API 1.0 already answers `owns_home_with_members`.
- **What binds the choice:**
  - Accounts are never matched by email, and Apple may give a relay or no email at all ([ADR-0008](0008-sign-in.md)). The cloud sends no email.
  - A member talks to a device with microphones, and perhaps a camera. So nobody should join by accident, and nobody removed should have a way back.
  - Being the owner binds a person: they cannot delete their account while others depend on the home (`owns_home_with_members`).
- **How others do it** (retrieved 2026-11-03):

| Product | Roles | Joining | Changing hands |
|---|---|---|---|
| Google Home | Admins and members. Admins are equals: they "add and remove other people, including you". | An email to the person, who accepts in the app. The inviter picks the role. | The last admin leaves only by deleting the home. |
| SmartThings | An owner and members. "Only the owner of the location can remove members." | An email to a Samsung account, or a QR code | The recipient scans a QR code from the owner's phone (search excerpt, 2026). |
| Apple Home | The owner, and residents or guests, who may be allowed to add and edit | An invitation to an Apple Account, with a role, accepted in the app | Not documented |
| Wiser by SE | An owner and members | An invitation code, shared in any way, valid for three days (search excerpt) | Not documented |
| Home Assistant | A *person* and a user account are apart. A person may have no login: "they can still be used for device tracking, show up on a map, and be included in automations." | Not looked at | Not looked at |
| Ring | Not looked at | Not looked at | The owner starts it, and the new owner must set the device up again. |
| Signal, for group chats | Not looked at | A link. Admins can "require admin approval for people trying to join", and "reset the link". | Not looked at |

## Decision

1. **A home begins when a person creates it.** The app asks for a name, and offers the phone's time zone and languages. Its creator is its owner. Nobody gets a home by signing in, so a person who joins by invitation never owns an empty one.
2. **What each role may do:**

   | | Owner | Admin | Member |
   |---|---|---|---|
   | See the home and who is in it, and use its devices | ✓ | ✓ | ✓ |
   | Change the home's name, time zone and languages | ✓ | ✓ | |
   | Add and remove devices ([ADR-0005](0005-homes.md), decision 2) | ✓ | ✓ | |
   | Invite people, and add, rename and remove profiles | ✓ | ✓ | |
   | Remove a member | ✓ | ✓ | |
   | Remove an admin, and change a person's role | ✓ | | |
   | Hand the home over, and delete it | ✓ | | |
   | Leave the home | | ✓ | ✓ |

3. **People join by invitation, with a code:**
   - **The code** is 32 random bytes. It works once, and expires after `invitation_lifetime`: three days, to start.
   - **Whoever holds it may join.** It travels by any channel: a link in a chat, or a QR code on the inviter's phone.
   - **The cloud shows it once,** when it is made, and keeps only its hash.
   - **Before joining,** the person sees the home's name and who invited them.
   - **It always joins as a member.** The owner raises a person afterwards, so that a leaked code never gives more than a member's rights.
   - **An invitation can be revoked.** Removing or demoting the person who made it revokes it too, so that nobody keeps a way back in.
   - **Everyone sees who joined,** in the home's list of people.
4. **A profile is a person without an account.** The owner or an admin adds one, with a name. It cannot sign in, and has no role. To the cloud, a profile and a person with an account are the same thing: one identifier for a person in a home, to which what the cloud keeps refers. A later version can then let the person behind a profile join with an account, and keep what is theirs.
5. **Handing a home over takes two people.** The owner offers it to a person with an account, after a fresh sign-in. That person accepts, and becomes the owner; the old owner becomes an admin. The offer ends after `handover_lifetime`, when either of them cancels it, or when that person leaves.
6. **What goes with a person, or a home:**
   - **Leaving, or being removed,** deletes what the cloud keeps of that person in that home ([ADR-0005](0005-homes.md), decision 4; PRIV-4). Their account and their other homes stay.
   - **Deleting a home** is for its owner, after a fresh sign-in. It deletes what the home and its people have there, and revokes its devices' registrations (SEC-3): each device gets `bye` `revoked`, and offers set-up (PROV-3).
   - **Deleting an account** removes its person from every home. A home it owns goes with it, if no other person with an account is in that home, since a profile cannot take a home over. Otherwise the cloud answers `owns_home_with_members`.
7. **A home the person is not in does not exist for them:** the cloud answers `404`, not `403` (SEC-6).

## Alternatives considered

| Alternative | Why not |
|---|---|
| A home made at the first sign-in | An invited person would own an empty home, and a sign-in does not know the time zone. ai-app's first screen already meets a person with no home. |
| Equal admins with no owner, as Google Home | [ADR-0005](0005-homes.md) chose one owner. Admins who can remove each other can lock out the person who set the home up. |
| Admins who remove each other, or change roles | The same lock-out, and a way for a member raised by mistake to raise others. With one person deciding who holds power, the rule is short to explain. |
| Invitations sent to an email address, as Google Home, SmartThings and Apple Home | Accounts are not matched by email, Apple may give a relay, and the cloud would need to send email. |
| A link that works many times, as Signal's | One leak lets in any number of people, and a link that lives on has time to leak. |
| An admin approves each person who joins, as Signal offers | It closes the gap a bearer code leaves, at the price of a second person acting at the right moment, and a pending state for each person. A code that works once and expires in days, with everyone seeing who came, narrows that gap enough for a family. It can come later as an optional field, if that proves wrong. |
| A short code to type, like a PIN | It would need careful limits against guessing. With 32 random bytes guessing is no risk, and a person never types it. |
| The role inside the invitation, as Google Home and Apple Home | A leaked code could then make a stranger an admin. |
| Handing over in one step | Being the owner stops a person deleting their account, so nobody should become one without agreeing. Ring and SmartThings also need the recipient to act. |
| Refusing to delete a home that has devices | A lost or broken device would keep a home alive for good. Revoking the registration is enough: a device that comes back offers set-up. |
| Keeping what a person leaves behind, for the home | [ADR-0005](0005-homes.md) says that deleting a person deletes what is theirs. |

## Consequences

- Positive:
  - one way to join, with no email, over the chat apps families already use;
  - a leaked code gives a member's rights at worst, once, for days, and in plain sight;
  - a person's identifier in a home outlives any later binding to an account.
- Negative / accepted trade-offs:
  - **A code can be forwarded.** A stranger holding it could join before the person it was meant for. That person's code then fails, and the inviter sees the stranger in the list and removes them.
  - **A link needs the project's domain,** for the phone to open the app (Android App Links, iOS universal links). Until there is one, the code travels as a QR code read by the app's own scanner, or a pasted link.
  - **Handing over needs both people,** and an owner whose people will not accept must delete the home to delete their account.
  - **A person who leaves loses what the cloud kept of them there,** so the app warns first.
- Follow-up:
  - the app API 1.1: these endpoints;
  - ai-cloud's `accounts`: homes, members and invitations. Other modules learn of a deleted person or home from its domain events;
  - ai-cloud's architecture builds invitations and several homes "when others join": this decision says what is built, not when;
  - ai-app's `homes`;
  - set-up's registration into a home, in a later minor version of the app API;
  - telling the owner and the admins that someone joined, once the app API has notifications;
  - what the cloud may keep for a profile: ai-cloud ADR-0006, as [ADR-0005](0005-homes.md) says.

## References

Retrieved 2026-11-03:

- Google Home Help: [manage people and permissions](https://support.google.com/googlehome/answer/9155535).
- Samsung: [invite members using the SmartThings app](https://www.samsung.com/us/support/answer/ANS10002634/).
- Apple Support: [share control of your home](https://support.apple.com/102386).
- Home Assistant: [the person integration](https://www.home-assistant.io/integrations/person/).
- Ring: [transfer device ownership](https://ring.com/support/articles/k8jn9/transfer-device-ownership).
- Signal: [link up with group links](https://signal.org/blog/group-links/).
- Read only as a search result's excerpt, since these pages refuse automated readers:
  - Wiser by SE's [frequently asked questions](https://www.clipsal.com/faq/faq000195543): "a code for joining a home as a member will be valid for three days";
  - SamMobile: [SmartThings: transfer ownership of your smart home setup](https://www.sammobile.com/news/smartthings-transfer-ownership-of-your-smart-home-setup-in-one-go/), 2026.
