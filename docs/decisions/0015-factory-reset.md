# 0015 — A device's factory reset: it leaves its home, then erases itself

- **Status:** Accepted. The owner approved its direction on 2026-11-14; the protocol's details are a technical decision, delegated to the assistant (2026-11-18).
- **Date:** 2026-11-18

## Context

- **What is settled:**
  - A device goes to a new owner only through a reset that erases the previous owner's data and binding (PROV-4), and a factory reset erases the device's credentials, its settings and what it stored (PRIV-6).
  - The robot's factory reset wipes its data partition and clears its TPM (ai-robot [ADR-0014](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0014-updates.md), decision 5), which holds its key and its identifier (ai-robot [ADR-0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md)). A reset robot is a new device to the cloud.
  - Removing a device in the app revokes its registration, and does not erase it ([ADR-0012](0012-registering-devices.md), decision 6). Until the cloud link 3.2, only the cloud ended a registration: `bye` `revoked` on the control channel, and `invalid_client` at the token endpoint.
  - ETSI EN 303 645 V2.1.1 (2020-06), provision 5.11-1: "The user shall be provided with functionality such that user data can be erased from the device in a simple manner." User data includes "cryptographic material such as user passwords or keys" (its Note 1).
- **The owner's direction (2026-11-14):** the reset starts on the device's screen. Online, the device leaves its home before it erases itself, so that the app no longer lists it. Offline, it erases itself anyway, and its screen first says to remove it in the app. Afterwards it starts as a new device, with a new identity.
- **What others do** (read 2026-11-13, but Tuya, ESP RainMaker and Zigbee, read 2026-11-16):

| Product | Where the reset starts | The cloud and the app |
|---|---|---|
| Amazon Echo Hub | On the device: Reset to Factory Defaults | "To clear all device settings, including deregistering the Echo Hub from your Amazon account, select Reset to Factory Defaults." |
| Google Nest Hub | On the device: both volume buttons, held for about 10 seconds | It "disconnects the device from all members in the home". "You can't use your voice or the Google Home app to perform a factory reset." |
| Tuya's devices (TuyaOS, page updated 2024-06-25) | On the device | A factory reset clears the device's data, then does this: "Notify the cloud to unbind the device and clear the device's historical data." An offline device can be reset too, and "After a reset, the device status on the app shows `Offline`." |
| ESP RainMaker | On the device | With "factory reset reporting", off by default, the device tells the cloud on its own MQTT link, which "allows the cloud to clean up old user-node mappings when a device is factory reset". |
| Zigbee (ESP Zigbee SDK) | On the device: a reset "via local action" (Base Device Behavior, 9.5) | "The device will leave the current network and clear all Zigbee persistent data." |
| Matter | Left to each platform: `InitiateFactoryReset` has an empty body in the SDK | A reset device cannot tell its controllers, which learn of it only when they fail to reach it. |

- **Where they agree:** the reset starts on the device, and a device that reaches its cloud tells it over its own link, as it erases itself (Echo Hub, Tuya, RainMaker, Zigbee). Only Tuya documents the offline case: the device resets anyway, and the app shows it offline.

## Decision

