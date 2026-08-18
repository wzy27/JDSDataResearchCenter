---
name: literature-intake
description: Ingest research papers into a project evidence ledger with normalized identifiers, auditable metadata provenance, duplicate detection, and review-ready evidence cards. Use when adding papers from DOI, doi.org URL, arXiv ID/URL, OpenAlex work ID, or PMID; importing a reading list; recording literature discovered during research; or checking whether a paper is already registered. Do not use for writing a full literature review or downloading copyrighted full text.
---

# Literature Intake

Convert each paper into a stable machine-readable record and a human review card. Treat intake as metadata registration, not as proof that the paper supports a claim.

## Workflow

1. Resolve the target project directory before writing. Ask only when it cannot be inferred from `projects/<project-id>` or the user's request.
2. Read `references/source-policy.md` when choosing among Zotero, DOI, arXiv, OpenAlex, PMID, or a generic URL.
3. Inspect `<project>/literature/index.json` and existing records before adding a paper.
4. Prefer an authorized Zotero connector for papers already in the user's library. Otherwise use the bundled script for supported stable identifiers.
5. Run:

   ```bash
   python .agents/skills/literature-intake/scripts/literature_intake.py --project-dir <project-dir> <identifier> [<identifier> ...]
   ```

   Useful options:

   - `--dry-run`: resolve and normalize without writing.
   - `--update`: refresh metadata while preserving curated review fields and existing notes.
   - `--mailto`: identify polite Crossref/arXiv requests; otherwise use `CROSSREF_EMAIL` when set.
   - `--openalex-api-key`: authorize OpenAlex; otherwise use `OPENALEX_API_KEY` when set.
   - `--json`: emit a machine-readable result summary.

6. Open the generated `literature/notes/LIT-*.md`. Fill evidence, methods, limitations, and traceability only from material actually inspected. Mark whether notes come from metadata, abstract, or full text.
7. Report created, updated, duplicate, and unresolved inputs separately. Never silently choose an ambiguous title match.

## Identifier routing

- DOI or `doi.org` URL: retrieve publisher-deposited metadata from Crossref.
- arXiv ID or URL: retrieve the arXiv Atom record.
- OpenAlex `W...` ID or PMID: retrieve the OpenAlex work; require an API key.
- Generic publisher/project URL: first resolve a DOI, arXiv ID, OpenAlex ID, or PMID with web search or an authorized literature connector. Do not scrape arbitrary pages in the script.
- Title only: search interactively, present candidates, and obtain a stable identifier before intake. Do not auto-select the first search result.

## Integrity rules

- Never invent or repair an identifier by guessing.
- Keep provider metadata and researcher interpretation separate.
- Treat citation counts and source prestige as context, not evidence quality.
- Do not claim full-text review when only metadata or an abstract was inspected.
- Do not download or commit PDFs automatically. Store lawful links and licenses when providers expose them.
- Never read `.env` files. Read only the explicit environment variables named above.
- Preserve manual review content on metadata refresh.
- Link evidence cards to project IDs such as `IDEA-*`, `EXP-*`, `CLAIM-*`, `FIG-*`, and `TABLE-*`; do not create links without a real target.

## Data contract

Read `references/data-contract.md` before changing record fields, statuses, deduplication, or update behavior. Validate records against `assets/literature-record.schema.json` when adding CI checks or integrations.

Use `assets/evidence-card.md` as the output note template. The script renders it automatically for new records and never overwrites a curated note.

## Extending sources

Read `references/upstream-patterns.md` before adding another provider or vendoring third-party code. Add a provider adapter that returns the existing normalized metadata shape, record provenance, implement retry/backoff, and add fixture-based tests. Keep optional provider credentials explicit and narrowly scoped.
