# 0006 — The cloud link in two channels: control always on, media only to talk

- **Status:** Proposed
- **Date:** 2026-10-28

## Context

- Today a device stays in its LiveKit room for as long as it runs. The room carries everything (the cloud link 2.2, ai-robot ADR-0009): the session's messages, the capabilities, the events, and the audio of turns.
- That costs, all day and for each device:
  - two WebRTC participants, the device and the cloud's agent, even when nobody speaks. That is about 86,400 participant-minutes a month for one robot, where LiveKit Cloud's free plan includes 5,000 a month;
  - one agent's job, held idle in the cloud;
  - a media server that devices can reach over UDP, all the time.
- Voice platforms that serve many devices keep a light channel always open, and stream audio only for an interaction:
  - Alexa's devices hold a long-lived HTTP/2 stream for the cloud's directives, and send speech in requests of their own;
  - xiaozhi's devices keep MQTT for control, and open a UDP channel for audio when a conversation starts.
- The owner wants a wake word to open a conversation, many turns long, as one talks with a person, rather than a single request (2026-10-28). A conversation may last long.
- WebSockets pass through HTTPS proxies and tunnels, such as the Cloudflare Tunnel Luni Cloud ran behind. WebRTC media needs UDP to a public address, or a TURN relay.

## Decision

1. **Two channels between a device and the cloud:**
   - **control**, always on: a WebSocket over HTTPS to `ai-cloud`. It carries the session: versions, the capabilities' catalogue, MCP calls, events, settings, notices of updates, and the cloud's requests to talk;
   - **media**, only to talk: the device's LiveKit room, joined for a conversation and left after it.
2. **A conversation:**
   1. A wake word or a touch opens it. The cloud may open one too, on the control channel, within the privacy class the owner allows (SEC-8, SEC-9).
   2. The device asks for its room on the control channel, and gets the LiveKit server and a token.
   3. It joins, and the agent joins with it. The device keeps the audio heard from the wake word until its track is up, so that no word is lost while it connects.
   4. The conversation lasts as many turns as people speak. The device streams what it hears throughout, the cloud takes the turns, and either side may interrupt the other.
   5. It ends when the user ends it, or after `idle` seconds in which nobody speaks, a setting. Both then leave the room.
3. **The control channel's authentication** is the device's: an assertion signed by its key buys a short-lived token (ai-robot ADR-0010), which opens the WebSocket.
4. **This is the cloud link's version 3.0.** It also makes ADR-0001's renames to devices and ADR-0005's homes. The protocol keeps its messages: what the room's data channel carried moves to the control channel unchanged, but for the names.
5. **Other kinds of control channel** may follow for devices that cannot keep a WebSocket, such as MQTT for devices on batteries. Each would be its own link, with the same messages and the same identity.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Everything in a room that stays open (the cloud link 2.2) | Media minutes and an idle agent for each device all day, and a media server reachable over UDP at all times. |
| MQTT for control, from the start | A broker to run, for messages that a WebSocket carries as they are. It stays the choice for devices that need it (decision 5). |
| HTTP polling | The cloud's requests (a reminder, a call to talk) would wait for the next poll. |
| A room per conversation, with no control channel | The cloud could not reach an idle device, for a reminder or an update. |

## Consequences

- Positive:
  - a wake word opens a conversation, which lasts as long as people talk;
  - media costs only while people talk. One owner can start on LiveKit Cloud's free plan ([ai-cloud ADR-0004](https://github.com/trungnguyen278/ai-cloud/blob/main/docs/decisions/0004-hosting.md));
  - the cloud's own servers need nothing but HTTPS, so they can sit behind a tunnel at home;
  - an idle device costs one WebSocket, not a media session and an agent, which is what lets the cloud serve many devices.
- Negative / accepted trade-offs:
  - joining a room takes time after a wake word. The device's buffer keeps the words, and the room stays open for follow-ups;
  - a device keeps two connections while it talks;
  - devices and the cloud implement the cloud link 3.0, which the renames required anyway.
- Follow-up:
  - the cloud link 3.0's specification, schema and examples, here;
  - `idle`, and the room's request and answer, in the specification;
  - PRIV-1 now speaks of conversations, not turns (in this change);
  - in ai-robot, the voice module holds a conversation across turns, as an ADR there decides;
  - in ai-robot, the cloud adapter for 3.0, after the move to this repository's pin.

## References

Retrieved 2026-10-28:

- Amazon: [managing the HTTP/2 connection to Alexa Voice Service](https://developer.amazon.com/en-US/docs/alexa/alexa-voice-service/manage-http2-connection.html) (the downchannel).
- [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32): its MQTT and UDP protocol.
- LiveKit: [pricing](https://livekit.com/pricing) (the Build plan), and [ports and firewall](https://docs.livekit.io/home/self-hosting/ports-firewall/).
- Cloudflare: [WebSockets](https://developers.cloudflare.com/network/websockets/).
