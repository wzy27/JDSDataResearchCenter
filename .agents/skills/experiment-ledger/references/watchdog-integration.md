# Experiment watchdog integration

Use the ledger as the source of experiment identity and the watchdog as the runtime supervisor.

## Mapping

| Ledger | Watchdog |
|---|---|
| `EXP-*` | unique policy/job name prefix |
| `execution.command_argv` | `command` |
| resolved connection cwd | `cwd` |
| accelerator requirement | `resource.provider` and custom probe |
| protocol time limits | progress/deadline policy |
| expected outputs | `outputs.required` plus semantic validator |
| watchdog event | append-only ledger event or external run pointer |

Map watchdog states as follows:

- `WAITING_FOR_RESOURCE` -> ledger `queued`
- `STARTING` or `RUNNING` -> ledger `running`
- `VERIFYING_OUTPUT` -> ledger `verifying`
- `COMPLETE` -> ledger `complete` only after semantic validation
- `FAILED` -> ledger `failed`
- `STOPPED` -> ledger `stopped`

Do not generate a watchdog policy while the ledger record is `planned` or `blocked`. Do not copy secrets from executor configuration into the policy or ledger.
