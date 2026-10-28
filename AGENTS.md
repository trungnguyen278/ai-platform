# AGENTS.md

Guidance for AI coding assistants working in this repository. Read [README.md](README.md) for what it holds and [CONTRIBUTING.md](CONTRIBUTING.md) for the rules — they apply to assistants exactly as they do to people.

This repository holds what the project's repositories share: the protocols between them and the decisions that span them. Every change here reaches at least two of them: [ai-robot](https://github.com/trungnguyen278/ai-robot), [ai-cloud](https://github.com/trungnguyen278/ai-cloud) and, later, the app.

## How to work here

- Reply in the language the user writes in; everything committed to the repository is in English.
- Check the newest file in `docs/devlog/` to see where things stand, and add an entry when a work session ends.
- Never make a decision on someone's behalf:
  - record a decision that spans repositories as an ADR in `docs/decisions/`; a repository's own decisions stay in it;
  - leave anything that has not been explicitly agreed as `Proposed`.
- Build for the long run ([rule 7](CONTRIBUTING.md#rules)): propose the design that will last, even when it is bigger. "For now", "provisional" or "until X" in a proposal is a sign to settle the choice first.
- Never state what a standard, a library, a service or a platform allows from memory (an RFC, Bluetooth, JSON Schema, a phone's operating system, a speech service): look it up, cite it, and date it.
- Keep commit messages and pull request descriptions short, as [CONTRIBUTING.md](CONTRIBUTING.md#commits) says. Lists of files and what a review found go in the conversation or the dev log, never in git.
- Every value a protocol fixes (a version, a code, a size, a time) is written here once, named, and the code on each side refers to it.

## Task checklists

Each folder in `.claude/skills/` holds one step-by-step checklist in plain Markdown (`SKILL.md`); its header says when to use it. Follow `protocol-change` for any change to a protocol, `adr` and `devlog` for decisions and the dev log, and `review` before handing a pull request over.
