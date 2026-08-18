# Upstream patterns

This skill reimplements a narrow intake workflow; it does not vendor upstream source code.

- K-Dense Scientific Agent Skills (`literature-review`, `citation-management`, `paper-lookup`, `pyzotero`): use stable identifiers, query authoritative databases, deduplicate results, verify citations, and separate scripts/references/assets. Review each upstream skill and its license before copying code: https://github.com/K-Dense-AI/scientific-agent-skills
- PaperQA2: retain document provenance and grounded citations when later building local-paper retrieval: https://github.com/Future-House/paper-qa
- Zotero MCP: expose authorized library search and item retrieval as external tools rather than embedding private library data in prompts: https://github.com/kujenga/zotero-mcp
- OpenAlex API: use external-ID singleton lookups, explicit API keys, timeouts, and exponential backoff: https://developers.openalex.org/api-reference/introduction
- Crossref REST API: use DOI singleton lookups, a descriptive User-Agent, optional `mailto`, caching, and backoff: https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/

When extending the skill, prefer adapters around these systems over replacing the canonical record contract.
