# 0006 — The cloud link in two channels: control always on, media only to talk

- **Status:** Proposed
- **Date:** 2026-10-28
- **Revised:** 2026-10-28: a conversation's own messages stay in its room, with its audio; the control channel pings on its own, and its sessions resume.

## Context

- Today a device stays in its LiveKit room for as long as it runs. The room carries everything (the cloud link 2.2, ai-robot ADR-0009): the session's messages, the capabilities, the events, and the audio of turns.
- That costs, all day and for each device:
  - two WebRTC participants, the device and the cloud's agent, even when nobody speaks. That is about 86,400 participant-minutes a month for one robot, where LiveKit Cloud's free plan includes 5,000 a month;
  - one agent's job, held idle in the cloud;
  - a media server that devices can reach over UDP, all the time.
- Voice platforms that serve many devices keep a light channel always open, and stream audio only for an interaction:
  - Alexa's devices hold a long-lived HTTP/2 connection, whose downchannel carries the cloud's directives, and send speech in requests of their own;
  - xiaozhi's devices keep MQTT for control, and open a UDP channel for audio when a conversation starts;
  - Discord's clients keep a gateway open, which gives them a voice server's address and token when they join a call. Who is speaking travels on the voice connection, with the audio.
- Realtime voice APIs keep a conversation's events with its audio. OpenAI's Realtime API over WebRTC sends them on a data channel of the call itself, and keeps tool calls and business logic on a separate connection from the server.
- In the cloud, a conversation's messages (its turns, its answers, interruptions) are made and read by the agent, which is in the room. Calls to a device come from many places: the agent, reminders, moods, the owner's app.
- Links that stay open for hours ping on their own, so that the ping crosses every proxy to the far end:
  - Alexa's device SDK sends `GET /ping` after five idle minutes;
  - Discord's gateway and LiveKit's signalling send heartbeats at a pace their server sets.

  Proxies also close connections on purpose: Cloudflare ends WebSockets when it releases new code. Gemini Live warns before it closes a connection (`GoAway`), and resumes the session on the next.
- The owner wants a wake word to open a conversation, many turns long, as one talks with a person, rather than a single request (2026-10-28). A conversation may last long.
- WebSockets pass through HTTPS proxies and tunnels, such as the Cloudflare Tunnel Luni Cloud ran behind. WebRTC media needs UDP to a public address, or a TURN relay.

## Decision

1. **Two channels between a device and the cloud:**
   - **control**, always on: a WebSocket over HTTPS to `ai-cloud`. It carries what concerns the device:
     - versions;
     - its capabilities, and every call to them (MCP), whoever calls: the agent of a conversation, a reminder, the app;
     - its events, settings and notices of updates;
     - the opening and the end of conversations;
   - **media**, only to talk: a LiveKit room for each conversation. It carries what concerns the conversation, between the device and the agent: the audio both ways, the turns, the answers and interruptions.
2. **A conversation:**
   1. A wake word or a touch opens it. The cloud may open one too, on the control channel, within the privacy class the owner allows (SEC-8, SEC-9).
   2. The device asks for a conversation on the control channel, and gets its room: a LiveKit server and a token.
   3. It joins, and the agent joins with it. The device keeps the audio heard from the wake word until the agent hears its track, so that no word is lost while it connects.
   4. The conversation lasts as many turns as people speak. The device streams what it hears throughout; the agent takes the turns and says so in the room; either side may interrupt the other.
   5. It ends when the user ends it, or after `idle` seconds in which nobody speaks, a setting. Both then leave the room.
3. **The control channel:**
   - Its authentication is the device's: an assertion signed by its key buys a short-lived token (ai-robot ADR-0010), which opens the WebSocket.
   - It pings on its own, at a pace the cloud sets, and the pings say what each side has received.
   - Its session outlives a connection. Messages are numbered, so that a device can resume its session on a new connection. The cloud asks for that before it closes a connection on purpose.
4. **This is the cloud link's version 3.0,** with ADR-0001's renames to devices.
   - The messages of 2.2 keep their meaning. Each now travels where its owner is: the session's on the control channel, the conversation's in the room.
   - A device's home matters to its registration, which set-up 2.0 carries, not to this link ([ADR-0005](0005-homes.md)).
