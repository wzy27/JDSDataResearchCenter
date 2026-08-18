# Experiment ledger data contract

## Locations

- `experiments/records/EXP-<hash>.json`: canonical experiment plan and lifecycle record.
- `experiments/notes/EXP-<hash>.md`: Chinese human-facing plan and interpretation.
- `experiments/preflight/<EXP-id>-<timestamp>.json`: persisted, non-launching environment checks.
- `experiments/index.json`: derived index.

`EXP-*` is the first 12 uppercase hexadecimal characters of SHA-256 over `<project_id>|<normalized initial title>`. Keep the ID after renaming.

## Lifecycle

`planned -> blocked | ready | cancelled`

`blocked -> ready | cancelled`

`ready -> queued | running | blocked | cancelled`

`queued -> running | failed | stopped`

`running -> verifying | failed | stopped`

`verifying -> complete | failed`

`failed -> ready | cancelled`

Do not skip from `planned` or `blocked` to `complete`. `complete` requires validated outputs and a recorded interpretation.

## Required content

- `objective`: the question or engineering gate being tested.
- `protocol`: experiment type, scope, success criteria, failure criteria, and expected outputs.
- `traceability`: linked `IDEA-*`, `TASK-*`, `LIT-*`, `CLAIM-*`, and parent experiments.
- `execution`: executor, argv command, connection-based cwd, required commands, and watchdog pointer.
- `code`: repository, immutable commit, dirty state, and patch pointer when relevant.
- `data`: dataset identifiers, versions, splits, and connection-based locations.
- `environment`: OS, runtime/container, packages or lockfile, and random seeds.
- `resources`: accelerator vendor/count/VRAM and host storage requirements.
- `blockers`: concrete unresolved conditions and how to clear them.
- `preflight`: report pointers and latest outcome.
- `results`: metrics, artifacts, conclusion, support direction, limitations, and reviewer.
- `events`: append-only lifecycle events.

## Evidence discipline

A process exit code is operational evidence, not a scientific conclusion. Only mark `complete` after semantic output gates pass. Record whether results `support`, `contradict`, `qualify`, or are merely `inconclusive` for each linked idea, with scope and limitations.

Keep large artifacts external and store URI, checksum, producer run, and validation result here.
