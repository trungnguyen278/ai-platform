# 0013 — Setting a device up: the steps, its name in its home, and a new network

- **Status:** Accepted. The owner approved the flow and its four choices on 2026-11-12 (decisions 1 and 2). The rest is technical, delegated to the assistant (decisions 3 to 9).
- **Date:** 2026-11-12

## Context

- **What is settled:** set-up 2.0 joins a device to a network, gives it its first languages and time zone, and has it sign its registration, which the app relays to the cloud ([ADR-0012](0012-registering-devices.md), the app API 1.4). Only the owner and admins add and remove devices ([ADR-0009](0009-people-in-a-home.md)).
- **What ADR-0012 left open:** whether and when the app asks for a device's name in its home, which people see. Apple Home asks for one as it adds an accessory.
- **How large products add a device** (researched 2026-11-11):

| Product | How the device is found | Its name | A room | A new network later |
|---|---|---|---|---|
| Apple Home | A code to scan, or the phone held near | Asked, with the room: "Assign your accessory to a room and name it" | Asked | — |
| Google Home | A pop-up, or Add, then a QR code or a code | Asked | Asked first | "Forget this network", then set it up again, without a reset |
| Echo Show | Its own screen: language, Wi-Fi, sign-in; a QR code on it continues in the app | — | — | On its screen |
| Tuya | Found when Add opens; a Bluetooth device pops up | Pre-filled, editable, at most 64 characters | Optional | — |
| SmartThings | "Scan nearby", or a QR code | Edited afterwards | Chosen at set-up, for Matter | — |
| iRobot | A product found nearby; a button pressed on the robot | "The name 'Roomba' is preloaded", editable | Not asked | "Reconnect or Change Product Wi-Fi" |
| Sonos | A pop-up | — | — | Settings, "Update Network" |

- **Where they agree:** Add, then a code or the device's own proof, then Wi-Fi, a name, a short wait, and "Connected" or "Done". Nobody registers a device again to change its network.
- **Where they differ:** the name is asked (Apple, Google) or pre-filled (iRobot, Tuya); a room is asked by most; a device found nearby pops up in some apps.
- **Our device has a screen,** as the Echo Show: it shows the code, and opens set-up when someone asks on it. It scans for networks itself, so the app needs no permission to read the phone's network.

## Decision

1. **The flow,** as a person lives it (approved by the owner):
   1. "Add device" in a home, for the owner and admins only;
   2. a short explanation, then the Bluetooth and camera permissions, asked only now;
   3. the QR code on the device's screen, scanned, or its 8 digits, typed;
   4. a Wi-Fi network chosen from the device's own scan, and its password; skipped when the device is already on a network that reaches the Internet;
   5. the home's languages and time zone, given to the device;
   6. the name: pre-filled, editable, one tap to accept;
   7. "Ready" once the device has connected to the cloud; then the device's page.
2. **Four choices** (approved by the owner):
   - **the name is asked at the end, pre-filled** with the name the device gives itself, which closes ADR-0012's open question;
   - **no room:** a device belongs to a home, and nothing finer;
   - **no "found nearby" pop-up:** the app looks for devices only after "Add device";
   - **a new network later never registers the device again.**
3. **The name reaches the cloud with the registration,** so that a set-up interrupted after it still leaves a named device:
   - the app sends `name`, the device's own from set-up's `info`, beside the registration it relays. The cloud keeps it with the device;
   - at step 6, a person who keeps the name sends nothing. One who changes it renames the device, with `If-Match`, as other resources change ([ADR-0004](0004-conventions.md));
   - **renaming is for the owner and admins,** as adding and removing are;
   - **a device that registers again** into its home keeps the name it has there;
   - **the rules are a home's name's:** 1 to 100 characters, without control characters. Set-up lets a device's own name hold control characters, so the app offers its own name for the device's kind in place of such a name;
   - **two devices of a home may share a name,** as two homes or two people may. Two devices of one model give the same name: refusing the second would break the one tap that accepts it.
4. **A device already bound** opens set-up only when someone asks on it. It refuses `register`, with `bound`, and serves the rest. The app sees `bound` in `info`: it asks for no challenge, sends neither `register` nor `configure`, and offers only the network.
   - **Who is at the other end:** anyone who reads the code on the screen. The session lets them do only what being at the device lets them do: change its network and its settings, as its own screen does. Nothing in it changes the device's home, key or server, and a hostile network cannot pass for the server (SEC-1).
   - **It is set-up 2.0 as written,** said plainly: 2.0 refuses only `register` on a bound device, and no message changes. So set-up keeps its version.
5. **Step 4 is skipped** when `info` shows the device connected to a network that reaches the Internet (`internet` true). While `internet` is `null`, the app asks for `info` again.
6. **A typed code** finds the device alone when only one device is in set-up. With several, the app also asks for the 4 characters shown beside the code, the discriminator, as Matter's 11-digit code carries part of it. It never tries a code on a device it has not matched, since each failed attempt changes that device's code.
7. **Each failure the flow names has an answer the app tells apart:**

   | What the person meets | What the app sees |
   |---|---|
   | A wrong Wi-Fi password | Set-up's `wrong_password` |
   | A device in another home | `bound` in `info`, for a device in none of the person's homes; or the cloud's `device_taken`. Its home removes it, or it is reset. |
   | An expired code | No device in set-up shows the code's discriminator; or set-up's `code`, once the device has drawn another code |
   | A busy device | Set-up's `busy` |
   | An interruption | The session ends. The app starts again with a new session, and `info` and the home's devices tell it where things stand (decision 8). |

