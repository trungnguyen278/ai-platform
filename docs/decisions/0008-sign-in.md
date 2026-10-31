# 0008 — Signing in: the cloud's own accounts, reached with Google or Apple

- **Status:** Accepted
- **Date:** 2026-10-31

## Context

- **Who signs in.** The people of a home who have an account: one owner, any admins and members ([ADR-0005](0005-homes.md)). Profiles never sign in.
  - They sign in to ai-cloud through ai-app.
  - Set-up's registration needs a member who may add devices (set-up 2.0), and the homes, devices, settings and control all go through the cloud.
- **The stores' rules** (retrieved 2026-10-31):
  - **App Store 4.8:** an app whose primary account is set up with a third-party login, such as Google's, must also offer an equivalent login. That login must limit data to a name and an email, let people keep their email private, and not track them for advertising without consent. Sign in with Apple is one. An app that uses only its own account system is exempt.
  - **App Store 5.1.1(v) and Google Play:** an app that creates accounts lets people delete them from inside the app.
    - Google Play also asks for a web page where deletion can be requested.
    - Apple asks apps that offer Sign in with Apple to revoke its tokens through its REST API.
- **The platform's requirements:**
  - every request confined to the account's homes (SEC-6);
  - credentials that expire (SEC-12);
  - what the cloud keeps about a person can be seen and deleted (PRIV-4);
  - adults only (PRIV-7), so there are no children's accounts.
- **The project:** personal first, since its maker is the first owner; then many owners (ai-cloud's phases). Little money: no cost for each person, no messages to pay for.
- **The phones' own sign-in:**
  - **Android:** Credential Manager, one API for passkeys, passwords and Sign in with Google. Google's older sign-in library is deprecated.
    - The app gets a Google ID token (OpenID Connect), carrying a nonce if it asks for one.
    - Google says the server must verify the token and its nonce before trusting it.
  - **iOS:** AuthenticationServices, for Sign in with Apple and passkeys. Apple's ID token is OpenID Connect too. Google's SDK signs in with Google there.
  - **In React Native:**
    - Expo's own modules: `expo-apple-authentication` for Apple, and `expo-secure-store` for secrets.
    - For Credential Manager, community modules: `react-native-credentials-manager` (0.9.0, MIT, 2026-09). `react-native-google-signin` keeps Credential Manager for its paid licence.
    - A module that wraps one platform API is small enough for ai-app to keep its own if one stops.
  - **Passkeys need a domain of the project's own,** associated with the app on both platforms (Digital Asset Links, Apple's associated domains), and a way back for someone who lost theirs.
