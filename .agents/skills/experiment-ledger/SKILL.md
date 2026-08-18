---
name: experiment-ledger
description: Create and maintain traceable research experiment plans and results, including objectives, linked ideas and tasks, code/data/environment provenance, resource requirements, blockers, preflight reports, execution state, metrics, artifacts, and scientific interpretation. Use when planning a smoke test, training or evaluation run; checking whether an executor is ready; documenting why an experiment is blocked; transitioning a run through its lifecycle; or connecting experiment evidence to ideas and manuscript claims.
---

# Experiment Ledger

Keep the canonical experiment definition and scientific interpretation in ResearchCenter. Keep large logs, metrics, checkpoints, and datasets in their execution or artifact systems.

## Workflow

1. Read the project, linked `IDEA-*`, relevant `TASK-*`, code-repository instructions, and available executor policy.
2. Read [references/data-contract.md](references/data-contract.md) before creating or editing records.
3. Separate four stages: contract test, preflight, smoke test, and full run. Never report one stage as another.
4. Create a JSON spec from [assets/experiment-spec.example.json](assets/experiment-spec.example.json), then run `scripts/experiment_ledger.py create`.
5. Keep unresolved code commits, data versions, commands, and resource requirements explicitly `null` or blocked. Never guess them.
6. Read [references/executor-contract.md](references/executor-contract.md) before running preflight. Keep executor mappings and credentials in ignored machine-local config.
7. Run preflight without launching the experiment. Inspect every failed check and persist the report only when it is useful audit evidence.
8. Transition to `ready` only after required blockers are cleared and the exact command, code commit, data version, executor, and output boundary are resolved.
9. Read [references/watchdog-integration.md](references/watchdog-integration.md) before queueing or monitoring a long-running job.
10. Record results and interpretation after output validation. Task completion or process exit alone is not scientific support.
11. Run `validate` before handoff.

## Commands

Create from a spec:

```powershell
python .agents\skills\experiment-ledger\scripts\experiment_ledger.py create `
  --project-dir projects\<project-id> `
  --spec path\to\experiment-spec.json
```

Run a non-launching preflight:

```powershell
python .agents\skills\experiment-ledger\scripts\experiment_ledger.py preflight `
  --project-dir projects\<project-id> `
  --experiment-id EXP-XXXXXXXXXXXX `
  --executor .researchcenter.local.json `
  --write-report
```

Transition state:

```powershell
python .agents\skills\experiment-ledger\scripts\experiment_ledger.py transition `
  --project-dir projects\<project-id> `
  --experiment-id EXP-XXXXXXXXXXXX `
  --status ready `
  --reason "All required preflight checks passed."
```

Validate:

```powershell
python .agents\skills\experiment-ledger\scripts\experiment_ledger.py validate `
  --project-dir projects\<project-id>
```

## Safety

- Treat preflight as read-only. It may inspect commands, paths, OS, and accelerator availability; it must not launch research code.
- Require explicit user authority before starting, stopping, retrying, allocating, or deleting a remote job.
- Use argv arrays, exact working directories, unique output boundaries, and immutable code/data identifiers.
- Keep secrets, host credentials, signed URLs, and private attachment URLs out of records and reports.
- Keep human-facing notes in Simplified Chinese while preserving commands, identifiers, field names, and source metadata.
