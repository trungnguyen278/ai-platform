# ai-platform

What the project's AI products share: the protocols between them, and the decisions that span them ([ADR-0001](docs/decisions/0001-repositories.md)). Every repository of the project pins this one, so that each of them reads the same definitions.

| Repository | What it is |
|---|---|
| [ai-robot](https://github.com/trungnguyen278/ai-robot) | The robot: a mobile robot with an expressive face, the first device |
| [ai-cloud](https://github.com/trungnguyen278/ai-cloud) | The cloud side: the devices' AI, their tokens, set-up's registration, updates |
| [ai-app](https://github.com/trungnguyen278/ai-app) | The owner's app: set-up, settings, remote control |
| ai-platform | This repository |

## Protocols

| Protocol | Between | Version | Decided in |
|---|---|---|---|
| [Cloud link](protocols/cloud/README.md) | A device and ai-cloud | 3.0 | [ADR-0006](docs/decisions/0006-two-channels.md); ai-robot ADR-0008, ADR-0009, ADR-0010, ADR-0012 |
| [Set-up](protocols/setup/README.md) | The owner's app, a device and ai-cloud | 2.0 | [ADR-0005](docs/decisions/0005-homes.md); ai-robot ADR-0015 |

Each protocol folder holds:
- `README.md`, the specification: messages, sequences, errors, limits, security;
- `schema.json`, every message as JSON Schema (draft 2020-12);
- `examples/`, whole exchanges, which every side tests against;
- `requirements.md`, where the protocol has requirements of its own.

The cloud link and set-up came from ai-robot's `protocol/`, with their history, on 2026-10-28. The protocols inside one product stay with it, such as the robot's screen and body protocols. Both speak of devices, the cloud link from its version 3.0 and set-up from its version 2.0 ([ADR-0001](docs/decisions/0001-repositories.md), decision 5).

## Decisions

[`docs/decisions/`](docs/decisions/README.md) holds every decision that spans repositories. A repository's own decisions stay in it. The decisions made before this repository existed are ai-robot's ADR-0001 to ADR-0017, which the index links.

## How the repositories use it

Each repository pins this one as a git submodule at `platform/`. A pin moves in the pull request that implements a change, never on its own. Clone with `git clone --recurse-submodules`, or run `git submodule update --init` after a plain clone.

## Versions

- Each protocol has its own version, *major.minor*, in its README and its schema's title.
  - A minor version adds what the other side may ignore.
  - A major version changes or removes something.
- The two sides of a link say their versions when they meet, and keep to what both support, so that a device and the cloud need not move together.
- The commit that publishes a version is tagged `<protocol>/v<major>.<minor>`, such as `cloud/v2.2`.
- How long the cloud keeps speaking each version, and why the update path never breaks: [ADR-0003](docs/decisions/0003-compatibility.md).

## Documentation

- [docs/](docs/README.md) — the decisions that span the repositories, and the dev log
- [CONTRIBUTING.md](CONTRIBUTING.md) — rules for protocols, branches, commits, licensing

## License

Released under the [MIT License](LICENSE).