1. **The reset starts on the device,** as on the Echo Hub, the Nest Hub, and Tuya's and Zigbee's devices. Each device decides how it is confirmed, and its fallback for a screen that does not work (ai-robot, for the robot). The app does not start it: removing a device in the app still only revokes it (ADR-0012).
2. **Online, the device leaves its home first,** with the cloud link 3.2's `leave`, on its own control channel, which its key opened.
   - The cloud does what the app's removal does: it revokes the registration, refuses the device's tokens and assertions, forgets its key, and deletes what it keeps of the device. What belongs to the home and its people stays ([ADR-0005](0005-homes.md), decision 4). The app no longer lists the device.
   - It answers with `bye` `left` once the device is out of its home, and only then, and closes the connection.
   - **A lost answer costs nothing.** The device's next request for a token gets `invalid_client`: the cloud holds it no more, which is what it asked for. OAuth's revocation reasons the same way: it answers a token that is already invalid as one it has just revoked, since "the client cannot handle such an error in a reasonable way" ([RFC 7009](https://www.rfc-editor.org/rfc/rfc7009), §2.2). `bye` `revoked`, from a removal in the app at the same moment, means the same.
   - The device sends it only in a session of 3.2 or later. A 3.1 cloud ignores a message type it does not know, and would never answer.
   - **The device keeps that it is resetting** before it sends `leave`, so that a reset cut short, by a power cut for one, goes on at the next start. Without it, a device that the cloud removed would restart, meet `invalid_client`, and offer set-up with the previous owner's data still on it.
3. **Offline, the device erases itself anyway** (ETSI EN 303 645, 5.11-1). It does so when it has no session of 3.2, or when no answer comes within `leave_timeout`, 15 s to start with. Its screen first says to remove it in the app, if the app still lists it. The home keeps it, not connected, until someone removes it, as Tuya's app shows a device reset offline.
4. **Afterwards, it is a new device,** with a new key and a new identifier. Set up again, it registers as a new device, into any home. A record of the old one that stayed in its home takes nothing from it.
5. **Versions** ([ADR-0003](0003-compatibility.md)):
   - the cloud link 3.2, a minor version. A 3.1 cloud never gets `leave`, since a device sends it in a session of 3.2 only, and only a device that sent it gets `bye` `left`;
   - the app API and set-up do not change. The app API's text says that a device may leave by itself.

## Alternatives considered

| Alternative | Why not |
|---|---|
| An HTTPS endpoint, where the device deletes its own registration with an assertion, as OAuth's dynamic client registration lets a client deprovision itself ([RFC 7592](https://www.rfc-editor.org/rfc/rfc7592), §2.3, Experimental) | The control channel is already open and tied to the device ([ADR-0006](0006-two-channels.md), SEC-6), and its version says whether the cloud knows `leave`. An endpoint would need a version and refusals of its own, for one request in a device's life. |
| `bye` with a reason of the device's, such as `leaving` | A `bye` gets no answer. The device could not tell whether the app still lists it, which its screen must say. |
| Wait for the cloud before erasing | A device that cannot reach its cloud could never be erased, against ETSI EN 303 645, 5.11-1. |
| Tell the cloud after the reset, at the next start, as RainMaker does | The reset clears the TPM, so the new device cannot speak for the old one. Keeping the old identity to do so would keep the previous owner's binding past the erase (PRIV-6). |
| The cloud keeps a record of the devices that left, to answer a `leave` sent again | The token endpoint's `invalid_client` answers it already, and nothing need be kept. |
| The app's removal also erases the device, as Tuya's "Disconnect and wipe data" does | Not this direction: a removal only revokes (ADR-0012), and what a removed device keeps is the owner's choice (PROV-4). |

## Consequences

- Positive:
  - online, one reset on the device ends both its data and its place in the home, and the app keeps no stale device;
  - the erase never waits for the network;
  - no new endpoint, and no record of the devices that left.
- Negative / accepted trade-offs:
  - **A device reset offline stays in its home's list,** not connected, until someone removes it in the app. Its screen says so before it erases itself.
  - **A leave that times out after the cloud acted** makes the screen ask for a removal that is already done. The app then shows nothing to remove.
  - **Whoever holds the device's key can make it leave,** as they could act as the device. Tokens are short-lived and never logged (SEC-5), and the owner sets the device up again.
- Follow-up:
  - **ai-cloud:** `leave` on the control channel, through the same path as the app's removal, then `bye` `left`;
  - **ai-robot:** the reset: its confirmation on the screen, `leave`, the erase and the TPM, what the screen says for each outcome, and a reset that goes on after a power cut;
  - **ai-app:** a device that left disappears from its home. The removal's dialog can name the reset on the device once ai-robot has it.

## References

- ETSI: [EN 303 645 V2.1.1](https://www.etsi.org/deliver/etsi_en/303600_303699/303645/02.01.01_60/en_303645v020101p.pdf) (2020-06), provision 5.11-1, read 2026-11-12.
- Read 2026-11-13:
  - Amazon: [Echo Hub, reset to factory defaults](https://digprjsurvey.amazon.com/csad/help/node/TC9bcGEOX18wsF3dvC);
  - Google: [factory reset a Google Nest speaker or display](https://support.google.com/googlenest/answer/7073477);
  - Matter: [`GenericConfigurationManagerImpl.ipp`](https://github.com/project-chip/connectedhomeip/blob/master/src/include/platform/internal/GenericConfigurationManagerImpl.ipp) in connectedhomeip, `InitiateFactoryReset`.
- Read 2026-11-16:
  - Tuya: [device reset](https://developer.tuya.com/en/docs/iot-device-dev/TuyaOS-iot_abi_device_reset?id=Kc67srci7m1jk), TuyaOS;
  - ESP RainMaker: `ESP_RMAKER_FACTORY_RESET_REPORTING` in [`Kconfig.projbuild`](https://github.com/espressif/esp-rainmaker/blob/master/components/esp_rainmaker/Kconfig.projbuild), and `esp_rmaker_reset_user_node_mapping` in [`esp_rmaker_user_mapping.c`](https://github.com/espressif/esp-rainmaker/blob/master/components/esp_rainmaker/src/core/esp_rmaker_user_mapping.c);
  - ESP Zigbee SDK: [Base Device Behavior](https://docs.espressif.com/projects/esp-zigbee-sdk/en/latest/esp32/api-reference/esp_zigbee_core/bdb.html), `ezb_bdb_reset_via_local_action`;
  - IETF: [RFC 7009](https://www.rfc-editor.org/rfc/rfc7009), §2.2 (revoking a token that is already invalid), and [RFC 7592](https://www.rfc-editor.org/rfc/rfc7592), §2.3 (a client that deletes its own registration).
