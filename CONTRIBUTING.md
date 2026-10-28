# Contributing

These conventions apply to everyone working in this repository — people and AI assistants alike. They match the other repositories', so that the project works the same way everywhere.

## Rules

1. **Defined once.** A protocol between repositories is defined here and nowhere else. The sides read the schemas from their pin of this repository, or generate from them; nobody copies a definition by hand.
2. **The specification, the schema and the examples change together**, in the same commit. Every example validates against its schema.
3. **Versions mean something.** A minor version only adds what the other side may ignore; anything else is a major version. A published version is never changed: a correction is a new version.
4. **Every side follows.** A change lands here first. Each side then implements it in a pull request that moves its pin, and tests against the examples. A protocol's README says which version each side implements.
5. **Devices, not one product.** The protocols serve any device of the project. What one kind of device needs, such as a robot's motion, it declares as capabilities, rather than the protocol assuming it ([ADR-0001](docs/decisions/0001-repositories.md)).
6. **Security is part of the protocol.** A change that touches identity, keys, tokens, or what leaves a device is checked against the requirements (`protocols/cloud/requirements.md`, §9), and says how it meets them.
7. **Build for the long run.** Choose the design that will last, even when it is more work: effort is no reason to settle for less. Do not build stopgaps meant to be replaced later. When the lasting choice is not clear yet, settle it first, with research, measurements or an ADR. Work may still land in steps, as long as each step belongs to the final design.

## Language

Everything in the repository — specifications, schemas, examples, decisions and commit messages — is written in English.

## Branches

- `main` must always be usable. Do not commit to it directly: work on a branch and merge through a pull request.
- Branch names follow `<type>/<short-description>`, e.g. `feat/turn-captions`, `fix/setup-error-codes`, `docs/adr-languages`.

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope>): <short summary in the imperative mood>`.

| Type | Use for |
|---|---|
| `feat` | A new message, field or behaviour: a new version |
| `fix` | A correction that changes what a side must do: a new version |
| `docs` | Decisions, wording, examples or notes that change nothing a side does |
| `chore` | Tooling, configuration, CI, housekeeping |

The scope is the protocol, `cloud` or `setup`, or `decisions`, `tools` and `ci`.

Example: `feat(cloud): let the cloud caption its answers`

Keep commit messages short:

- **The subject** says what changes, in under 72 characters.
- **A body** is optional: at most a few lines on *why*, with the ADR that decided it.
- **No inventories**, and **no review narratives**: those belong in the conversation or the dev log.

## Pull requests

- A pull request carries **exactly one commit**, written as a Conventional Commit. To change it, amend that commit (`git commit --amend`) and update the branch with `git push --force-with-lease`.
- Pull requests are merged with a merge commit, the only merge method enabled on GitHub.
- The description is short, following the template: what changes and why, how it was checked, and the checklist.
- After the merge, a new version is tagged `<protocol>/v<major>.<minor>` on the merge commit.

## Decisions and the dev log

- A decision that spans repositories → an ADR in `docs/decisions/` (`adr` checklist). Anything not explicitly agreed stays `Proposed`.
- End of a work session here → an entry in `docs/devlog/` (`devlog` checklist).

## Secrets

Examples hold made-up values only: keys generated for the example, codes and tokens that open nothing. A real key, token or password never appears here.

## Facts and sources

What a protocol or a decision relies on (an RFC, a Bluetooth specification, a platform's limit, a service's features) is cited, with the section, and dated where it may change.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
