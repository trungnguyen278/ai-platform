# 0009 — People in a home: what roles allow, how people join, how a home changes hands

- **Status:** Proposed
- **Date:** 2026-11-03
- **Revised:** 2026-11-03: redone from what large products do, at the owner's request. A home is deleted only by its last person with an account, handing it over takes one step, and a person's name is the home's.

## Context

- [ADR-0005](0005-homes.md) decided that a home owns devices, and that its people are one owner, any admins and members, and profiles without an account. It left to the app's API what each role may do, how a home begins, how people join, and how a home changes hands or ends. The app API 1.0 already answers `owns_home_with_members`.
- **These are questions of what people experience,** which large products have already tried on real people. So this decision follows them, and departs only for a constraint of this project's, which it names.
- **The constraints:**
  - Accounts are never matched by email, and Apple may give a relay or no email at all ([ADR-0008](0008-sign-in.md)). The cloud sends no email.
  - A member talks to a device with microphones, and perhaps a camera.
- **Smart home products** (retrieved 2026-11-03):

| Product | How a home begins | Who may do what | How people join | How it changes hands and ends |
|---|---|---|---|---|
| Tuya, the App SDK | "A new user usually has no home", and the app then creates one. | One owner. An admin, "added only by a home owner", adds and edits common members, and "cannot delete a home". A common member views and leaves. | By account, with a role; or with a code "which can only be used by one user". A code has a validity period, can be revoked, and pending ones are listed. Its request names only the home. | `transferOwner`, to another member: the old owner becomes an admin, and can then leave. A home is deleted only with no other member, and that removes its devices. |
| Google Home | A first-time user creates one. "Up to 5 homes" for each account. | Admins and members. Admins are equals: they "add and remove other people, including you". "Everyone can check who is an Admin or Member." | An email to the person, who accepts in the app ("Agree & join"). The inviter picks the role. | There is no owner. A home is deleted "only if you are the last person in it", and its devices must be set up again. |
| SmartThings | Not documented | An owner and members. "Only the owner of the location can remove members." | An email to a Samsung account, or a QR code. The invitee accepts in the app. | "Give devices to someone else": the recipient scans a QR code (search excerpt). |
| Apple Home | Not looked at | The owner, and residents or guests, whom the owner may allow to add and edit | An invitation to an Apple Account, with a role, accepted in the app | "Apple doesn't provide any mechanism" to hand a home over. 9to5Mac asks for one, with the former owner demoted. |
| Home Assistant | The first start creates the owner, and asks for a location for the time zone. | One owner, who cannot be deleted. Administrators, and users who only use. A *person* may have no login, and administrators rename people. | No invitations: an administrator creates people. | Not documented |

- **Codes and links elsewhere:**
  - Telegram: a link may have an expiry and a usage limit, may need an admin's approval, and can be revoked.
  - Discord: seven days by default, with a limit on uses.
  - Signal: an admin's approval is optional, and a link can be reset.
  - Open source: Homebox keeps a token's hash and returns the token once, with `uses` and `expires_at`, for its owner to make. Mealie has `uses_left`, one by default.
- **Handing over elsewhere:**
  - Telegram asks for the owner's 2FA password, from a session older than a day. It documents no acceptance.
  - Discord, by third-party guides: at once, after an acknowledgement. Community posts report people left with a server they did not want.
  - Google Drive: within an organization, "the transfer doesn't require the new owner to accept"; between personal accounts, it does. The old owner is "downgraded to Editor".
  - GitHub: the new owner of a personal repository accepts within a day.
  - Ring: the new owner must set the device up again.

## Decision

1. **A home begins when a person creates it,** as in Tuya and Google Home. The cloud makes none at sign-up. The app asks for a name, and offers the phone's time zone and languages. Its creator is its owner.
2. **What each role may do,** as Tuya's table, which has one owner, as [ADR-0005](0005-homes.md) does:

   | | Owner | Admin | Member |
   |---|---|---|---|
   | See the home and who is in it, and use its devices | ✓ | ✓ | ✓ |
   | Change the home's name, time zone and languages | ✓ | ✓ | |
   | Add and remove devices ([ADR-0005](0005-homes.md), decision 2) | ✓ | ✓ | |
   | Invite people, and add profiles | ✓ | ✓ | |
   | Rename or remove members and profiles | ✓ | ✓ | |
   | Rename or remove an admin, and change a person's role | ✓ | | |
   | Hand the home over, and delete it | ✓ | | |
   | Rename themself | ✓ | ✓ | ✓ |
   | Leave the home | | ✓ | ✓ |

