# 0001 — Repositories: a family of AI products, sharing one platform

- **Status:** Accepted
- **Date:** 2026-10-28
- **Supersedes:** [ai-robot ADR-0003](https://github.com/trungnguyen278/ai-robot/blob/main/docs/decisions/0003-neutral-repo-naming.md)'s names; its rule against product names in identifiers stays.

## Context

- ai-robot ADR-0003 named the repositories `ai-robot`, `ai-robot-server` and `ai-robot-app`. Only `ai-robot` existed, and every protocol lived in its `protocol/`: defined once, shared by both sides (its design rule 1).
- The cloud side starts now, and two protocols already cross repositories:
  - the cloud link, between the robot and the cloud;
  - set-up, between the owner's app and the robot, carrying a registration for the cloud.
- The robot is the first of the owner's products, not the only one. The others are not known yet, except that they will be AI products. Names and protocols tied to "robot" would mislead as soon as a second product shares the cloud.
- What is costly to change differs:
  - a repository's name: GitHub redirects links and remotes when a repository is renamed or transferred;
  - a name on the wire (`/robot/token`, `robot-registration+jwt`, a field `robot`): once devices are sold, every one of them must keep speaking it.

  Nothing speaks the protocols outside the robot's tests yet, so both are cheap to change now, and only now.
- The cloud link is already built for any device. A device declares what it can do (MCP tools and events, each in a safety class), and the cloud drives only what it declared. A speaker would declare fewer capabilities than a robot.
- How others share a protocol between repositories:

| Project | How |
|---|---|
| MAVLink (PX4, ArduPilot) | The message definitions are a repository of their own. Each autopilot pins it as a git submodule (PX4 at `src/modules/mavlink/mavlink`, ArduPilot at `modules/mavlink`) and generates its code from it. |
| Envoy | The API is written in the main repository and mirrored, read-only, to `data-plane-api` for other projects. |
| Kubernetes | Shared APIs are written in the main repository's `staging/` tree and published to repositories of their own, such as `kubernetes/api`. |
| Home Assistant | One organization; repositories named by role (`core`, `frontend`, `android`, `iOS`, `operating-system`), and an `architecture` repository for decisions that span them. |

- Names that outgrew their first product: MAVLink ("Micro Air Vehicle") also drives ArduPilot's rovers and submarines; Matter's repository is still `connectedhomeip`, from its earlier name.

## Decision

1. **Repositories are named `ai-<what it is>`**, under the owner's GitHub account:

   | Repository | What it is |
   |---|---|
   | `ai-robot` | The robot, renamed from `AI-robot`: its hardware, software, face and firmware, and the protocols inside it |
   | `ai-cloud` | The cloud side of every device: AI, accounts, devices' tokens, set-up's registration, updates, operations |
   | `ai-app` | The owner's app, for every device: set-up, settings, remote control. Created when its work starts. |
   | `ai-platform` | What the others share: the protocols between them, and the decisions that span them |
   | `ai-<product>` | A later product, named by what it is |

   - No product's display name appears in a repository, package or identifier (ADR-0003's rule, kept).
   - The repositories stay under the owner's account. No name in code or protocols contains the account, and GitHub redirects transferred repositories, so moving them to an organization later would change no code.

2. **`ai-platform` holds what the repositories share:**
   - the protocols between them, in `protocols/`: the cloud link and set-up, moved from ai-robot with their history; later the app's link to the cloud, and the update channel's format (ai-robot ADR-0014);
   - their requirements;
   - the decisions that span repositories or bind every product, in `docs/decisions/`, from this one on.

   The protocols inside one product stay with it: the robot's screen and body protocols in ai-robot.

3. **Each repository pins `ai-platform` as a git submodule at `platform/`**, as PX4 and ArduPilot pin MAVLink.
   - A pin moves in the pull request that implements a change, never on its own.
   - Each protocol keeps its own version, which the two sides negotiate when they meet, as both protocols do already.
   - The commit that publishes a version is tagged `<protocol>/v<major>.<minor>`.

4. **Decisions live where they apply:**
   - here, what spans repositories;
   - in each repository, its own: ai-robot its hardware and software, ai-cloud its stack and its pipeline.

   The decisions made before this repository stay in ai-robot (ADR-0001 to ADR-0017), and the index here links them.

