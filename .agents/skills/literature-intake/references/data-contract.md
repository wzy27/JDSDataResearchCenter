# Literature data contract

## Record locations

- `literature/records/LIT-<hash>.json`: canonical machine-readable record.
- `literature/notes/LIT-<hash>.md`: researcher-authored evidence card.
- `literature/index.json`: derived index rebuilt from canonical records.

`LIT-*` is the first 12 uppercase hexadecimal characters of SHA-256 over the strongest canonical identity: DOI, OpenAlex ID, arXiv ID, PMID, then normalized title plus year. The same paper therefore receives the same ID across projects when the canonical identifier is unchanged.

## Field ownership

- `bibliographic`, `external_ids`, `access`, and `provenance`: provider-derived. Refresh with `--update`.
- `review` and `traceability`: researcher/agent curated. Preserve on metadata refresh.
- `status`: workflow state. Preserve on metadata refresh.
- Markdown evidence card: curated narrative. Never overwrite automatically.

## Status lifecycle

`needs-review` -> `screened` -> `read` -> `verified`

- `needs-review`: metadata registered; identity or relevance still needs inspection.
- `screened`: title/abstract inspected and relevance decision recorded.
- `read`: full text inspected with evidence locations and limitations.
- `verified`: identifiers, bibliographic metadata, evidence notes, and traceability links independently checked.

Use `excluded` for an intentionally rejected work and record the reason. Do not delete it merely because it is irrelevant; the exclusion prevents repeated rediscovery.

## Duplicate policy

Match in this order:

1. DOI
2. OpenAlex ID
3. arXiv ID
4. PMID
5. normalized title plus publication year

An existing match is a duplicate, not a new record. `--update` refreshes provider-owned fields while retaining curated content and `created_at`.

## Evidence discipline

Each substantive evidence note should include:

- the claim in the researcher's own words;
- source location (page, section, figure, table, or supplement);
- support direction (`supports`, `contradicts`, `qualifies`, `background`);
- scope and population/dataset;
- uncertainty or limitation;
- related `IDEA-*`, `EXP-*`, or manuscript `CLAIM-*` identifiers.

Abstract-only notes must remain labeled as abstract-only. Metadata-provider abstracts can be incomplete or copyrighted; keep only what is necessary for local research use and never republish them automatically.