8. **After an interruption,** the app first looks for the device in the home, by the identifier that `info` gave, if it kept it. Otherwise the person opens set-up on the device again, if it has closed, and the app starts from step 3. What it may find:
   - **joined, not registered:** the device is on its network, so step 4 is skipped, and the registration is new;
   - **registered, without `finish`:** the device may have reached the cloud since, and is then bound, connected and in the home: the app goes on from step 6. Otherwise a new session finds it unbound, and its registration again gets `200`, with the device that the cloud holds;
   - **registered, its name not confirmed:** the device has its own name in the home, which its page lets the owner and admins change. Nothing on the wire records a confirmation, as for iRobot's and Tuya's pre-filled names.
9. **Versions** ([ADR-0003](0003-compatibility.md)): the app API 1.5, a minor version: an optional field in the registration, the device's `name` and `etag`, and renaming. Set-up stays 2.0, its README saying plainly what it implies. The cloud link does not change.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A room, as Apple, Google and SmartThings ask | The owner chose the home and nothing finer. |
| A pop-up for a device found nearby, as Google, Tuya, iRobot and Sonos show | The owner chose no pop-up. It would also need Bluetooth before "Add device", where Apple's guidelines ask to wait "until people actually use an app feature that requires access". |
| Registering again for a new network, as Google Home's "Forget this network" | The owner chose not to. The device's registration does not depend on its network. |
| The name asked before the registration, and sent with it | An interruption at the name step would leave no registration at all. |
| The registration without a name, and the name sent after it | An interruption in between would leave a device without a name, which a list could show only by its identifier. |
| The name in the device's signed registration, a minor version of set-up | The name is the home's, not the device's: it changes later through the cloud alone. A device of set-up 2.0 would not send it anyway. |
| A name the cloud makes from the device's first `hello` | It carries the device's kind and model only, and Apple's guidelines say "Never suggest company names or model numbers". |
| Unique names in a home, as HomeKit refuses to give "the name of one object to another object in the home" | HomeKit's guidelines shape names for Siri, and no device here is called by its name. Two devices of one model would need a name made up for the second, and homes and people may already share names. |
| A record that the person confirmed the name | No product keeps one: a pre-filled name is a name. |
| A minor version of set-up for a bound device's session | Nothing a side sends or answers changes. |
| A bound device that refuses `configure` too | A major version of set-up, for nothing: whoever reads the code stands at the device, whose screen changes the same settings. |
| Trying a typed code on every device in set-up | Each failure costs that device an attempt, and changes the code that its owner may be reading. |

## Consequences

- Positive:
  - the flow follows the products people know, and no step depends on a step that an interruption can lose;
  - a set-up that stops anywhere is resumed by starting again: the protocols' answers say where it stood;
  - set-up 2.0 serves the flow as it is, so the robot, which implements it, changes nothing on the wire.
- Negative / accepted trade-offs:
  - **two devices of a home may share a name,** and the person tells them apart on their pages. Refusing that later would be a major version;
  - **a device registered by an app of 1.4,** which sends no name, has none until someone gives it one: the app shows its own name for the device's kind meanwhile. No such app has shipped;
  - **anyone at a bound device can change its network,** once someone opens set-up on it, as on an Echo Show.
- Follow-up:
  - **ai-cloud:** the device's name and `etag`, from the registration and on renaming;
  - **ai-app:** the flow above, its messages, and renaming from the device's page;
  - **ai-robot:** nothing on the wire. The robot already serves a bound device's session as decision 4 says.

## References

Read 2026-11-11, unless dated otherwise:

- Apple: [add an accessory](https://support.apple.com/en-us/104998); [HomeKit guidelines](https://developer.apple.com/design/human-interface-guidelines/homekit) (dated 2 May 2023); [privacy guidelines](https://developer.apple.com/design/human-interface-guidelines/privacy); [`HMError.Code.objectWithSimilarNameExistsInHome`](https://developer.apple.com/documentation/homekit/hmerror/code/objectwithsimilarnameexistsinhome), read 2026-11-12.
- Google: [Matter devices in Google Home](https://support.google.com/googlehome/answer/13127223), [setting up Nest devices](https://support.google.com/googlehome/answer/7029485), [a new Wi-Fi network](https://support.google.com/googlehome/answer/10165378), [onboarding guidance](https://developers.home.google.com/apis/onboarding-guidance).
- Amazon: [Echo Show set-up](https://digprjsurvey.amazon.com/csad/help/node/T57xOIjRG5FLoczPDn); [commissioning Matter devices](https://developer.amazon.com/en-IN/docs/alexa/smarthome/best-practices-commission-matter.html).
- Tuya: [the Smart Life user manual](https://developer.tuya.com/en/docs/iot/user-manual-for-tuya-smart-v3177?id=K9obrofrfk4sk). Samsung: [SmartThings](https://www.samsung.com/us/support/answer/ANS10002639/). iRobot: [set-up](https://homesupport.irobot.com/articles/en_US/Knowledge/17734). Sonos: [a new network](https://support.sonos.com/en-us/article/connect-sonos-to-a-new-router-or-wi-fi-network).
- Matter: the manual pairing code, 11 digits that carry 4 bits of the discriminator, in [`ManualSetupPayloadGenerator.cpp`](https://github.com/project-chip/connectedhomeip/blob/master/src/setup_payload/ManualSetupPayloadGenerator.cpp), read 2026-11-12.