- **Sessions:** under the OAuth 2.0 Security Best Current Practice ([RFC 9700](https://www.rfc-editor.org/rfc/rfc9700), 2025-01), a public client's refresh tokens, such as an app's, MUST be sender-constrained or rotated. With rotation, a refresh token presented twice makes the server revoke the active one.

## Decision

1. **The cloud keeps its own accounts.**
   - An account is a person: an identifier (UUIDv7, [ADR-0004](0004-conventions.md)), a name, an email, languages.
   - Its sign-in methods are identities linked to it: a provider, and the provider's identifier for the person (`sub`). The account outlives any one of them, and a method can be added or removed.
   - Accounts are never merged by email alone. A person links a second method while signed in.
2. **People sign in with Google or with Apple,** through each platform's native sign-in.
   - **Android:** Credential Manager, for Google.
   - **iOS:** AuthenticationServices for Apple, and Google's SDK for Google, so that an account made on Android works on iOS (App Store 4.8).
   - **Both are OpenID Connect:**
     - the app asks the cloud for a nonce;
     - the provider puts it in its ID token;
     - the app gives the token to the cloud.
   - **The cloud verifies the token itself,** and never trusts the app's reading of it:
     - the provider's signature, against its published keys;
     - the issuer, the audience (the project's client identifiers) and the expiry;
     - the nonce, which it issued, and then forgets.
   - **The first sign-in with an identity creates its account.** Joining a home is an invitation's work (ADR-0005), not sign-in's.
3. **Sessions are the cloud's own tokens,** from its OAuth 2.0 authorization server, which issues devices' tokens too (the cloud link).
   - **The exchange:** the provider's ID token buys them (Token Exchange, [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693)).
   - **An access token:** short-lived, sent as a bearer token on every request ([RFC 6750](https://www.rfc-editor.org/rfc/rfc6750)), confined to the account's homes (SEC-6).
   - **A refresh token:**
     - opaque, and rotated on every use;
     - kept in the phone's secure storage: the Keystore, the Keychain;
     - presented twice, it ends its session (RFC 9700).
   - **A session is one app on one phone.** An account sees its sessions and can end any; signing out revokes the refresh token ([RFC 7009](https://www.rfc-editor.org/rfc/rfc7009)).
   - **Lifetimes** are the cloud's settings.
4. **An account is deleted from the app,** or from a web page (the stores' rules).
   - Deleting it deletes what is the person's (ADR-0005, PRIV-4), revokes Apple's tokens, and ends every session.
   - The owner of a home with other members hands the home over, or deletes it, first.
5. **Development signs in without Google or Apple.** The cloud's development environment has a simulated provider, which issues ID tokens for test people the same way. The app, the cloud and their tests then run end to end.
6. **The project's client identifiers** (Google's client IDs, Apple's service and bundle identifiers) are configuration of the cloud and the app, not secrets. Apple's key for revoking tokens is a secret of the cloud.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Passwords | The cloud would store a secret that people reuse elsewhere, and need resets, breach checks and second factors. |
| Codes or links by email | No password, but email to send, its delivery to watch, and codes that a fake site can ask for. An email service costs money beyond its free tier. |
| Codes by SMS | Each message costs money, and a SIM can be swapped. |
| Passkeys | They resist phishing, and need neither Google nor Apple. But they need the project's own domain associated with the app on both platforms. Someone who lost theirs needs a way back, which leads to a provider or to codes. The identities' model takes them as one more method. |
| An identity service (Firebase Authentication, Auth0, Clerk) | People's identities would live at a vendor, at its prices and terms. The cloud runs on one machine at home, with a token endpoint of its own. |
| Zalo's login, widely used in Vietnam | Its OAuth (version 4) returns access tokens, with no ID token for the cloud to verify, as Logto's catalogue of providers lists it. Apple would still be needed on iOS. The identities' model takes it as one more method. |
| Sender-constrained tokens (DPoP, [RFC 9449](https://www.rfc-editor.org/rfc/rfc9449)) instead of rotation | Stronger, since a stolen token is useless without the phone's key. But the app would sign every request with a key in the phone's keystore, which Expo's modules do not offer. Rotation meets RFC 9700. |
| Google's older sign-in library, or Google's page in a browser tab | The library is deprecated. Google directs Android apps to Credential Manager, and a browser tab is a worse experience. |

## Consequences

- Positive:
  - the cloud stores no secret that people chose, and Google and Apple bring their own protection against account takeover;
  - nothing to pay for each person, since nothing is sent to them;
  - one account works on Android and on iOS;
  - devices and people get their tokens from one OAuth authorization server.
- Negative / accepted trade-offs:
  - everyone needs a Google or an Apple account. On Android, a phone without Google's services cannot sign in;
  - an account made with Apple on iOS reaches Android only once it has added Google;
  - sign-in needs native modules, so a development build of the app rather than Expo Go. Set-up over Bluetooth LE needs one anyway;
  - the project needs a Google Cloud project for its client IDs, and an Apple developer account for iOS, which publishing there needs anyway;
  - a web page for deletion is needed before the first release on Google Play.
- Follow-up:
  - the app ⇄ cloud protocol: the endpoints for the nonce, the exchange, refreshing, sessions, signing out and deletion ([ADR-0004](0004-conventions.md));
  - ai-cloud: the `accounts` module's accounts, identities and sessions. Its architecture names an ADR-0005 of its own for owners' sign-in, which this ADR replaces;
  - ai-app: its `account` module, and its choice of a Credential Manager module, in an ADR of its own;
  - what the cloud keeps of a person, with the law on personal data (ai-cloud ADR-0006).

## References

Retrieved 2026-10-31:

- Apple:
  - [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/), 4.8 and 5.1.1(v);
  - [offering account deletion in your app](https://developer.apple.com/support/offering-account-deletion-in-your-app).
- Google:
  - [About the migration from legacy Google Sign-In](https://developer.android.com/identity/sign-in/legacy-gsi-migration);
  - [Sign in with Google with Credential Manager](https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation);
  - Google Play's [app account deletion requirements](https://support.google.com/googleplay/android-developer/answer/13327111).
- IETF and OpenID:
  - [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700) (OAuth 2.0 Security BCP);
  - [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693), [RFC 6750](https://www.rfc-editor.org/rfc/rfc6750), [RFC 7009](https://www.rfc-editor.org/rfc/rfc7009), [RFC 9449](https://www.rfc-editor.org/rfc/rfc9449);
  - [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html).
- Logto's [OAuth providers explorer: Zalo](https://logto.io/oauth-providers-explorer/zalo).
- Libraries:
  - [`react-native-credentials-manager`](https://github.com/benjamineruvieru/react-native-credentials-manager), and [`react-native-google-signin`'s licensed features](https://react-native-google-signin.github.io/docs/install);
  - Expo's [`expo-apple-authentication`](https://docs.expo.dev/versions/latest/sdk/apple-authentication/) and [`expo-secure-store`](https://docs.expo.dev/versions/latest/sdk/securestore/);
  - [`py_webauthn`](https://github.com/duo-labs/py_webauthn), for passkeys on the server.
