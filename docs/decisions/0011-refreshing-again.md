# 0011 — Refreshing again, after an answer was lost

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

- **[ADR-0008](0008-sign-in.md), decision 3:** a refresh token rotates on every use, and one presented twice ends its session. RFC 9700 asks for rotation or sender-constrained tokens from a public client, such as an app.
- **RFC 9700, 4.14.2,** says what rotation detects. If a refresh token is used by an attacker and by the legitimate client, "one of them will present an invalidated refresh token", and the server "will revoke the active refresh token". It says nothing of retries.
- **A phone loses answers.** The request reaches the cloud, which rotates the token, and the answer never arrives: the network drops, or the app is stopped. The app still holds the old token, and its next refresh presents it again. The session ends, and the person signs in again, as if their token had been stolen.
- **ai-app gives up on a request** after its configured time limit, 15 seconds, and sends again only what the protocol makes safe to repeat (ai-app's ADR-0004).
- **Large providers allow this retry** (read 2026-11-04):

  | Provider | Its setting | Default | What it allows |
  |---|---|---|---|
  | Okta | Grace period for token rotation | 30 s, from 0 to 60 | "the previous token remains valid for the configured amount of time to allow clients to get the new token" |
  | Auth0 | Reuse interval | Off | "a new rotating refresh token is issued"; "only the previous token can be reused", and reusing an older one revokes every token issued since |

## Decision

1. **A refresh token still refreshes for `refresh_reuse` after its first use, while its replacement has not been used.** That is a retry after a lost answer. The cloud answers with new tokens, as for any refresh, and the replacement it gave before stops working.
2. **Any other refresh token presented again ends its session,** as before: a token older than the one just replaced, one whose replacement has been used, or one past `refresh_reuse`.
3. **The app sends a refresh again only when no answer came,** at once, with the same refresh token.
4. **`refresh_reuse` starts at 60 seconds,** Okta's most. It covers one retry after the app's time limit, and the phone's network coming back soon after.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Rotation without a retry, as before | A lost answer signs the person out, whatever the network did. |
| The same answer again, for a retry | The cloud would keep the new tokens themselves, not their hashes, for the time a retry may come. |
| A longer window, of minutes | A stolen token would work beside the app for longer. |
| Refresh tokens that never rotate | RFC 9700 then asks for sender-constrained tokens, which ADR-0008 left out: Expo's modules cannot sign with a key in the phone's keystore. |

## Consequences

- Positive:
  - a lost answer no longer signs the person out;
  - theft is still detected: whichever side refreshes next presents a token that no longer works, and the session ends.
- Negative / accepted trade-offs:
  - for `refresh_reuse`, a stolen copy of the token just replaced works once beside the app, until the app's next refresh ends the session;
  - against SEC-12's rule that a replayed message has no effect beyond its first one, a retry has one: the same session goes on, with new tokens. It never has two refresh tokens that work, since the one given before stops working. The access token of a lost answer works until it expires, within `access_lifetime`.
- Follow-up:
  - the app API 1.3, which specifies it;
  - ai-cloud, which implements it;
  - ai-app's session, and its simulated cloud.

## References

- [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700), 2.2.2 and 4.14.2 (read 2026-11-04).
- Okta: [refresh tokens](https://developer.okta.com/docs/guides/refresh-tokens/main/), "Refresh token rotation".
- Auth0: [configure refresh token rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/configure-refresh-token-rotation).
- [ADR-0008](0008-sign-in.md); ai-app's ADR-0004.
