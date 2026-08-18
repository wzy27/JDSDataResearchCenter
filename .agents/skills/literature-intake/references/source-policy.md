# Source and access policy

## Preferred source order

1. Authorized Zotero/library connector for private library state, collections, tags, attachments, and existing notes.
2. DOI registry metadata from Crossref for DOI identity and publisher deposits.
3. arXiv API for arXiv-native records.
4. OpenAlex for OpenAlex IDs, PMID resolution, topics, and open-access discovery.
5. Publisher or repository landing page for manual verification.
6. General web search only to resolve an identifier or locate an authoritative source.

Record every automated retrieval in `provenance.retrievals`. Do not merge conflicting values invisibly; keep the selected value and add a review warning.

## Access boundaries

- Metadata availability does not grant rights to download or redistribute full text.
- Do not bypass authentication, paywalls, robots controls, or license restrictions.
- Prefer an open-access URL explicitly supplied by a registry or repository.
- Never commit API keys, cookies, access tokens, signed URLs, or private attachment URLs.
- Use only `CROSSREF_EMAIL` and `OPENALEX_API_KEY`; never scan `.env` or unrelated credential stores.

## Verification expectations

- Verify DOI resolution before marking a record `verified`.
- Compare title, authors, year, and venue against the paper or publisher page.
- Treat provider abstracts, citation counts, topics, and open-access flags as potentially stale or incomplete.
- Record retraction, correction, expression-of-concern, and version relationships when found; do not infer them from title similarity.

## Provider behavior

- Crossref: public metadata API; identify requests with `mailto` when available and back off on transient errors.
- arXiv: use the export API for stable arXiv identifiers and respect request-rate guidance.
- OpenAlex: require `OPENALEX_API_KEY`; singleton DOI/ID resolution is preferred over paid search operations.
- Zotero: use MCP or API only when the user has authorized access. Preserve Zotero item keys as external IDs, not as replacements for DOI/OpenAlex/arXiv identifiers.
