# Set-up — the app ⇄ a device, over Bluetooth LE

How the owner's app sets up a device: its Wi-Fi network, its first settings, and its registration into a home on `ai-cloud`. A robot is the first kind of device ([ADR-0001](../../docs/decisions/0001-repositories.md), decision 5).
- On the robot (ai-robot's `software/`), it is the `setup` module, with its `setup_link` and `network` ports.
- In the app, [ai-app](https://github.com/trungnguyen278/ai-app), it is not built yet.

Version **2.0**:
- It follows ai-robot's [ADR-0015](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0015-set-up.md), accepted, and registers the key of [ADR-0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md) into a home ([ADR-0005](../../docs/decisions/0005-homes.md)).
- It meets the [requirements](../cloud/requirements.md) on set-up and ownership (PROV-1 to PROV-4), and SEC-3, SEC-5 and SEC-16.
- [`schema.json`](schema.json) defines every message, in JSON Schema 2020-12.
- [`examples/`](examples/) holds a whole session, in the clear, with what an app needs to replay its exchange byte for byte: the code, the salt, both sides' random scalars, the intermediate values and the session keys.

**Version notes:**
- **2.0** speaks of devices: `device` in `info`, `device-registration+jwt`, and the labels `ai-platform/setup/2`. The challenge registers the device into a home ([ADR-0005](../../docs/decisions/0005-homes.md)). `configure` gives the device its first languages and time zone ([ADR-0002](../../docs/decisions/0002-languages.md)). Messages are numbered, `seq`, as in the cloud link 3.0 ([ADR-0004](../../docs/decisions/0004-conventions.md)).
- 1.0 was the robot's, as ai-robot's ADR-0015 decided.

> **Implemented:** by the robot ([ai-robot#34](https://github.com/trungnguyen278/ai-robot/pull/34)). The app and the cloud's side, not yet.

## How it goes

```
device                                                  app
shows a code and a QR code;
advertises the set-up service
                                                        the owner scans the QR code,
                                                        or types the code
          <────────────── connects ────────────────────
          <────────────── hello ───────────────────────
          ─────────────── hello: discriminator, salt ──>
          <────────────── share (SPAKE2+) ─────────────
          ─────────────── share, confirm ──────────────>
          <────────────── confirm ─────────────────────
                     from here on, everything is encrypted
          <────────────── info, networks, join ────────
          <────────────── configure: languages, zone ──
          <────────────── register: challenge, server ─    from ai-cloud, for a home
          ─────────────── registration (signed) ───────>   to ai-cloud
          <────────────── finish ──────────────────────
closes set-up, asks the server for a
token: once one comes, it is bound
```

## When set-up is open

The device is open to set-up only on request, and for a limited time (SEC-16).

| | |
|---|---|
| **Opens** | From start, while the device is not bound (PROV-3), and when the owner asks on the device. Each time, the device draws a new discriminator, code and salt. |
| **Closes** | After `window` (15 minutes on the robot), on `finish`, when the owner cancels on the device, or after `attempts` failed attempts (20). |
| **Advertising** | Only while set-up is open and no session runs. One session at a time: a second app gets the error `busy`. |
| **A failed attempt** | A session that sent a `share` but did not confirm. The device then shows a new code, with a new salt. |
| **An idle session** | The device ends a session that has sent nothing for `idle` seconds (120). |

These durations and counts are the device's settings; the values above are the robot's, in `[modules.setup]` of ai-robot's `software/config/base.toml`.

## Finding the device

- **The service.** While set-up is open, the device advertises the set-up service's UUID (below), and its display name if there is room.
- **The discriminator.** 4 hexadecimal digits, drawn each time set-up opens. The device shows it beside the code, the QR code carries it, and the device's `hello` gives it. When several devices are in set-up, the app connects to each one, and keeps the one whose discriminator matches.

## The code

- **8 decimal digits**, drawn uniformly, shown as two groups of four (`1234 5678`). The PAKE's password is the 8 digits in ASCII, without the space.
- **The QR code** holds the set-up string: `setup:2:<discriminator>:<code>`, for example `setup:2:3F7A:12345678`.
  - The `2` is this protocol's major version.
  - The device's setting `link` can wrap it in an address, so that a phone's camera opens the app. `{setup}` in `link` stands for the string, and `"{setup}"`, the robot's, is the string alone.
- The code is a secret for the few minutes it lives. The device shows it only on its screen, never in its logs (SEC-5).

## The Bluetooth service

| | UUID | Properties |
|---|---|---|
| Service | `eaf35dcb-e774-4881-b0c6-4990127a1289` | Primary |
| Request | `eaf35dcc-e774-4881-b0c6-4990127a1289` | Write, with a response: from the app |
| Answer | `eaf35dcd-e774-4881-b0c6-4990127a1289` | Indicate: from the device |

- **No Bluetooth pairing.** The characteristics ask nothing of Bluetooth's own security: the session protects the messages, as Matter's does.
- **First, indications.** The app enables Answer's indications, then writes its first fragment: the device counts it as connected from that write.
- **Fragments.** A message is split into fragments, one per write or indication, each at most the ATT MTU minus 3 bytes. The smallest MTU, 23, leaves 20 bytes.
  - Byte 0 holds flags: `0x80` on a message's first fragment, `0x40` on its last; the other bits are 0.
  - The first fragment then holds the message's length in bytes, on 2 bytes, big-endian, then the message's first bytes.
  - A message has at most **8192** bytes.
- **Order.** The app makes one write at a time, and the device sends one indication at a time, each confirmed before the next: no other flow control is needed.
- **Errors.** Either side ends the session on a fragment that does not fit: a continuation with no first fragment, a first fragment within a message, or more or fewer bytes than announced.

## The session

### Before the exchange, in the clear

Messages are JSON objects, in UTF-8. Each has a `type`, and a `seq`: each side numbers its messages from 1, its `hello` included. An answer also has `reply_to`, the `seq` of the message it answers.

| From | Message | Fields |
|---|---|---|
| App | `hello` | `protocol`: the version it speaks, `"2.0"` |
| Device | `hello` | `protocol`; `discriminator`; `salt`: 16 random bytes, in base64url |
| App | `share` | `share`: SPAKE2+'s shareP |
| Device | `share` | `share`: shareV; `confirm`: confirmV |
| App | `confirm` | `confirm`: confirmP |

- **Versions.** If the app's major version is not the device's, the device answers the error `version` and ends the session. A newer minor version only adds optional fields and messages.
- **Points and tags** are in base64url, without padding: a point in SEC1's uncompressed form, 65 bytes, and a tag of 32 bytes.
- **A wrong code.** If confirmP is wrong, the device answers the error `code` and ends the session. The app sees a wrong confirmV first, and ends it itself. Either way, the device then shows a new code.
- Then the device accepts nothing in the clear any more.

### SPAKE2+

[RFC 9383](https://www.rfc-editor.org/rfc/rfc9383), with:

| | |
|---|---|
| Ciphersuite | P256-SHA256-HKDF-SHA256-HMAC-SHA256, with M and N from RFC 9383, §4 |
| Roles | The app is the Prover; the device is the Verifier |
| w0 and w1 | scrypt ([RFC 7914](https://www.rfc-editor.org/rfc/rfc7914)), with N = 32768, r = 8, p = 1, as RFC 9383 recommends. Its password is `len(pw) ‖ pw ‖ len(idProver) ‖ idProver ‖ len(idVerifier) ‖ idVerifier`, its salt the device's `salt`, and its output 80 bytes. w0 is the first 40 bytes, and w1 the last 40, each as a big-endian integer modulo the order of P-256. |
| Identities | Both empty, as in Matter: the context names the session |
| Context | SHA-256 of `ai-platform/setup/2` ‖ the app's `hello` ‖ the device's `hello`, the hellos as the exact bytes sent |
| `len()` | 8 bytes, little-endian, as in RFC 9383 |

- The transcript, the confirmation keys and K_shared are those of RFC 9383, §3.3 and §3.4.
- Each side checks that the other's share is a point of P-256, other than the point at infinity.
- **Session keys.** HKDF-SHA256 ([RFC 5869](https://www.rfc-editor.org/rfc/rfc5869)) of K_shared, with an empty salt and the info `ai-platform/setup/2 keys`, gives 32 bytes. The first 16 are the app's key, and the last 16 the device's.

### After the exchange, encrypted

- Each message is the JSON message's UTF-8 bytes, encrypted with AES-128-GCM under its sender's key: the ciphertext, then the 16-byte tag. It is split into fragments as above.
- The nonce is 4 zero bytes, then the sender's message counter on 8 bytes, big-endian. The counter starts at 0 for the first encrypted message, and counts each one. There is no associated data.
- The receiver keeps the same count. A message that does not decrypt ends the session.

## Requests and answers

The app sends one request at a time, and waits for its answer.

| Request | Fields | Answer |
|---|---|---|
| `info` | | `info`: `device`, `bound`, `network` |
| `networks` | | `networks`: the networks the device sees, after a scan, the strongest first, at most 50 |
| `join` | `ssid` or `ssid_hex`; `password`, for a protected network; `hidden` and `security`, for a network that does not announce itself | `joined`: `network`, once connected |
| `configure` | `languages`, `time_zone`, either or both | `configured`: the languages and the time zone the device keeps |
| `register` | `challenge`; `server` | `registration`: the device's signed registration |
| `finish` | | `finished`. The device then ends the session and closes set-up. |

- **The device**, in `info`:
  - `id`, the identifier it made itself, a UUID ([ADR-0004](../../docs/decisions/0004-conventions.md));
  - `name`, the name it shows;
  - `kind`, such as `robot`, and `model`, as its maker names it, as in the cloud link's `hello`;
  - `software`, its version;
  - `languages` and `time_zone`, its settings now.
- **A network**, in `networks`:
  - `ssid`, its name; or `ssid_hex`, its name's bytes in hexadecimal, if they are not UTF-8;
  - `security`: `open` (no password, encrypted or not), `wpa2` (WPA2 Personal, or WPA2 and WPA3 mixed), `wpa3` (WPA3 Personal only), or `other` (a security the device does not join, such as WPA Enterprise);
  - `signal`, from 0 to 100;
  - `saved`: whether the device already has the network's password.
- **The network the device is on**, in `info` and `joined`:
  - `state`: `connected`, `connecting` or `disconnected`;
  - when connected, also `ssid` or `ssid_hex`, `address` (its IP address), and `internet` (whether it reaches the Internet, or `null` if not known yet).
- **Joining** adds the network to those the device knows and keeps the others, so that a wrong password does not lose a network that worked. A saved network needs no `password`.
- **Configuring.** The app offers the languages and the time zone of the home it registers the device into, or the phone's ([ADR-0002](../../docs/decisions/0002-languages.md), [ADR-0005](../../docs/decisions/0005-homes.md)):
  - `languages` are BCP 47 tags, in the owner's order. The device keeps, in that order, those it supports; if it supports none, it keeps its own;
  - `time_zone` is an IANA name. One the device does not know gets the error `time_zone`, and nothing changes;
  - the device answers with what it keeps. The owner may change both later, on the device or through the cloud.
- **`register`** is refused with the error `bound` by a device that is already bound: a new owner needs a reset (PROV-4). The device uses `server` from then on, as the server it was registered with.
  - The app gets `challenge` from the cloud, for the home the device is to join, as a member allowed to add devices: the owner or an admin ([ADR-0005](../../docs/decisions/0005-homes.md)).
  - The device never learns the home: the challenge carries it.
- **`finish`** on a device that is not registered leaves it unbound: it then offers set-up again.

### Errors

An error is a message of type `error`, with `reply_to` when it answers a message, a `code`, and a `message` for people.

| `code` | When |
|---|---|
| `version` | No common major version |
| `busy` | Another session runs |
| `code` | The confirmation is wrong: a wrong code, or someone in between |
| `protocol` | A message out of place, or one that breaks the schema |
| `unknown` | A request the device does not know, of a newer minor version |
| `wrong_password` | The network refused the password |
| `not_found` | The network is out of reach |
| `no_address` | Joined, but no IP address came |
| `network` | Joining failed otherwise, or took more than `join_timeout` |
| `time_zone` | `configure` named a time zone the device does not know |
| `bound` | `register` on a device already bound |
| `server` | `server` is not an address the device accepts |
| `identity` | The device could not sign |

## The registration

A JWT ([RFC 7519](https://www.rfc-editor.org/rfc/rfc7519)), signed with ES256 by the device's key, which its TPM holds on the robot ([ADR-0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md)).

| Part | Content |
|---|---|
| Header | `alg`: `ES256`. `typ`: `device-registration+jwt`, so that it cannot pass for another JWT ([RFC 8725](https://www.rfc-editor.org/rfc/rfc8725), §3.11). `jwk`: the device's public key ([RFC 7517](https://www.rfc-editor.org/rfc/rfc7517)): `kty` `EC`, `crv` `P-256`, `x`, `y`. |
| `iss`, `sub` | The device's identifier |
| `aud` | The server's address, as `register` gave it |
| `nonce` | The challenge |
| `jti` | A random identifier |

- **No `iat` or `exp`.** Before it first connects, the device's clock may not be set. The challenge makes the registration fresh: the server issues it for one registration, and lets it expire.
- **What the server checks**, before it binds:
  1. `alg` is `ES256`, `typ` is `device-registration+jwt`, `jwk` is a P-256 key, and the signature verifies with it;
  2. `nonce` is a challenge it issued, unexpired and unused, to the member who sends the registration, which it then forgets;
  3. `aud` is its own address;
  4. `iss` equals `sub`, and no device has this key yet, unless it is already in the challenge's home: a device that lost its state registers again, and so learns its server again.
- **What it binds** into the home it issued the challenge for (SEC-3, SEC-6): the device's identifier, and its key with the key's thumbprint ([RFC 7638](https://www.rfc-editor.org/rfc/rfc7638)), which the device's assertions name as `kid` ([the cloud link](../cloud/README.md#tokens-from-the-server)).
- **The device learns that it is bound** when the token endpoint of `server` first accepts its assertion (`/device/token`, the cloud link 3.0). It keeps that, to work offline. An answer of `invalid_client` makes it unbound again: it then offers set-up (PROV-3).

## Limits

| Field | Limit |
|---|---|
| A message | 8192 bytes |
| `ssid` | 1 to 32 bytes in UTF-8; `ssid_hex`, 2 to 64 hexadecimal digits (IEEE 802.11) |
| `password` | 1 to 128 characters. WPA2 Personal takes 8 to 63 characters, or 64 hexadecimal digits; WPA3 Personal, any length (NetworkManager's `psk`) |
| `languages` | 1 to 16 BCP 47 tags, each up to 35 characters |
| `time_zone` | Up to 64 characters |
| `challenge` | 16 to 128 base64url characters |
| `server` | Up to 2048 characters: `https://`, or `http://` to the device itself only, for development, as in the cloud link |
| `seq`, `reply_to` | 1 to 2<sup>53</sup> − 1 |
| An error's `message` | Up to 256 characters |
