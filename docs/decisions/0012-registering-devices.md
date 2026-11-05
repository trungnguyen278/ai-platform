# 0012 — Registering a device into a home: the cloud's challenge, signed by the device, relayed by the app

- **Status:** Accepted
- **Date:** 2026-11-05

## Context

- **What is settled:**
  - A device's identity is registered during set-up, by its owner, through the app, and the owner or the cloud can revoke it (SEC-3). A revoked device offers set-up again (PROV-3), and a new owner takes a device only after a reset (PROV-4).
  - The identity is a P-256 key that the device's TPM makes and keeps, and an identifier that the device makes (ai-robot [ADR-0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md)). The robot keeps both in its TPM, so a factory reset, which clears the TPM, makes both anew.
  - Set-up 2.0 has the app relay a registration that the device signs (ai-robot [ADR-0015](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0015-set-up.md)): a JWT with the device's identifier, its public key, the cloud's challenge as `nonce`, and the cloud's address as `aud`. The challenge carries the home, which the device never learns ([ADR-0005](0005-homes.md)). Only the owner and admins add or remove devices ([ADR-0009](0009-people-in-a-home.md)).
  - Deleting a home revokes its devices (the app API 1.1). ai-cloud relays `accounts.home.deleted.v1` for its `devices` module (ai-cloud ADR-0009).
- **What set-up 2.0 left to the app API:** how the app gets a challenge, how the cloud answers a registration and its retry, what happens to a device that is already in a home, and how one device is removed.
- **How others bind a device to its owner** (retrieved 2026-11-05):

| Product | What the app gets from the cloud | What the device does with it | A device already someone's |
|---|---|---|---|
| ESP RainMaker, challenge-response mapping, recommended, and on by default on most platforms | A challenge, over the signed-in session | Signs it, and the app forwards the answer for the cloud to verify. "No shared secret is exchanged", and "the node does not need network connectivity". The device shows in the account as soon as set-up starts. | Not documented |
| AWS IoT, provisioning by trusted user | A claim certificate, which "expires after five minutes" | Gets it with the Wi-Fi credentials, connects with it, and registers itself | Not documented |
| Tuya | A pairing token for a home, with the cloud's `region`. It "is valid for 10 minutes and expires immediately after the device is paired". | Activates itself with it, once online | Unbinding clears the device's local pairing and schedule data. A device removed while offline unbinds "after getting back online". |
| Matter | No cloud: the commissioner draws a random 32-byte nonce | Signs a request for a new operational key with its attestation key. The administrator's certificate then names its fabric and node. "A fail-safe provides a way to roll back the device" if commissioning does not complete. | Joins another fabric only when "the Matter controller of that fabric" opens a commissioning window |
| WebAuthn (a browser relays a security key) | A random challenge, which "SHOULD therefore be at least 16 bytes long" | Signs it with a new credential | "If the credentialId is already known then the Relying Party SHOULD fail this registration ceremony" (§7.1, step 26) |
| Amazon, Frustration-Free Setup | Nothing: the device is the buyer's from the sale. "We save the unique identifier of the device we shipped to you." | Joins through a nearby Amazon device, which registers it to the account | A device "factory reset" or "received as gifts" is set up again |
| Google Home | Not documented | Not documented | Removing a device is not a factory reset: "Factory reset your device before you add it to another home." |

- **Where they agree:**
  - the cloud's proof is short-lived: five minutes for AWS's claim, ten for Tuya's token, which also ends once a device is paired with it;
  - it belongs to the person signed in, and to a home where there are homes (Tuya);
  - the device proves that it holds its key by signing (RainMaker, Matter, WebAuthn);
  - a device that is already someone's is not taken without them (Matter, WebAuthn, Google Home).
