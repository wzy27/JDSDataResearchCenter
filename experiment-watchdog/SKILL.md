---
name: experiment-watchdog
description: Safely launch, queue, supervise, alert on, stop, and verify long-running accelerator or distributed experiments with business-progress heartbeats, resource gating, fatal-log detection, process-group cleanup, deadlines, and output gates. Use for NPU/GPU jobs, profiling, training, rollout, evaluation, reward-service workflows, jobs waiting for cards, stale-but-alive processes, or requests to make experiment execution persistent and observable across machines.
---

# Experiment Watchdog

Use the bundled standard-library supervisor to turn process liveness into an
auditable experiment state machine. Keep project-specific semantics in a small
JSON policy or adapter; do not duplicate the supervisor into the project.

## Workflow

1. Read the repository's `AGENTS.md` and existing execution policy. Respect a
   mandated platform launcher. Use this watchdog inside that launcher rather
   than creating a competing detached job.
2. Run `python scripts/watchdog.py doctor`. Pass `--tmux /absolute/path/tmux`
   when tmux is installed outside `PATH`. For Slurm, Kubernetes, systemd, or an
   existing persistent supervisor, run `scripts/watchdog.py _run --job-dir ...`
   under that manager instead of using `launch`.
3. Copy `assets/policy-template.json` to the experiment plan directory. Replace
   every placeholder and use absolute paths for cwd, configs, outputs, and
   adapter executables.
4. Read `references/adapter-contract.md` when selecting a resource probe,
   heartbeat, notifier, or output gate. Read `references/operating-policy.md`
   when setting timeouts, retry behavior, or alert policy.
5. Validate before launch:

   ```bash
   python scripts/watchdog.py validate /absolute/path/policy.json
   ```

6. Confirm that the job directory does not exist, the output/S3 boundary is
   unique, required queues and credentials are usable, and the exact launch
   command is recorded in the experiment plan.
7. Launch through tmux only when repository policy permits it:

   ```bash
   python scripts/watchdog.py launch \
     --config /absolute/path/policy.json \
     --job-dir /absolute/new/job-directory
   ```

8. Immediately inspect `status`, then inspect it again after at least one poll
   interval. Verify the supervisor, tmux session, expected phase, events, and
   notification audit. Do not describe a queued task as an active run.
9. Use `status` for observation and `stop` for explicit termination:

   ```bash
   python scripts/watchdog.py status --job-dir /absolute/job-directory
   python scripts/watchdog.py stop --job-dir /absolute/job-directory
   ```

10. Declare success only for `COMPLETE` after project output gates pass. Treat
    `FAILED`, `STOPPED`, missing outputs, stale progress, or cleanup warnings as
    distinct outcomes.

## Required policy decisions

- Prefer explicit business heartbeats over stdout mtime for long silent stages.
- Calibrate startup, no-progress, and hard deadlines independently.
- Use a custom resource probe when whole-machine emptiness is too conservative
  or allocation races require scheduler reservations.
- Pass notifier events through argv adapters and stdin JSON. Keep tokens in
  protected machine-local files or environment; never store them in the Skill,
  policy, provenance, or logs.
- Keep automatic retry disabled for optimizer-bearing training. Resume only at
  an audited, project-defined safe boundary.
- Require semantic project validation before writing a final completion marker
  when file existence and size are insufficient.

## State interpretation

`WAITING_FOR_RESOURCE` means queued without accelerator use. `STARTING` means
resources were acquired but the project start marker is not yet verified.
`RUNNING` means business work started. `VERIFYING_OUTPUT` is provisional.
Only `COMPLETE`, `FAILED`, and `STOPPED` are normal terminal states.

The supervisor emits state-change events plus `RESOURCE_WAIT_REMINDER`,
`FATAL_LOG`, `NO_PROGRESS`, `CLEANUP_FAILED`, and `OUTPUT_INCOMPLETE`. Configure
the notifier adapter to deliver only the events useful to the operator.