5. **Other kinds of control channel** may follow for devices that cannot keep a WebSocket, such as MQTT for devices on batteries. Each would be its own link, with the same messages and the same identity, and with its transport's own keep-alive where it has one, such as MQTT's.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Everything in a room that stays open (the cloud link 2.2) | Media minutes and an idle agent for each device all day, and a media server reachable over UDP at all times. |
| MQTT for control, from the start | A broker to run, for messages that a WebSocket carries as they are. It stays the choice for devices that need it (decision 5). |
| HTTP polling | The cloud's requests (a reminder, a call to talk) would wait for the next poll. |
| A room per conversation, with no control channel | The cloud could not reach an idle device, for a reminder or an update. |
| Everything on the control channel, and the room for audio only (this decision's first draft) | The agent makes and reads a conversation's messages. The cloud would relay them between its agent and its gateway for every conversation, and route them between its machines as it grows. A blip of the WebSocket would also disturb a conversation whose audio is fine. |
| Everything about a conversation in the room, the agent's calls to the device included | The device would hold two MCP sessions, and the cloud would check and log calls to a device in two places. The agent would also read the device's catalogue again for each conversation. |
| WebSocket's own Ping and Pong frames | A proxy that ends the WebSocket answers them itself, and libraries hide them, so they cannot say what was received. The links that stay open for hours ping on their own (Alexa, Discord, LiveKit). |
| A new session after each loss, with nothing resumed | A call in flight when the connection drops would be lost, or run twice if sent again. Proxies drop connections routinely. |

## Consequences

- Positive:
  - a wake word opens a conversation, which lasts as long as people talk;
  - media costs only while people talk. One owner can start on LiveKit Cloud's free plan ([ai-cloud ADR-0004](https://github.com/trungnguyen278/ai-cloud/blob/main/docs/decisions/0004-hosting.md));
  - the cloud's own servers need nothing but HTTPS, so they can sit behind a tunnel at home;
  - an idle device costs one WebSocket, not a media session and an agent, which is what lets the cloud serve many devices;
  - a conversation does not depend on the control channel: a blip of the WebSocket leaves its turns and answers alone;
  - one place in the cloud checks and logs every call to a device.
- Negative / accepted trade-offs:
  - joining a room takes time after a wake word. The device's buffer keeps the words, and the room stays open for follow-ups;
  - a device keeps two connections while it talks, and handles messages on both, as the devices of 2.2 already do in the room;
  - the agent's calls to a device go through the control channel, so an expression may follow the words it goes with by some tens of milliseconds;
  - devices and the cloud implement the cloud link 3.0, which the renames required anyway.
- Follow-up:
  - the cloud link 3.0's specification, schema and examples, here: the conversation's messages in the room; the control channel's pings, numbering, resuming and `reconnect`;
  - PRIV-1 now speaks of conversations, not turns (in this change);
  - in ai-robot, the voice module holds a conversation across turns, as an ADR there decides;
  - in ai-robot, the cloud adapter for 3.0, after the move to this repository's pin.

## References

Retrieved 2026-10-28:

- Amazon: the Alexa Voice Service's documentation is offline. Its [device SDK](https://github.com/alexa/avs-device-sdk), archived, shows the downchannel and the pings: [`HTTP2Transport.cpp`](https://github.com/alexa/avs-device-sdk/blob/master/ACL/src/Transport/HTTP2Transport.cpp) and [`PingHandler.cpp`](https://github.com/alexa/avs-device-sdk/blob/master/ACL/src/Transport/PingHandler.cpp).
- [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32): its [MQTT and UDP protocol](https://github.com/78/xiaozhi-esp32/blob/main/docs/mqtt-udp.md).
- Discord: [the gateway](https://docs.discord.com/developers/events/gateway), and [voice connections](https://docs.discord.com/developers/topics/voice-connections).
- OpenAI: [the Realtime API with WebRTC](https://developers.openai.com/api/docs/guides/realtime-webrtc), and [webhooks and server-side controls](https://developers.openai.com/api/docs/guides/realtime-server-controls).
- Google: [Gemini Live API, session management](https://ai.google.dev/gemini-api/docs/live-session) (`GoAway`, and resuming a session).
- LiveKit: [pricing](https://livekit.com/pricing) (the Build plan), [ports and firewall](https://docs.livekit.io/home/self-hosting/ports-firewall/), and its signalling's pings, at the pace the server sets ([`livekit_rtc.proto`](https://github.com/livekit/protocol/blob/main/protobufs/livekit_rtc.proto)).
- Cloudflare: [WebSockets](https://developers.cloudflare.com/network/websockets/).