5. **The protocols speak of devices, and a robot is one kind of device.**
   - Their next major versions, cloud link 3.0 and set-up 2.0, rename what says "robot": `/robot/token` becomes `/device/token`, `robot-registration+jwt` becomes `device-registration+jwt`, and `robot` fields become `device`.
   - A device's `hello` says its kind and model.
   - What one kind of device needs, such as a robot's motion, stays a capability that it declares.
   - This lands before the cloud or the app implements anything.

6. **Every repository works the same way**:
   - `AGENTS.md`, `CLAUDE.md`, and a `CONTRIBUTING.md` with the same rules for branches, commits and pull requests;
   - the `review` checklist, and `adr` and `devlog`;
   - the MIT License.

## Alternatives considered

| Alternative | Why not |
|---|---|
| ADR-0003's names: `ai-robot-server`, `ai-robot-app`, and `ai-robot-protocol` | They tie the cloud, the app and the protocols to one product, while more are expected to share them. |
| An organization, with repositories named by role (Home Assistant) | It needs an organization's name before any product is named, and that name would be a brand. The owner has one account. The repositories can move to an organization later without touching code. |
| The shared protocols in ai-robot, which the other repositories pin | Every other repository would pull the robot's hardware, software and face to read two folders, and the protocols' versions would follow the robot's history. |
| Protocols here, decisions across repositories in ai-robot (this ADR's first draft) | The robot's repository would hold decisions about products that are not robots. The cloud's and the app's assistants would not have them in their pin. |
| A repository for decisions and another for protocols | Two shared repositories to pin and keep in step, for decisions and protocols that change together. |
| A mirror published from ai-robot (Envoy, Kubernetes) | It needs a mirroring bot. A change the cloud needs would still go through the robot's reviews. |
| A package per language (PyPI, npm, pub.dev) | One package to publish for each language, while the app's language is not chosen. The specifications are documents as much as schemas, and a submodule carries both. |
| One repository for everything | The cloud, the app and each device are built, deployed and released apart, with their own CI and permissions. |

## Consequences

- Positive:
  - one definition for every side, which the cloud and the app take without the robot's code;
  - a new product joins by pinning `ai-platform` and declaring its capabilities;
  - each protocol's history, versions and examples, and the decisions behind them, in one place;
  - the same conventions in every repository, for people and assistants alike.
- Negative / accepted trade-offs:
  - submodules must be cloned on purpose (`git clone --recurse-submodules`), and moved on purpose;
  - a protocol change takes two pull requests: the protocol first, then each side's;
  - decisions are split between this repository and each repository's own, by a rule that must be applied;
  - `ai-` is a generic prefix: the repositories group by it within the owner's account.
- Follow-up:
  - the owner creates `ai-cloud` and `ai-platform` on GitHub, public, and renames `AI-robot` to `ai-robot`;
  - this repository's history (the protocols, from ai-robot) is pushed, and tagged `cloud/v2.2` and `setup/v1.0`;
  - ai-robot replaces `protocol/cloud` and `protocol/setup` with the submodule at `platform/`. Its code, tests, CI and links follow, its design rule 1 changes, and ADR-0003 is marked superseded;
  - cloud link 3.0 and set-up 2.0, for devices (decision 5), here, then in ai-robot;
  - ai-cloud adds the submodule, then decides its stack.

## References

Retrieved 2026-10-28:

- PX4's [`.gitmodules`](https://github.com/PX4/PX4-Autopilot/blob/main/.gitmodules) and ArduPilot's [`.gitmodules`](https://github.com/ArduPilot/ardupilot/blob/master/.gitmodules), which pin MAVLink; [mavlink/mavlink](https://github.com/mavlink/mavlink).
- [envoyproxy/data-plane-api](https://github.com/envoyproxy/data-plane-api): "read only mirror" of Envoy's API definitions.
- [kubernetes/api](https://github.com/kubernetes/api), published from the `staging/` tree of [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes).
- [home-assistant/architecture](https://github.com/home-assistant/architecture), and the organization's [repositories](https://github.com/home-assistant).
- [project-chip/connectedhomeip](https://github.com/project-chip/connectedhomeip), Matter's repository.
- GitHub: [renaming a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository) and [transferring a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository) keep redirects.
