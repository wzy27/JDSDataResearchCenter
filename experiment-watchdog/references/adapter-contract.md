# Adapter contract

Use JSON configuration only. Keep credentials outside the policy file.

## Resource providers

- `auto`: Prefer `npu-smi`, then `nvidia-smi`; require the whole visible machine
  to have no accelerator compute processes.
- `ascend` or `nvidia`: Force the corresponding conservative whole-machine probe.
- `none`: Skip accelerator gating for CPU jobs.
- `custom`: Run `resource.probe_argv`. Exit zero means available; any nonzero
  exit means busy. Print a short human-readable reason to stdout.

Use a custom probe to integrate Slurm reservations, Kubernetes leases, shared
lock services, or per-device allocation. Make the probe read-only and bounded.

## Business progress

Treat task-log writes and `progress.heartbeat_globs` mtimes as progress. Add
`start_patterns` when process creation is not sufficient proof that ranks or
workers started. Set phase-specific thresholds from measured cold-start and
iteration distributions; do not copy a universal timeout blindly.

## Notification adapter

Set `notifier.argv` to an executable argv array. The watchdog writes one event
JSON object to stdin. The adapter must return zero only after the remote service
accepts the event. Store tokens in a protected local file or environment, never
in the policy, job directory, provenance, logs, or Skill.

Example event:

```json
{
  "schema_version": "experiment-watchdog.event/v1",
  "timestamp": "2026-08-04T10:00:00+0800",
  "event": "NO_PROGRESS",
  "detail": "business progress timeout",
  "name": "run-123",
  "state": "RUNNING",
  "job_dir": "/cache/jobs/run-123"
}
```

Recommended notification events are `WAITING_FOR_RESOURCE`,
`RESOURCE_WAIT_REMINDER`, `RESOURCE_ACQUIRED`, `RUN_STARTED`, `FATAL_LOG`,
`NO_PROGRESS`, `OUTPUT_INCOMPLETE`, `COMPLETE`, `FAILED`, and `STOPPED`.

## Output gates

Each `outputs.required` rule contains a cwd-relative `glob`, `min_count`, and
`min_size_bytes`. A zero exit code becomes `COMPLETE` only when every gate
passes. Use a project-side semantic validator command before the final marker
when shape, rank identity, checkpoint continuity, or metric contents matter.

## Persistence boundary

`launch` uses detached tmux. On managed platforms, call the private `_run`
subcommand from systemd, Slurm, Kubernetes, or the platform-native supervisor
instead. Keep exactly one supervisor per job directory.
