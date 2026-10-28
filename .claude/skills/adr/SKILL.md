---
name: adr
description: Record a decision that spans the project's repositories as an ADR (Architecture Decision Record) in docs/decisions/ — a protocol's design, identity and security, languages, how work is split between devices, the cloud and the app, the repositories themselves — or when the user asks to write down such a decision or to explain why it was chosen.
---

# Recording a decision (ADR)

1. Decide where it belongs:
   - it spans repositories, or binds every product (a protocol, identity, languages): here, in `docs/decisions/`;
   - it stays inside one repository (the robot's hardware, the cloud's stack): in that repository's `docs/decisions/`.
2. Read `docs/decisions/README.md` to get the next number and check for related ADRs, here and in the earlier ones it lists.
3. Copy `docs/decisions/0000-template.md` to `docs/decisions/NNNN-short-title.md` (four digits, kebab-case).
4. Fill in Context → Decision → Alternatives considered (with why each was rejected) → Consequences (positive and negative) → References. Keep it short; include numbers and sources where available, dated.
5. Status: `Proposed` while under discussion, `Accepted` only once the people responsible for the decision have explicitly agreed. Never accept a decision on your own.
6. To change an earlier decision, **do not rewrite the old ADR**: set its status to `Superseded by NNNN` and write a new one. An earlier decision in another repository gets `Superseded by ai-platform ADR-NNNN`.
7. Add a row to the table in `docs/decisions/README.md`.
8. Commit with the scope `decisions`, e.g. `docs(decisions): add ADR-0003 on devices`.