3. **People join with a code,** as Tuya's, which SmartThings and Telegram also offer as a scan or a link:
   - **The code** works once, as Tuya's. It expires after `invitation_lifetime`, and can be revoked. Open invitations are listed.
   - **It is 32 random bytes,** and the cloud shows it once and keeps its hash, as Homebox does.
   - **It travels by any channel:** a link in a chat, or a QR code on the inviter's phone.
   - **Before joining,** the person sees the home's name and who invited them, and agrees, as in Google Home and SmartThings.
   - **It joins as a member,** as a code in Tuya, Telegram and Homebox names no role. The owner raises the person afterwards.
   - **Removing or demoting the person who made it revokes it,** so that nobody keeps a way back in.
4. **A profile is a person without an account,** as Home Assistant's. The owner or an admin adds one, with a name. To the cloud, a profile and a person with an account are the same thing: one identifier for a person in a home, to which what the cloud keeps refers.
5. **A person's name in a home is that home's,** as in Tuya and Home Assistant. It starts as their account's. The role table says who may change it.
6. **Handing a home over is one step, among people already in it,** as in Tuya and Telegram. The owner names another person with an account, after a fresh sign-in. That person becomes the owner, and the old owner an admin, who can then leave.
7. **Ending:**
   - **The owner cannot leave,** as in Tuya and Home Assistant. They hand the home over, or delete it.
   - **A home is deleted only by an owner who is its last person with an account,** as in Google Home and Tuya. The others leave, or the owner removes them, first. Profiles go with the home. A fresh sign-in comes first.
   - **Deleting a home revokes its devices' registrations** (SEC-3), as Tuya removes them and Google Home has them set up again. Each device gets `bye` `revoked`, and offers set-up (PROV-3).
   - **Leaving, or being removed,** deletes what belongs to that person in that home ([ADR-0005](0005-homes.md), decision 4; PRIV-4). Their account and their other homes stay.
   - **Deleting an account** removes its person from every home. A home it owns goes with it if nobody else with an account is in it. Otherwise the cloud answers `owns_home_with_members`.
8. **A home the person is not in does not exist for them:** the cloud answers `404`, not `403` (SEC-6).

### Where this departs from them, and why

- **No invitation to a known account,** which Google Home, SmartThings, Apple Home and Tuya all offer, because accounts are not matched by email ([ADR-0008](0008-sign-in.md)). The code alone remains, which Tuya and SmartThings also have.
- **A fresh sign-in before deleting a home or handing it over,** which those products' help pages do not mention. A phone left unlocked must not be enough to destroy or give away a home, as for deleting an account ([ADR-0008](0008-sign-in.md)). Telegram asks the same of its owners, with a password.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A home made by the cloud at sign-up | No product read does this. An invited person would own an empty home. |
| Equal admins with no owner, as Google Home | [ADR-0005](0005-homes.md) chose one owner, as Tuya, SmartThings, Apple Home and Home Assistant have. |
| An owner who deletes a home with people in it | Google Home and Tuya refuse it. It would destroy what belongs to the others. |
| The person offered a home must accept, as GitHub and Google Drive between personal accounts | Those hand a thing to someone outside it. Here the person is already in the home, like Drive's transfer within an organization, which needs no acceptance. It would also add an offer's state and three endpoints. The cost is below, in the trade-offs. |
| The role inside the invitation, as Google Home and Apple Home | Those invitations are bound to a person. A code is not. Tuya's request for one names only the home, though Tuya can set a role on the pending invitation afterwards. A leaked code could otherwise make a stranger an admin. A later version can add an optional role. |
| An admin approves each person who joins, as Telegram and Signal offer | No smart home product read makes this the way to join, and they offer it as an option. It can come later as an optional field. |
| A link that works many times, as Telegram's and Discord's can | Tuya's codes work once. A family invites few people, and one leak would let in any number. |
| Refusing to delete a home that still has devices | Tuya and Google Home do not. A lost device would keep a home alive for good. |

