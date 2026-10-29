# Cloud link — device ⇄ ai-cloud

The link between a device of the project and `ai-cloud`. A robot is the first kind of device. Each device declares what it can do, and the cloud drives only that ([ADR-0001](../../docs/decisions/0001-repositories.md), decision 5).

The device's core AI runs in the cloud. The device listens, plays, shows and acts, and keeps everything safe. This link carries:
- the session: what the device is and can do, the cloud's calls, and the device's events;
- conversations: opened on the session, with their audio in a LiveKit room of their own.

Version **3.0**:
- It builds on:
  - [ADR-0006](../../docs/decisions/0006-two-channels.md): a control channel always on, and media only to talk;
  - [ADR-0002](../../docs/decisions/0002-languages.md), [ADR-0003](../../docs/decisions/0003-compatibility.md) and [ADR-0004](../../docs/decisions/0004-conventions.md): languages, compatibility and conventions;
  - ai-robot's [ADR-0008](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0008-cloud-link-messages.md) (typed JSON messages, and MCP for capabilities), [ADR-0009](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0009-cloud-link-webrtc.md) (WebRTC through LiveKit, now for conversations only), [ADR-0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md) (the device's identity) and [ADR-0012](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0012-end-of-speech.md) (the cloud ends the user's speech).
- It meets the [requirements](requirements.md), whose identifiers (SES-2, PRIV-1…) it cites.
- [`schema.json`](schema.json) defines every message, in JSON Schema 2020-12, and [`examples/`](examples/) holds whole exchanges.

**Version notes:**
- **3.0** splits the link in two: the session on a WebSocket to `ai-cloud`, always open, and a LiveKit room for each conversation, with its audio, its turns and its answers. A conversation lasts many turns, which the cloud takes. The link speaks of devices: `/device/token`, and the device's kind and model in its `hello`. Identifiers are UUIDs, instants RFC 3339 and durations seconds. Messages are numbered, so that a session survives a short loss of its connection. A version the cloud no longer speaks gets "update required".
- 2.2 had the cloud end the user's speech; 2.1 added the token endpoint; 2.0 carried everything in a LiveKit room; 1.0 carried everything over one WebSocket ([ai-robot ADR-0007](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0007-cloud-link-transport.md), superseded).
- No cloud ever spoke 1.x or 2.x, and no device left the workshop with them. The cloud speaks 3.0 only, and ADR-0003's periods start with it.

> **Implemented:** the control channel, by the robot ([ai-robot#36](https://github.com/trungnguyen278/ai-robot/pull/36)). Conversations, and the cloud's side, not yet.

## Two channels

| Channel | What it carries | When it is open |
|---|---|---|
| **Control:** a WebSocket to `ai-cloud` | What concerns the device: its capabilities and every call to them, its events, and conversations opened and ended | Always, while the device runs |
| **Media:** a LiveKit room for each conversation | What concerns the conversation, between the device and the cloud's agent: the audio both ways, the turns and the answers | During the conversation |

Each message travels where its owner is ([ADR-0006](../../docs/decisions/0006-two-channels.md)). A conversation's turns and answers are the agent's, and go with its audio. A call to the device goes on the control channel, whoever in the cloud makes it.

```mermaid
sequenceDiagram
    participant D as Device
    participant C as ai-cloud
    participant R as LiveKit room, with the agent
    D->>C: POST /device/token, with a signed assertion
    C->>D: an access token
    D->>C: WebSocket /device/v3/link, then hello
    C->>D: hello
    Note over D: a wake word: the device listens, and keeps what it hears
    D->>C: conversation.request
    C->>D: conversation.start: the room, and a token for it
    D->>R: joins, and publishes its microphone
    Note over R: the agent joins
    D->>R: what it heard so far, then its microphone live
    R->>D: turn.speech_end, response.start, response.text, and the voice
    D->>C: conversation.end, after a silence
    D->>R: leaves
```

## Connecting

### The cloud's address

Set-up registers the device with a cloud, whose address the device then keeps: `server`, in [the registration](../setup/README.md#the-registration). It is `https://`, or `http://` to the device itself, for development (SEC-1). The device drops a trailing slash from it, and appends:
- `/device/token`, for the token endpoint;
- `/device/v3/link`, for the control channel, with `wss://` in place of `https://` (`ws://` for `http://`).

### Tokens from the server

Before each connection, the device asks the token endpoint for an access token. It proves who it is with an assertion signed by its key ([ai-robot ADR-0010](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0010-device-identity.md)): OAuth 2.0 client authentication with a JWT ([RFC 7523](https://www.rfc-editor.org/rfc/rfc7523), §2.2).

```http
POST /device/token HTTP/1.1
Host: cloud.example
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=eyJhbGciOiJFUzI1NiIsImtpZCI6...
```

The assertion is a JWT signed with ES256, ECDSA on P-256 with SHA-256 ([RFC 7518](https://www.rfc-editor.org/rfc/rfc7518), §3.4):

| Part | Content |
|---|---|
| Header | `alg`: `ES256`; `typ`: `JWT`; `kid`: the key's JWK thumbprint ([RFC 7638](https://www.rfc-editor.org/rfc/rfc7638)), so that the server finds the key, and can know two of a device's keys while it changes them |
| `iss`, `sub` | The device's identifier: a UUID it made itself ([ADR-0004](../../docs/decisions/0004-conventions.md)) |
| `aud` | The token endpoint's URL |
| `iat`, `exp` | When it was made, and when it expires: at most 5 minutes later |
| `jti` | A random identifier. The server refuses one it has already seen while it is valid, so that a replayed assertion is worthless (SEC-12). |

The server answers with JSON ([`schema.json`](schema.json), `$defs/token_response`), as OAuth 2.0 does:

```json
{"access_token": "eyJhbGciOiJFUzI1NiIs...", "token_type": "Bearer", "expires_in": 600}
```

- **Refusals** follow OAuth 2.0 ([RFC 6749](https://www.rfc-editor.org/rfc/rfc6749), §5.2): status 400 or 401, and JSON with `error` and `error_description`.
  - `invalid_client` means a key the server does not know, or one that was revoked: the device is not set up. It then offers set-up ([the set-up protocol](../setup/README.md), PROV-3).
  - After any other refusal, the device tries again after the backoff ([Staying connected](#staying-connected)).
- **No redirects.** The endpoint answers itself. The device does not follow a redirect, which would carry its assertion to an address it never chose: it takes one as a refusal.
- **The clock.** The device keeps its clock right (NTP); the server refuses assertions from a clock far off.

### The control channel

The device opens a WebSocket ([RFC 6455](https://www.rfc-editor.org/rfc/rfc6455)) with its access token as a bearer token ([RFC 6750](https://www.rfc-editor.org/rfc/rfc6750), §2.1):

```http
GET /device/v3/link HTTP/1.1
Host: cloud.example
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Authorization: Bearer eyJhbGciOiJFUzI1NiIs...
```

- **The path carries the major version** ([ADR-0004](../../docs/decisions/0004-conventions.md), decision 5). The cloud can then run two majors side by side, and answer one it has retired ([Update required](#update-required)).
- **One message per text frame:** a JSON object, in UTF-8.
- **The token opens the connection,** and need not stay valid while the connection lasts. When the device's registration is revoked, the cloud ends its session with `bye` `revoked` (SEC-3).
- **Refusals.** The cloud may answer the handshake with an error instead. Its body is Problem Details ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)), for people and logs; the device acts on the status:

  | Status | Meaning | The device |
  |---|---|---|
  | 401 | The access token is not valid | Gets a new token, and connects again after the backoff |
  | 410 | The cloud no longer speaks this major version | Updates ([Update required](#update-required)) |
  | Any other | Too many connections, the cloud is busy or down | Connects again after the backoff, and no sooner than `Retry-After` if the answer has one |

- **One connection per device.** A new connection replaces the device's older one, which the cloud ends with `bye` `replaced`.

### Staying connected

- **Pings** (SES-3). The cloud's `hello` gives `ping_interval`, in seconds. The device sends a `ping` that often, the first after a random fraction of the interval, so that devices that connect together spread their pings. The cloud answers each with a `pong`. Both say the last message number their sender has received ([Resuming a session](#resuming-a-session)):
  ```json
  {"type": "ping", "received": 41}
  {"type": "pong", "received": 37}
  ```
  - If no `pong` has come by the time the next `ping` is due, the device closes the connection, and connects again to resume its session.
  - The cloud closes a connection from which nothing has come for two intervals.
  - Pings also keep proxies from closing a quiet connection: Cloudflare, for one, closes a WebSocket on which nothing moves for a while ([Cloudflare](https://developers.cloudflare.com/network/websockets/)).
  - They are messages of this protocol, not WebSocket's Ping frames. A proxy that ends the WebSocket answers those itself, and libraries hide them. Links that stay open for hours ping on their own too: Alexa's device SDK sends `GET /ping`, and Discord's gateway and LiveKit's signalling send heartbeats at the pace their server sets ([ADR-0006](../../docs/decisions/0006-two-channels.md)).
- **Going away.** Before it closes a connection on purpose, such as to restart, the cloud sends `reconnect`, much as Gemini Live sends `GoAway` ([Google](https://ai.google.dev/gemini-api/docs/live-session)). It sends nothing more on that connection. The device connects again at once, after a random wait of up to `reconnect_first` so that devices spread, and resumes its session.
- **Reconnecting** (SES-4). After a lost connection or a refusal, the device connects again after a random wait, from 0 to `min(reconnect_max, reconnect_first × 2ⁿ)`, where n counts the failed attempts in a row: exponential backoff with full jitter. A completed `hello` exchange resets n.
- **Losses are ordinary.** Proxies restart: Cloudflare ends WebSockets when it releases new code to its network ([Cloudflare](https://developers.cloudflare.com/network/websockets/)). The session is built to survive them.

### Resuming a session

A session outlives a short loss of its connection (SES-5), as a session of Discord's gateway does ([Discord](https://docs.discord.com/developers/events/gateway)).

- **Numbers.** Each side numbers the messages it sends in a session, `seq`, from 1. `hello`, `ping`, `pong`, `reconnect` and `bye` have no number: they open, keep and end the numbering. A number is a place in one session, not an identifier: outside the session it means nothing, and the session itself has a UUID ([ADR-0004](../../docs/decisions/0004-conventions.md), decision 1).
- **Keeping what was sent.** Each side keeps the messages it sent until the other has received them, as the other's `received` says, and at most `replay` of them.
- **Resuming.** A device whose connection was lost without a `bye` names its session in its next `hello`, with the last number it received: `"resume": {"session": "01a18085-…", "received": 41}`.
  - If the cloud still holds the session, for `resume_window` seconds after the loss, and kept everything the device has not received, it answers with the same session, `"resumed": true`, and the last number it received from the device.
  - Each side then sends again, in order and with their numbers, what it sent after the other's `received`, and goes on from there.
  - A device that no longer holds what the cloud's `received` asks for ends the session with `bye` `resume_failed`, and connects again for a new one.
- **A new session.** Otherwise the cloud answers with a new session and `"resumed": false`. Numbers start again from 1, and what was in flight is lost: a call gets no result, and its caller's time limit applies. The cloud discovers the device's capabilities again.
- **Duplicates** (SES-6). A message whose number is not above the last one handled from that side is a duplicate, and is ignored. A message that skips a number ends the session with `bye` `out_of_sequence`.
- **A `bye` ends a session for good:** nothing resumes it.

## Messages

- **Shape.** A JSON object with:
  - `type`, in lower case, with dots (`turn.speech_end`);
  - `seq`, its number, in every message but `hello`, `ping`, `pong`, `reconnect` and `bye`;
  - `reply_to`, in a message that answers another: that message's `seq`.
- **Sizes.** A message holds up to 1 MiB. A side stops reading a larger one, answers `invalid_message`, and ignores it.
- **Order.** Messages arrive in the order sent, and each side handles them in that order.
- **Values** ([ADR-0004](../../docs/decisions/0004-conventions.md)): identifiers are UUIDs, made as UUIDv7 ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562), §5.7); instants are [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339), in UTC; durations are seconds; numbers are finite, since JSON has no NaN; languages are BCP 47 tags ([ADR-0002](../../docs/decisions/0002-languages.md)).
- **Validation.** Each side validates what it receives against [`schema.json`](schema.json) (SEC-14). A message that fails gets an `error`, and is otherwise ignored: the session goes on (REL-4).
- **Unknown content.** A side ignores message types and fields it does not know, so that a newer minor version can add them (REL-5). A `reason` it does not know, it takes as `error`.
- **Rates** (SEC-15). Each side limits what it takes from the other. The device handles up to `rate` messages a second, in bursts of up to `burst`; up to `backlog` more wait their turn, so a busy answer loses nothing. Past the backlog, it drops what comes, says so with `rate_limited`, and logs it.

| Type | From | Purpose |
|---|---|---|
| `hello` | both | Opens or resumes the session |
| `ping`, `pong` | device, cloud | Keep the connection alive, and say what was received |
| `reconnect` | cloud | The cloud is about to close this connection: resume on a new one |
| `bye` | both | Ends the session |
| `device.changed` | device | The owner changed the device's languages, time zone or allowed classes |
| `mcp` | both | One MCP message: the cloud calls the device's capabilities |
| `event` | device | Something happened that the cloud subscribed to |
| `conversation.request` | device | Someone spoke to the device, which asks for a conversation |
| `conversation.start` | cloud | A conversation starts, and where its audio goes |
| `conversation.end` | both | The conversation is over |
| `error` | both | A message could not be handled |

The conversation's own messages travel in its room ([Turns and responses](#turns-and-responses)).

## The session

### `hello`

The device speaks first, as soon as the connection is open, and the cloud sends nothing before it:

```json
{"type": "hello", "protocol": "3.0",
 "device": {"kind": "robot", "model": "concept-v0", "software": "0.4.0"},
 "time": "2026-10-28T03:20:00.250Z", "time_zone": "Asia/Ho_Chi_Minh",
 "languages": ["vi", "en"], "allowed_classes": ["informational", "physical"],
 "conversations": true, "media": ["livekit"],
 "events": [{"name": "screen.touched", "description": "Someone touched the screen",
             "schema": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}}}}]}
```

| Field | Meaning |
|---|---|
| `protocol` | The version the device speaks, as `major.minor`. The major is the path's. |
| `device` | What the device is: its `kind`, such as `robot`; its `model`, as its maker names it; its `software` version |
| `time` | The device's clock |
| `time_zone` | The device's time zone, an IANA name (IO-1) |
| `languages` | The device's languages, in its owner's order: it shows the first ([ADR-0002](../../docs/decisions/0002-languages.md)) |
| `allowed_classes` | The safety classes its owner allows (SEC-8, SEC-9) |
| `conversations` | Whether it holds conversations: it streams what it hears, and plays the cloud's voice |
| `media` | The media it can use for conversations: `livekit` |
| `events` | The events it can send, each with a JSON Schema of its `data` (EXT-6). Events declared after the `hello` take effect at the next session. |
| `resume` | Only to resume: the session, and the last number received from the cloud |
| `conversation` | Only while the device is in a conversation: which one |

The cloud answers:

```json
{"type": "hello", "protocol": "3.0", "session": "01a18085-942c-78a0-9282-31c8cede2442",
 "resumed": false, "time": "2026-10-28T03:20:00.310Z", "ping_interval": 20,
 "conversations": true, "events": ["screen.touched"]}
```

| Field | Meaning |
|---|---|
| `protocol` | The session's version: the major, and the lower of the two minors |
| `session` | The session's identifier, so that logs on both sides can be matched (OPS-3) |
| `resumed` | Whether the session goes on from before |
| `received` | Only when resumed: the last number received from the device |
| `time` | The cloud's clock (IO-14) |
| `ping_interval` | How often the device pings, in seconds |
| `conversations` | Whether the cloud holds conversations with the device. The session has conversations only if both sides say so. |
| `events` | The events the cloud subscribes to. The device sends only those, and only declared ones. |

- **No answer.** Each side waits `hello_timeout` for the other's `hello`. Past it, it sends `bye` `no_hello` and closes the connection.
- **Another major version** in a `hello` than in the path is refused with `bye` `unsupported_protocol`.
- **A conversation the cloud no longer knows**, named by a device's `hello`, is ended by the cloud with `conversation.end` `lost`.

### `device.changed`

When the owner changes the device's languages, time zone or allowed classes, the device says what changed:

```json
{"type": "device.changed", "seq": 8, "languages": ["en", "vi"]}
```

A change to the allowed classes also changes the capabilities' catalogue, which MCP announces ([Capabilities](#capabilities-mcp)).

### `bye`

Before ending a session on purpose, a side sends `bye` (SES-7), then closes the connection:

```json
{"type": "bye", "reason": "stopping"}
```

| Reason | From | Then |
|---|---|---|
| `stopping`, `restarting`, `updating` | device | The device stops, restarts or installs an update |
| `replaced` | cloud | A newer connection of the device took over. The device keeps to that one. |
| `revoked` | cloud | The device is no longer registered. It forgets its session and offers set-up (PROV-3). |
| `update_required` | cloud | The device needs an update ([Update required](#update-required)) |
| `no_hello` | both | The other side's `hello` did not come in time |
| `unsupported_protocol` | cloud | The `hello` named another major version than the path |
| `resume_failed` | device | The device cannot send again what the cloud asked for |
| `out_of_sequence` | both | A message skipped a number |

After any other reason, the device connects again after the backoff, for a new session. `bye` may add a `message`, for logs.

## Capabilities: MCP

The cloud drives the device through the device's capabilities (EXT-1…10). Every call comes on the control channel, whoever in the cloud makes it: the agent of a conversation, a reminder or the app. These are MCP tools, revision 2026-07-28, with the device as the MCP server and the cloud as the client. An `mcp` message carries exactly one MCP JSON-RPC message in `payload`:

```json
{"type": "mcp", "seq": 2,
 "payload": {"jsonrpc": "2.0", "id": 1, "method": "tools/list",
             "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                                  "io.modelcontextprotocol/clientCapabilities": {}}}}}
```

The device implements:

| Method | What it does |
|---|---|
| `server/discover` | Returns the supported MCP versions (`2026-07-28`), the server capabilities (`tools.listChanged`), and `serverInfo` in `_meta` |
| `tools/list` | Returns the catalogue in one page, sorted by name |
| `tools/call` | Runs a capability |
| `subscriptions/listen` | With `toolsListChanged`, acknowledges, then sends `notifications/tools/list_changed` whenever the catalogue changes (EXT-4) |
| `notifications/cancelled` | Cancels a call in progress, or ends a subscription |

- **Request metadata.** Every request carries `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities` in `params._meta`, as MCP requires. A request for another MCP version gets `UnsupportedProtocolVersion` (−32022).
- **Errors in the request.** A request whose parameters are malformed gets `InvalidParams` (−32602), and so does a call to a tool that is not in the catalogue.
- **Unknown methods** get `MethodNotFound` (−32601).
- **Results** come back in the `payload` of an `mcp` message whose `reply_to` is the request's `seq`.

Each tool definition carries two keys in `_meta`:

| Key | Meaning |
|---|---|
| `ai-platform/safety` | The capability's safety class: `informational`, `privacy`, `physical` or `system` (SEC-8) |
| `ai-platform/version` | The capability's version, an integer (EXT-7) |

**How the device enforces this:**
- It enforces the safety classes itself. A class its owner has switched off is left out of the catalogue (SEC-9), and a call outside the catalogue is refused like an unknown tool.
- Arguments that do not match the tool's `inputSchema` give a tool error (`isError: true`) whose text says what is wrong. MCP advises this, so that a language model can correct itself.
- A capability that fails, or does not answer within the device's time limit, also gives a tool error.
- Results carry `structuredContent` that matches the tool's `outputSchema`, and the same JSON as text.

What a device offers is its own. A robot's, for one, come from its modules, and a new capability needs no change here. Settings and updates are capabilities too (IO-12, IO-13): a device that the cloud may configure, or tell of an update, offers tools for them in the `system` class.

## Events

The device sends an event only if the cloud subscribed to it in its `hello`:

```json
{"type": "event", "seq": 6, "name": "screen.touched", "time": "2026-10-28T03:20:12.800Z", "data": {"x": 0.42, "y": 0.61}}
```

`data` matches the schema the device declared for the event. Events that happen while the control channel is down may wait for it: a bounded number, the oldest dropped first (REL-3).

## Conversations

Only in a session with conversations (see [`hello`](#hello)).

### Opening one

**The device opens one** when someone speaks to it:
1. On the wake word, a touch or a button, it shows at once that it listens (PERF-1), and keeps what it hears from then on.
2. It asks for a conversation, with an identifier it makes:
   ```json
   {"type": "conversation.request", "seq": 7, "conversation": "01a18086-9160-765a-a90f-9dd0604d45f2",
    "trigger": "wake_word", "context": {"battery": 82.0, "charging": false}}
   ```
   - `trigger` is `wake_word`, `touch` or `button`.
   - `context` is a snapshot of the device (IO-4): `battery` (percent) and `charging`, each `null` when unknown. Later minor versions may add fields.
3. The cloud answers with `conversation.start`, or with an `error`: `limit_reached` when a budget or a quota is spent, or `unavailable` when it cannot talk now. Either may give `retry_after`, in seconds.
4. After an error, with no answer within `start_timeout`, or while its control channel is down, the device gives a cue of its own, without words ([ADR-0002](../../docs/decisions/0002-languages.md), decision 5), and drops what it kept. Without an answer, it also sends `conversation.end` `no_answer`.

**The cloud opens one,** such as for a reminder, with a `conversation.start` of its own:
- It asks the device to listen (`listen: true`) only when it wants an answer, and the device's owner allows the `privacy` class: a conversation the cloud opens is in it (SEC-8). A device refuses one it may not listen to, with the error `not_allowed`, and the cloud may open it again without listening.
- With `listen: false`, the device plays the cloud's voice and sends nothing. A wake word ends that conversation, and opens a new one.
- A device already in a conversation refuses with `busy`. When both sides open one at once, the device's wins: it refuses the cloud's.

```json
{"type": "conversation.start", "seq": 3, "reply_to": 7, "conversation": "01a18086-9160-765a-a90f-9dd0604d45f2",
 "listen": true, "media": {"livekit": {"url": "wss://media.cloud.example", "token": "eyJhbGciOiJIUzI1NiIs..."}}}
```

| Field | Meaning |
|---|---|
| `conversation` | The device's identifier, for one it asked for; the cloud's, for one it opens |
| `listen` | Whether the device streams what it hears |
| `media` | Where the conversation's audio goes: one of the media the device offered in its `hello` |

### The room

`media.livekit` gives a LiveKit server and a token for the conversation's room. The token names the room and the device's identity, and lets the device publish a microphone and data, and subscribe.

- **Joining.** The device joins at once: the token may expire soon after. The server's address follows SEC-1: `wss://`, or `ws://` to the device itself, for development.
- **Its microphone,** when `listen` is true, is a track of source `microphone`. Only agents may subscribe to it, as the device sets before it publishes the track (PRIV-1).
- **It listens only to agents.** It plays audio, and takes the conversation's messages, only from participants of kind `agent`, which only the cloud's tokens can make (SEC-7). It ignores, and logs, anything else in the room.
- **The audio heard before the agent.** The device keeps what it hears until an agent subscribes to its microphone. It then sends that audio to the agent as LiveKit's pre-connect audio: a byte stream on the topic `lk.agent.pre-connect-audio-buffer`, with the attributes `trackId` (its microphone's track), `sampleRate` and `channels`, holding 16-bit PCM. LiveKit's agents put that audio before the track's, so that no word is lost ([LiveKit](https://docs.livekit.io/agents/multimodality/audio/)). The device then feeds the track live.
- **No agent.** If no agent subscribes within `agent_timeout`, or the agent leaves and none comes back within it, the device ends the conversation with `no_agent`.
- **The format** is Opus, negotiated by WebRTC through SDP ([RFC 7874](https://www.rfc-editor.org/rfc/rfc7874)). This settles NEG-1 to NEG-6 of the requirements without a scheme of our own.
- **A lost room.** LiveKit resumes after a short loss. When it cannot, the device ends the conversation with `media_lost`.
- **A lost control channel** does not end the conversation: its audio, its turns and its answers go on in the room. Calls to the device wait for the session to resume, and a new session's `hello` names the conversation.

### Turns and responses

The device streams what it hears for the whole conversation. The agent decides where the user's turns begin and end, and says so in the room; the device shows it on its face.

```mermaid
sequenceDiagram
    participant D as Device
    participant A as Agent, in the room
    participant C as Cloud, on the control channel
    D-->>A: what the user says
    A->>D: turn.start
    A->>D: turn.speech_end
    A->>D: response.start, response.text
    A-->>D: its voice
    C->>D: mcp: tools/call screen.show_expression
    D->>C: mcp: result
    A->>D: response.end
    Note over D,A: more turns, until a silence or a goodbye
    D->>C: conversation.end
```

**In the room.** The conversation's messages go between the device and the agent:
- **Shape.** Each is one LiveKit text stream on the topic `conversation`, sent to the other's identity only: a JSON object with a `type`, in UTF-8, up to 1 MiB.
- **No numbers.** The room keeps its messages in order, and they end with the conversation, so they have no `seq`.
- **Validation.** The device validates what the agent sends against `$defs/from_agent` of [`schema.json`](schema.json), and the agent what the device sends against `$defs/from_device_in_room`. A message that fails is ignored and logged: the room has no `error`. The device takes from the agent the same rates as on the control channel (SEC-15).
- **Unknown content** is ignored, as on the control channel.

| Type | From | Purpose |
|---|---|---|
| `turn.start` | agent | The user started speaking |
| `turn.speech_end` | agent | The user has finished speaking |
| `turn.cancel` | agent | The turn is dropped |
| `response.start` | agent | An answer begins; its voice follows on the agent's track |
| `response.text` | agent | The answer's text, piece by piece |
| `response.end` | agent | The answer is complete |
| `response.stop` | agent | Stop playing the answer, now |
| `response.interrupted` | device | The user spoke over the answer |

- **Turns.** The agent says when the user starts speaking, `turn.start`, and when it judges that they have finished, `turn.speech_end` ([ai-robot ADR-0012](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0012-end-of-speech.md)). Each turn has an identifier the agent makes. `turn.cancel` drops a turn, with a `reason` such as `noise`, or speech not meant for the device.
  ```json
  {"type": "turn.speech_end", "turn": "01a18086-9854-7225-8534-4e2bfd22bb42"}
  ```
- **Answers.** The agent answers with a response. Its voice plays on the agent's track, from about `response.start` to about `response.end`:
  ```json
  {"type": "response.start", "response": "01a18086-9e30-…", "turn": "01a18086-9854-…", "language": "en"}
  {"type": "response.text", "response": "01a18086-9e30-…", "delta": "It is sunny in Hanoi, "}
  {"type": "response.end", "response": "01a18086-9e30-…"}
  ```
  - `turn` is `null` for an answer that no turn asked for, such as a reminder in a conversation the cloud opened.
  - `language` is the answer's language: the one the user spoke, among the device's.
  - `response.text` gives the text of the speech in pieces, `delta`, for the screen and the logs.
  - The agent may call capabilities during an answer, such as an expression while it speaks. Its calls go on the control channel, as every call does ([Capabilities](#capabilities-mcp)).
- **Stopping.** `response.stop` asks the device to stop playing at once, and to drop what it still holds. The agent stops its voice too.
- **Barge-in.** When the user speaks over an answer, the device stops playing at once, on its own (PERF-3), and sends `response.interrupted`. The agent stops its voice and forgets what was not played: it knows what it sent, and when.
- **One turn and one response at a time** in a conversation (SES-8). A new one ends the one before, as if it had ended.
- **Crossings.** A message about a turn, a response or a conversation that has ended is ignored, not refused: it may have crossed the end on its way.

### Ending

Either side ends a conversation with `conversation.end` and a `reason`, on the control channel. Both then leave the room, and the device stops streaming at once (PRIV-1).

```json
{"type": "conversation.end", "seq": 9, "conversation": "01a18086-9160-765a-a90f-9dd0604d45f2", "reason": "idle"}
```

| Reason | From | When |
|---|---|---|
| `done` | cloud | The exchange is over |
| `user` | both | The user ended it: in words, which the cloud understood, or with a touch |
| `idle` | device | Nobody spoke, neither the user nor the cloud, for `idle` seconds |
| `longest` | device | The conversation lasted `longest` seconds |
| `muted` | device | The user muted the microphone |
| `limit_reached` | cloud | A budget or a quota ran out |
| `no_answer` | device | The cloud did not answer the request in time |
| `no_agent`, `media_lost` | device | See [The room](#the-room) |
| `lost` | cloud | The cloud no longer knows the conversation |
| `error` | both | Anything else |

The device ends a conversation on its own after `idle` or `longest`, whatever the cloud does, so that audio never leaves it for longer than its settings allow (PRIV-1).

## Errors

```json
{"type": "error", "seq": 4, "reply_to": 9, "code": "not_allowed",
 "message": "the owner does not allow the cloud to listen"}
```

| Code | Meaning |
|---|---|
| `invalid_message` | The message failed `schema.json`, or was too large |
| `unknown_conversation` | The message names a conversation the receiver does not know |
| `not_allowed` | The device's owner does not allow it (SEC-9) |
| `busy` | The device is in another conversation |
| `limit_reached` | A budget or a quota is spent. `retry_after` may say when to try again. |
| `unavailable` | The cloud cannot hold a conversation now. `retry_after` may say when to try again. |
| `rate_limited` | The sender sent too many messages; some were dropped |
| `internal` | The receiver failed to handle a valid message |

An error answers a numbered message. A side that cannot handle a `hello`, a `ping` or a `pong` ends the session with `bye`. A code a side does not know, it takes as `internal`.

## Update required

The cloud speaks each major version for at least 24 months after the next one ships, and accepts no version below the lowest it allows, for security ([ADR-0003](../../docs/decisions/0003-compatibility.md)):
- **A major it no longer speaks:** the handshake gets `410 Gone` ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110), §15.5.11).
  ```http
  HTTP/1.1 410 Gone
  Content-Type: application/problem+json

  {"type": "about:blank", "title": "Gone", "status": 410,
   "detail": "This version of the cloud link is no longer spoken: update the device."}
  ```
- **A version or software below the lowest it allows:** the cloud answers the `hello` with `bye` `update_required`.

The device then shows that it needs an update; the app learns it from the cloud. It updates through its own update channel, which does not depend on this link ([ai-robot ADR-0014](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0014-updates.md)). Until it has updated, it connects again only at the longest backoff, `reconnect_max`.

## Security and privacy

How this version meets the [requirements](requirements.md#9-security):
- **SEC-1:** TLS on all three connections: the token endpoint, the control channel and the room. No redirects. Plain HTTP and WebSocket only to the device itself, for development.
- **SEC-2 to SEC-4:** each connection opens with a short-lived token, bought with an assertion that the device's key signs. Revoking a device refuses its assertions (`invalid_client`), and ends its session (`bye` `revoked`).
- **SEC-5:** neither side logs an assertion, an access token or a room's token.
- **SEC-6:** the cloud ties a connection to the device its token names, and confines it to that device's data.
- **SEC-7 to SEC-9:** the device checks every call against its catalogue, and enforces the safety classes itself. The cloud learns which classes are allowed, and never sets them. In the room, the device takes messages and audio from agents only.
- **SEC-12, SES-6:** assertions are single-use (`jti`), and messages are numbered within a session, so that a duplicate has no effect. TLS keeps others from replaying them.
- **SEC-14, SEC-15:** both sides validate every message, and bound sizes and rates.
- **SEC-16:** the device only opens connections, and listens on none.
- **PRIV-1:** audio leaves the device only in a conversation: one its user opens, or one the cloud opens with its owner's leave. The device ends conversations on its own (`idle`, `longest`, `muted`), and only agents may hear its microphone.
- **PRIV-5:** `ping` and `pong` carry numbers only.

## Settings

The names in `code` in this document are settings, of the device or of the cloud. The values below are starting points, not part of the protocol: each side sets its own in its configuration.

| Setting | Side | Starting point | Meaning |
|---|---|---|---|
| `reconnect_first`, `reconnect_max` | device | 1 s, 60 s | The backoff |
| `hello_timeout` | both | 5 s | How long a side waits for the other's `hello` |
| `replay` | both | 1,000 messages | How many sent messages a side keeps, to resume |
| `rate`, `burst`, `backlog` | device | 50 a second, 100, 500 | What the device takes from the cloud |
| `start_timeout` | device | 5 s | How long the device waits for `conversation.start` |
| `agent_timeout` | device | 10 s, as long as LiveKit's web client waits for an agent | How long the device waits for an agent |
| `idle` | device | 10 s | The silence that ends a conversation |
| `longest` | device | 900 s | The longest conversation |
| `ping_interval` | cloud | 20 s | How often devices ping; sent in the cloud's `hello` |
| `resume_window` | cloud | 120 s | How long a session can be resumed after its connection was lost |

## Changing the protocol

- **No version change.** A new capability or event needs no protocol change: the device's catalogue and `hello` carry them.
- **Minor version.** A new message type, or a new optional field, raises the minor version. The specification, the schema and the examples change together (CONTRIBUTING.md, rule 2).
- **Major version.** Changing or removing anything a side relies on raises the major version, with a path of its own (`/device/v4/link`). The cloud runs both majors side by side ([ADR-0003](../../docs/decisions/0003-compatibility.md)).
- **MCP.** The MCP revision is pinned and changes deliberately ([ai-robot ADR-0008](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0008-cloud-link-messages.md)). `server/discover` lets a device support two revisions during a change.

## References

- IETF: [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455) (WebSocket), [RFC 6750](https://www.rfc-editor.org/rfc/rfc6750) (bearer tokens), [RFC 6749](https://www.rfc-editor.org/rfc/rfc6749) and [RFC 7523](https://www.rfc-editor.org/rfc/rfc7523) (OAuth 2.0, and JWT client authentication), [RFC 7518](https://www.rfc-editor.org/rfc/rfc7518) and [RFC 7638](https://www.rfc-editor.org/rfc/rfc7638) (ES256, thumbprints), [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) (HTTP semantics), [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) (Problem Details), [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562) (UUIDv7), [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339), [RFC 7874](https://www.rfc-editor.org/rfc/rfc7874) (WebRTC audio).
- Retrieved 2026-10-28:
  - [Model Context Protocol, revision 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28), still the current one;
  - Discord: [the gateway](https://docs.discord.com/developers/events/gateway) (heartbeats with the last sequence number, resuming, and replaying missed events) and [voice connections](https://docs.discord.com/developers/topics/voice-connections) (the voice server's address and token, given on the gateway);
  - Cloudflare: [WebSockets](https://developers.cloudflare.com/network/websockets/) (idle connections closed, and connections ended when new code is released);
  - Amazon: the Alexa device SDK's [pings](https://github.com/alexa/avs-device-sdk/blob/master/ACL/src/Transport/PingHandler.cpp), `GET /ping` after five idle minutes ([`HTTP2Transport.cpp`](https://github.com/alexa/avs-device-sdk/blob/master/ACL/src/Transport/HTTP2Transport.cpp));
  - Google: [Gemini Live API, session management](https://ai.google.dev/gemini-api/docs/live-session) (`GoAway`, and resuming);
  - OpenAI: [the Realtime API with WebRTC](https://developers.openai.com/api/docs/guides/realtime-webrtc) (a conversation's events on a data channel of the call);
  - LiveKit: [pre-connect audio](https://docs.livekit.io/agents/multimodality/audio/), and how [its web client sends it](https://github.com/livekit/client-sdk-js/blob/main/src/room/participant/LocalParticipant.ts) and [its agents read it](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/room_io/_pre_connect_audio.py); its signalling's pings ([`livekit_rtc.proto`](https://github.com/livekit/protocol/blob/main/protobufs/livekit_rtc.proto)).
