# TODO separation policy

## Classification

Classify each source item before importing it:

| Source item | Destination |
|---|---|
| Testable proposition or method rationale | `IDEA-*` |
| Concrete implementation, inspection, or coordination action | `TASK-*` in project `TODO.md` |
| Executed run with configuration and result | `EXP-*` |
| Stable factual source | `LIT-*` or provenance link |
| Manuscript assertion | `CLAIM-*` |

One source document may produce a few ideas and many TODOs. This is expected.

## TODO requirements

Each research-relevant task should include:

- stable `TASK-*` ID;
- status: `待处理`, `进行中`, `阻塞`, `完成`, or `放弃`;
- milestone and priority;
- one actionable sentence;
- acceptance evidence, not only an activity description;
- linked `IDEA-*` and, after execution, linked `EXP-*` or artifact;
- dependencies and blocker when applicable;
- source section or issue URL.

Generate `TASK-*` as the first 10 uppercase hexadecimal characters of SHA-256 over `<project_id>|<normalized initial task text>`. Keep the ID after wording changes.

## Checklist migration

1. Preserve the original checklist as provenance; do not imply unchecked items were newly proposed by the agent.
2. Merge duplicates that share the same deliverable and acceptance evidence.
3. Group tasks by real dependency order, not merely document order.
4. Add explicit gates: a downstream milestone starts only when the upstream evidence exists.
5. Link each task to the idea it operationalizes. Use a project-level idea only when a more specific idea does not exist.
6. A checked box means work was performed, not that a research hypothesis was supported.