## Consequences

- Positive:
  - people meet what other smart home apps already taught them;
  - one way to join, with no email, over the chat apps families already use;
  - a leaked code gives a member's rights at worst, once, for days, and in plain sight.
- Negative / accepted trade-offs:
  - **A code can be forwarded.** A stranger holding it could join before the person it was meant for. That person's code then fails, and the inviter sees the stranger in the list and removes them.
  - **A person can be made an owner without being asked,** which stops them deleting their account while others are in the home. They can hand the home back in one step, or remove the others and delete it.
  - **A link needs the project's domain,** for the phone to open the app. Until there is one, the code travels as a QR code read by the app's own scanner, or a pasted link.
  - **A person who leaves loses what belonged to them there,** so the app warns first.
- Follow-up:
  - the app API 1.1: these endpoints;
  - ai-cloud's `accounts`: homes, members and invitations. Other modules learn of a deleted person or home from its domain events;
  - ai-cloud's architecture builds invitations and several homes "when others join": this decision says what is built, not when;
  - ai-app's `homes`;
  - set-up's registration into a home, in a later minor version of the app API;
  - telling a person that someone joined, or that they were removed, as Google Home does, once the app API has notifications;
  - what the cloud may keep for a profile: ai-cloud ADR-0006, as [ADR-0005](0005-homes.md) says.

## References

Retrieved 2026-11-03:

- Tuya, the Smart App SDK: [home member management](https://developer.tuya.com/en/docs/app-development/extension-family-member?id=Kcy2iwdhz60pm), [home management](https://developer.tuya.com/en/docs/app-development/extension-sdk-tutorial-family?id=Kd8k3f7cbsk83), and [member information management on iOS](https://developer.tuya.com/en/docs/app-development/iOS-family-member?id=Kaixlyjh6uer8).
- Google Home Help: [manage people and permissions](https://support.google.com/googlehome/answer/9155535), and [organize your homes and devices](https://support.google.com/googlehome/answer/15559809).
- Samsung: [invite members using the SmartThings app](https://www.samsung.com/ph/support/apps-services/invite-members-using-the-smartthings-app/).
- Apple Support: [share control of your home](https://support.apple.com/102386). 9to5Mac: [we really need a way to hand over ownership of an Apple Home](https://9to5mac.com/2026/07/03/we-really-need-a-way-to-hand-over-ownership-of-an-apple-home/), 2026-07-03.
- Home Assistant: [people and users](https://www.home-assistant.io/docs/configuration/user-configuration/), [the person integration](https://www.home-assistant.io/integrations/person/), and [onboarding](https://www.home-assistant.io/getting-started/onboarding/).
- Telegram: [invite links](https://core.telegram.org/api/invites), and [`channels.editCreator`](https://core.telegram.org/method/channels.editCreator).
- Signal: [link up with group links](https://signal.org/blog/group-links/).
- Homebox: [its invitation token](https://github.com/sysadminsmedia/homebox/blob/main/backend/internal/data/ent/schema/group_invitation_token.go), and [making one](https://github.com/sysadminsmedia/homebox/blob/main/backend/internal/core/services/service_group.go). Mealie: [its invite token](https://github.com/mealie-recipes/mealie/blob/mealie-next/mealie/db/models/household/invite_tokens.py).
- Handing over: [GitHub](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository), [Google Drive](https://support.google.com/drive/answer/2494892), and [Ring](https://ring.com/support/articles/k8jn9/transfer-device-ownership).
- Read only as search excerpts or third-party pages, since the originals refuse automated readers or were not found:
  - Google Home's first run: [Business Insider](https://www.businessinsider.nl/how-to-set-up-and-use-the-google-home-app-on-your-mobile-device/), an older guide;
  - SmartThings' transfer: [SamMobile](https://www.sammobile.com/news/smartthings-transfer-ownership-of-your-smart-home-setup-in-one-go/), 2026;
  - Discord's [invites](https://support.discord.com/hc/articles/208866998), and its transfer: [Appuals](https://appuals.com/transfer-ownership-discord-server/), and a [community post](https://support.discord.com/hc/en-us/community/posts/1500001307902-Unable-to-delete-unwanted-server).
