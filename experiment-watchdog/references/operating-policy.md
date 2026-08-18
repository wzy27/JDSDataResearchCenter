# Operating policy

## Safety invariants

- Create a unique job directory and refuse reuse.
- Use argv arrays; never interpolate a training command through a shell.
- Resolve explicit cwd, configuration, output boundaries, and credentials
  before launch.
- Require stable resource availability, then let the task perform a second
  project-specific check when allocation races are possible.
- Terminate the entire task process group on fatal logs, deadline, no progress,
  supervisor stop, or supervisor exception.
- Never automatically restart optimizer-bearing training. Resume only at a
  project-defined safe boundary after audit.
- Treat a zero process exit as provisional until output gates pass.

## Timeout calibration

Set startup timeout above the measured p99 cold load. Set no-progress timeout
above the longest legitimate kernel, collective, reward wait, or checkpoint
write. Prefer explicit heartbeat files for stages that normally produce no
stdout. Set a hard task deadline independently.

## Alert policy

Notify on state changes. Use sparse waiting reminders such as two and six hours.
Send immediate alerts for fatal logs, no progress, incomplete outputs, cleanup
failure, and terminal state. Do not send a periodic “healthy” alert unless the
user explicitly needs it.

## Known limits

- Whole-machine probes are conservative and do not reserve resources.
- Log mtime is only a proxy for business progress.
- tmux cannot survive machine loss; use an external dead-man monitor when host
  failure notification is required.
- The generic output gate checks existence/count/size, not model semantics.
