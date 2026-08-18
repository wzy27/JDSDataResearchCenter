---
name: idea-ledger
description: Create and maintain traceable research idea records, including hypotheses, method proposals, design decisions, alternatives, assumptions, validation criteria, evolution events, and links to literature, TODOs, experiments, and manuscript claims. Use when capturing a new research idea, converting a planning document into an idea history, recording a pivot or rejected alternative, reviewing why a method changed, or connecting implementation work back to its research rationale.
---

# Idea Ledger

Maintain the research rationale and its evolution. Do not use the ledger as a generic task tracker.

## Workflow

1. Read the target project's `project.yaml`, README, existing `ideas/`, and the supplied source material.
2. Read [references/data-contract.md](references/data-contract.md) before creating or changing canonical records.
3. Separate source facts, researcher statements, and agent synthesis. Preserve provenance for each captured idea.
4. Identify the smallest independently discussable idea. Prefer one falsifiable hypothesis, method choice, research question, or system-design thesis per record.
5. Run `scripts/idea_ledger.py create` to allocate a stable `IDEA-*` ID and create the record, note, and index.
6. Complete the Chinese note with motivation, alternatives, assumptions, validation criteria, and traceability links. Keep source quotations minimal.
7. Record a refinement, pivot, challenge, rejection, or supersession with `scripts/idea_ledger.py evolve`; never erase the prior rationale.
8. Run `scripts/idea_ledger.py validate` and project-specific checks before handoff.

## Idea versus TODO

Read [references/todo-policy.md](references/todo-policy.md) when the input contains a checklist, roadmap, issue list, or implementation plan.

- Store why a direction may work, what would falsify it, and how it changed as `IDEA-*`.
- Store concrete work to perform in a project `TODO.md` or connected task system.
- Link each research-relevant TODO back to one or more `IDEA-*` records.
- Do not create one idea per checkbox unless the checkbox itself introduces an independently testable research proposition.

Use [assets/todo-view.md](assets/todo-view.md) as the human-facing Chinese TODO structure.

## Commands

Create an idea:

```powershell
python .agents\skills\idea-ledger\scripts\idea_ledger.py create `
  --project-dir projects\<project-id> `
  --title "<title>" `
  --kind system-design `
  --statement "<concise thesis>" `
  --source "<path-or-url>" `
  --source-anchor "<section>"
```

Append an evolution event:

```powershell
python .agents\skills\idea-ledger\scripts\idea_ledger.py evolve `
  --project-dir projects\<project-id> `
  --idea-id IDEA-XXXXXXXXXXXX `
  --event-type refined `
  --summary "<what changed>" `
  --reason "<why>"
```

Validate:

```powershell
python .agents\skills\idea-ledger\scripts\idea_ledger.py validate `
  --project-dir projects\<project-id>
```

## Guardrails

- Do not claim an agent-generated synthesis was explicitly proposed by a researcher; label it as synthesis.
- Do not silently rewrite history. Append evolution events and use `superseded` links.
- Do not mark an idea `supported` from an abstract, plan, or unrun TODO.
- Do not use TODO completion as scientific validation; link the resulting `EXP-*` or evidence instead.
- Keep human-facing notes in Simplified Chinese while preserving code, identifiers, field names, and source titles.