- **Where they split:**
  - **Who reaches the cloud:** the device itself, once online (Tuya, AWS), or the app, with what the device signed (RainMaker's recommended mapping, Matter, WebAuthn). Set-up 2.0 relays already.
  - **Hardware attestation:** Matter requires it, "to determine whether a device has been certified and is a genuine Matter device". Azure's Device Provisioning Service checks a TPM's endorsement key against an enrollment list, which "the device vendor" fills "during manufacture or final testing". WebAuthn's default is none: "The Relying Party is not interested in authenticator attestation."
  - **When the binding holds:** at once (RainMaker), once the device reaches the cloud (Tuya, AWS), or undone if the end does not come (Matter's fail-safe).

## Decision

1. **The challenge.** The owner or an admin of a home asks the cloud for one: `POST /app/v1/homes/{home_id}/device-challenges`.
   - It is 32 random bytes, as the app API's nonces, for that home and that account. It is valid for `challenge_lifetime`, 300 s as AWS's claim, and works once.
   - **The answer names `server`,** the address that devices use, from the cloud's configuration. The app passes it on in `register`. It need not be the app's own, as on a developer's network, and the cloud can name another for its devices, as Tuya's cloud gives its `region` with its token.
2. **The registration.** The app relays what the device signed: `POST /app/v1/homes/{home_id}/devices`, with an `Idempotency-Key`.
   - The cloud checks it as set-up 2.0 says. The challenge must be one it issued for this home to this account, and the account must still be allowed to add devices there.
   - **The first registration that presents a challenge uses it,** whether or not the cloud then registers the device, so that nothing is tried twice on one challenge. A retry with the same `Idempotency-Key` gets the first answer, so a lost answer costs nothing.
   - **A failed registration gets one code,** `registration_invalid`: the app does the same for every cause, a new challenge, once.
   - The app sends set-up's `finish` once the cloud has answered. After a refusal, it may send `register` again in the same session, with a new challenge.
3. **What binds the device to the home is the cloud's record** of its identifier and its key, in the home, from the moment the cloud accepts the registration, as in RainMaker's mapping.
   - **The device belongs to the home** ([ADR-0005](0005-homes.md)), not to the person who added it, and stays when they leave.
   - **The device knows that it is bound** when the token endpoint first accepts its assertion, as set-up 2.0 has it. The app waits for that first connection and shows it.
4. **The cloud trusts the key from the owner and from possession, not from the hardware:**
   - the app relays the key from a session that the code on the device's screen secures (PROV-2), so it is the key of the device in front of the owner;
   - the device signs the cloud's challenge with it, so it holds the private key now;
   - the challenge belongs to one person and one home, so a registration cannot be replayed, or used elsewhere.

   **There is no attestation.** It proves that a device came from its maker's line, against a root or a list that the maker keeps from its factory: Matter's certified vendors, the enrollment lists of Azure's service. The project's devices have no such step, and a TPM's own certificate would prove only that some genuine TPM holds the key, not that the device is one of the project's. Should the cloud need to refuse devices that the project did not make, a minor version of set-up can add attestation to the registration, as an optional part, and the cloud then require it by kind of device.
5. **One home per device, and one identifier per key:**
   - **the same device, already in the challenge's home** with the same identifier and key, gets `200` with the device: one that lost its state registers again, as set-up 2.0 has it;
   - **any other key or identifier that the cloud holds** gets `409` `device_taken`, as WebAuthn fails a credential it already knows: the device is in another home, or its key or its identifier is another device's. That home's owner or an admin removes the device, or the device is reset, which gives it a new key and a new identifier;
   - **identifiers compare as UUIDs,** whatever the case of their letters, which a UUID's text may mix ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562), §4);
   - **the limit counts new devices only,** so that a full home still takes back a device that lost its state.
6. **Removing a device revokes it,** for the owner and admins: `DELETE /app/v1/homes/{home_id}/devices/{device_id}`. Deleting a home does the same for each of its devices.
   - The cloud ends the device's session with `bye` `revoked`, refuses its tokens and assertions, and forgets its key. What belongs to the home and its people stays ([ADR-0005](0005-homes.md), decision 4).
   - The device offers set-up (PROV-3). Its key unknown again, it can be registered into any home, as a new device.
   - **Removing does not erase the device,** as in Google Home: its owner resets it before giving it away (PROV-4).
7. **Everyone in the home sees its devices:** each one's kind, model and software, from its latest `hello` on the cloud link, and whether it is connected.
8. **Limits:** `devices_per_home`, 300 as SmartThings allows a location, and `challenge_rate` for each account, 10 a minute as for invitation codes.
9. **Versions** ([ADR-0003](0003-compatibility.md)):
   - **the app API 1.4,** a minor version: new endpoints, which an app of 1.3 never calls;
   - **set-up stays 2.0:** no message changes. Its README says where the challenge and the address come from;
   - **the cloud link does not change:** `bye` `revoked` and `invalid_client` already revoke.

## Alternatives considered

| Alternative | Why not |
|---|---|
| The device registers itself, once online, with a token from the app (Tuya, AWS) | The token is a secret until it is used, and nothing is checked until the device is online. Set-up 2.0 relays, as RainMaker now recommends, since "no shared secret is exchanged" and "the node does not need network connectivity". |
| The device signs its home, without a challenge | The device would learn its home, and a registration would never expire: a copy could add the device again after it was removed. |
| The app's own address for the cloud, as `server` | The app may reach the cloud at another address than its devices do, as on a developer's network, and the cloud could never name another for its devices. |
| A binding that holds only once the device has connected (Tuya, AWS), or is undone if it does not (Matter's fail-safe) | A device whose home loses the Internet for a while would lose its registration, and need set-up again. The app registers a device once it has joined a network that reaches the Internet, and waits for its first connection. One that never comes shows, and the device is removed. |
| A device in another home moves to the new one | Someone holding a device whose binding was cleared, but not its TPM, could take it from its home without its owner. Matter asks that home's administrator, Google Home a reset, and WebAuthn fails a known credential. |
| Attestation now: the TPM's endorsement key, as Azure's service, or a maker's certificate, as Matter | It needs a root or a list of the project's devices, made at a factory that does not exist (decision 4). |
| A challenge that works for several devices, or for longer, as Tuya's app SDK (ten minutes) | The app asks for one just before `register`, for one device: five minutes covers it, as AWS's claim. |
| An error for each failed check of a registration | The app does the same for each: a new challenge, once. `detail` may say which, for logs. |

## Consequences

- Positive:
  - one flow, as RainMaker's recommended mapping and WebAuthn's registration, on set-up 2.0 as it is;
  - no secret crosses the air or the network: a challenge is worth nothing without the device's key and the person's session;
  - a lost answer is retried safely, and a device that lost its state registers again;
  - SEC-3 is whole: the owner and admins register and revoke a home's devices.
- Negative / accepted trade-offs:
  - **A registration that no connection follows** stays in the home, not connected, until it is removed. Set up into another home meanwhile, the device gets `device_taken`, unless it is reset.
  - **A key in a file passes for one in a TPM.** Someone can register a device made of software into their own home, within the quotas of their home and devices.
  - **A removed device keeps what it holds** until it is reset.
- Follow-up:
  - **ai-cloud's `devices`:** the endpoints; the registry of identifiers and keys; the token endpoint against it; revoking a deleted home's devices from `accounts.home.deleted.v1`, with no registration outliving its home; `connected`, and each device's kind, model and software from its `hello`;
  - **ai-app:** `setup` asks for the challenge, relays the registration, and waits for the first connection; `devices` lists and removes devices;
  - **ai-robot:** nothing on the wire, since it signs the registration already;
  - **a device's name in a home,** which people see: Apple Home asks for one as it adds an accessory, "Assign your accessory to a room and name it". Whether and when the app asks is the owner's choice;
  - **what a device keeps once revoked** (PROV-4): Tuya's unbinding clears the device's pairing and schedule data, and Google Home's removal "resets the device settings and any Automations or Routines". ai-robot chooses for the robot.

## References

Retrieved 2026-11-05:

- ESP RainMaker: [user-node mapping](https://docs.rainmaker.espressif.com/docs/product_overview/concepts/user-node-mapping), [challenge-response mapping](https://docs.rainmaker.espressif.com/docs/dev/firmware/firmware-faq/prov-wi-fi-claiming-fctry-reset/what-is-challenge-response-based-user-node-mapping-why-is-it-recommended), and [debugging it](https://docs.rainmaker.espressif.com/docs/dev/Troubleshooting%20Guide/Cloud_troubleshooting-guide/Debugging-user-node-mapping-issues).
- AWS IoT: [provisioning devices that don't have device certificates](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html), by claim and by trusted user.
- Tuya: [Wi-Fi AP mode](https://developer.tuya.com/en/docs/app-development/PairHotspot?id=Kam86ucnat7ai) (the app SDK's pairing token), [generate pairing token](https://developer.tuya.com/en/docs/cloud/5a3e590722?id=Kb03nje9njyhb) (the cloud API), and [device reset](https://developer.tuya.com/en/docs/iot-device-dev/TuyaOS-iot_abi_device_reset?id=Kc67srci7m1jk).
- Matter: Google's [commissioning primer](https://developers.home.google.com/matter/primer/commissioning); the SDK's [`OperationalCredentialsDelegate.h`](https://github.com/project-chip/connectedhomeip/blob/master/src/controller/OperationalCredentialsDelegate.h) (`kCSRNonceLength`, 32); Silicon Labs, [multi-admin](https://docs.silabs.com/matter/2.7.0/matter-ecosystems/multicontroller-ecosystem).
- W3C: [Web Authentication, Level 3](https://www.w3.org/TR/webauthn-3/), §5.4.7 (attestation conveyance) and §7.1 (registering a new credential); its §13.4.3 on challenges, as [SimpleWebAuthn's `generateChallenge`](https://github.com/MasterKale/SimpleWebAuthn/blob/master/packages/server/src/helpers/generateChallenge.ts) quotes it.
- Microsoft: [TPM attestation](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-tpm-attestation), Azure IoT Hub Device Provisioning Service.
- Amazon: [understanding Frustration-Free Setup](https://developer.amazon.com/docs/frustration-free-setup/understanding-ffs.html).
- Google Home Help: [set up, manage, and control Matter-enabled devices](https://support.google.com/googlehome/answer/13127223).
- Apple Support: [add a smart home accessory to the Home app](https://support.apple.com/en-us/104998).
- Samsung: [SmartThings](https://www.samsung.com/ca/apps/smartthings), devices per location.
