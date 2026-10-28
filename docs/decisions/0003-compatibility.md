# 0003 — Compatibility: every device in the field keeps working

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

- Devices update themselves, but not together (ai-robot [ADR-0014](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0014-updates.md)). Some stay off for months, and an owner may turn automatic updates off. The cloud therefore meets every version still in the field.
- Each protocol has its own version, *major.minor*, and the two sides negotiate it. The cloud link keeps the device's major and the lower of the two minors; set-up refuses another major. CI checks that a minor version still accepts the examples of the one before ([check.py](../../tools/check.py)).
- A device that can no longer fetch its update is stranded. No later fix reaches it.
- Kubernetes, which many clients depend on, publishes how long each kind of API version lives after it is deprecated, and never removes a stable version within a major release.

## Decision

1. **The cloud speaks every major version that active devices still use**, and each one for at least 24 months after its successor ships. After that, a device on the old major is told to update.
2. **The update path never breaks.** Whatever its version, a device can always learn of the newest release and install it:
   - the update channel's file and the steps that install a release keep a contract of their own, versioned apart from the rest;
   - the cloud answers a major it no longer speaks with "update required" and where to update from, never with silence.
3. **A minimum version per protocol**, for security only. A device below it is told to update, on its screen and in the app, and can still update (rule 2).
4. **Deprecation is announced**:
   - in the protocol's version notes;
   - to owners, through the app, at least 6 months before the cloud stops speaking a version.
5. **A breaking change** needs a new major version, an ADR, and a plan for both majors to run side by side in the cloud.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Speak only the newest version | Every device would have to update at once. One left off for a month would find its cloud gone. |
| Speak every version forever | The cloud's cost and risk grow with each version, and old ones keep old weaknesses. |
| A version per message or capability, as Alexa's interfaces have | Capabilities are already declared by each device, through MCP. For the link itself, a major and a minor are enough. |

## Consequences

- Positive:
  - an owner's device keeps working through the cloud's changes, and can always catch up;
  - protocol changes are planned, not discovered.
- Negative / accepted trade-offs:
  - for two years after a major, the cloud runs two of it;
  - the update path's contract can hardly change, so it must be designed with care.
- Follow-up:
  - the update channel's format, with its own version (ai-robot ADR-0014), here;
  - the "update required" answer in the cloud link and set-up;
  - a count, in the cloud, of the active devices on each version.

## References

- [Kubernetes deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/), retrieved 2026-10-28.
- [Semantic Versioning 2.0.0](https://semver.org/).
