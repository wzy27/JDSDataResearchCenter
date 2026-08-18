# Idea ledger data contract

## Locations

- `ideas/records/IDEA-<hash>.json`: canonical machine-readable record.
- `ideas/notes/IDEA-<hash>.md`: Chinese human-facing rationale and review note.
- `ideas/index.json`: derived index rebuilt from canonical records.

`IDEA-*` is the first 12 uppercase hexadecimal characters of SHA-256 over `<project_id>|<normalized initial title>`. Renaming an idea does not change its ID. A same-title collision must be resolved by choosing a more specific initial title.

## Required semantics

- `statement`: the current concise proposition or design thesis.
- `kind`: `hypothesis`, `method`, `research-question`, `system-design`, `dataset`, or `analysis`.
- `status`: `proposed`, `active`, `testing`, `supported`, `challenged`, `superseded`, `rejected`, or `parked`.
- `motivation`: why the idea matters; blank is allowed only at initial capture.
- `assumptions`: conditions the idea depends on.
- `alternatives`: materially different options considered.
- `validation`: success criteria, failure signals, and linked experiment IDs.
- `evolution`: append-only events explaining creation and later changes.
- `provenance.sources`: paths/URLs, file hashes when available, anchors, and source roles.
- `traceability`: links to `LIT-*`, `EXP-*`, `CLAIM-*`, `TASK-*`, and supersession relationships.

## Evolution rules

Never delete or rewrite a meaningful earlier event. Append one of:

- `captured`: initial registration;
- `refined`: scope or formulation clarified without changing the core direction;
- `pivoted`: direction materially changed;
- `challenged`: evidence or implementation raised a substantive concern;
- `supported`: linked evidence increased confidence;
- `rejected`: the direction was intentionally abandoned;
- `superseded`: a new `IDEA-*` replaces this one.

`supported` is not equivalent to proven. Record the exact evidence scope and remaining uncertainty in the note.

## Field ownership

The JSON record is canonical for identity, lifecycle, evolution, and links. The Markdown note is curated narrative and must not be overwritten automatically after creation. `ideas/index.json` is derived and may be rebuilt.
