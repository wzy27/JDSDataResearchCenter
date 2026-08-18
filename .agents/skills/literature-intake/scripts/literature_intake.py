#!/usr/bin/env python3
"""Create auditable literature records from stable scholarly identifiers."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


VERSION = "0.1.0"
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
OPENALEX_RE = re.compile(r"^(?:https?://openalex\.org/)?(W\d+)$", re.IGNORECASE)
PMID_RE = re.compile(r"^(?:pmid\s*:\s*|https?://pubmed\.ncbi\.nlm\.nih\.gov/)(\d+)/?$", re.IGNORECASE)
ARXIV_RE = re.compile(
    r"^(?:arxiv\s*:\s*|https?://arxiv\.org/(?:abs|pdf)/)?"
    r"([a-z][a-z.\-]+/\d{7}|\d{4}\.\d{4,5})(v\d+)?(?:\.pdf)?$",
    re.IGNORECASE,
)
TRANSIENT_HTTP_CODES = {403, 429, 500, 502, 503, 504}


class IntakeError(RuntimeError):
    """Raised for an actionable intake failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value)))
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text or None


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def normalize_doi(value: str) -> str | None:
    candidate = value.strip()
    parsed = urllib.parse.urlparse(candidate)
    if parsed.netloc.casefold() in {"doi.org", "dx.doi.org", "www.doi.org"}:
        candidate = urllib.parse.unquote(parsed.path.lstrip("/"))
    candidate = re.sub(r"^(?:doi\s*:\s*)", "", candidate, flags=re.IGNORECASE)
    match = DOI_RE.search(candidate)
    if not match:
        return None
    return urllib.parse.unquote(match.group(0)).rstrip(".,;").casefold()


def normalize_identifier(value: str) -> dict[str, str]:
    raw = value.strip()
    doi = normalize_doi(raw)
    if doi:
        return {"kind": "doi", "value": doi, "input": value}

    match = OPENALEX_RE.fullmatch(raw)
    if match:
        return {"kind": "openalex", "value": match.group(1).upper(), "input": value}

    match = PMID_RE.fullmatch(raw)
    if match:
        return {"kind": "pmid", "value": match.group(1), "input": value}

    match = ARXIV_RE.fullmatch(raw)
    if match:
        version = (match.group(2) or "").casefold()
        return {"kind": "arxiv", "value": match.group(1).casefold() + version, "input": value}

    if raw.startswith(("http://", "https://")):
        raise IntakeError(
            "Generic URL has no supported stable identifier. Resolve a DOI, arXiv ID, "
            "OpenAlex work ID, or PMID before intake."
        )
    raise IntakeError(
        "Unsupported identifier. Supply a DOI, doi.org URL, arXiv ID/URL, OpenAlex W ID, or PMID."
    )


def request_bytes(
    base_url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    attempts: int = 4,
    timeout: int = 30,
) -> tuple[bytes, str]:
    query = urllib.parse.urlencode(params or {})
    url = base_url + (("&" if "?" in base_url else "?") + query if query else "")
    request = urllib.request.Request(url, headers=headers or {})
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.geturl()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in TRANSIENT_HTTP_CODES or attempt == attempts - 1:
                if exc.code == 404:
                    raise IntakeError(f"No scholarly record found at {base_url}") from exc
                raise IntakeError(f"Provider request failed with HTTP {exc.code}: {base_url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
        time.sleep(2**attempt)

    raise IntakeError(f"Provider request failed after {attempts} attempts: {base_url}: {last_error}")


def request_json(
    base_url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], str]:
    body, final_url = request_bytes(base_url, params=params, headers=headers)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeError(f"Provider returned invalid JSON: {final_url}") from exc
    if not isinstance(payload, dict):
        raise IntakeError(f"Provider returned an unexpected JSON shape: {final_url}")
    return payload, final_url


def first_date_parts(message: dict[str, Any]) -> list[int]:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = message.get(key, {}).get("date-parts", []) if isinstance(message.get(key), dict) else []
        if parts and isinstance(parts[0], list):
            return [int(part) for part in parts[0] if isinstance(part, int)]
    return []


def normalize_crossref(message: dict[str, Any], retrieved_url: str) -> dict[str, Any]:
    title_values = message.get("title") or []
    title = clean_text(title_values[0] if title_values else None)
    if not title:
        raise IntakeError("Crossref record is missing a title.")

    authors = []
    for item in message.get("author") or []:
        if not isinstance(item, dict):
            continue
        name = clean_text(" ".join(part for part in (item.get("given"), item.get("family")) if part))
        authors.append(
            {
                "name": name or "Unknown",
                "orcid": (item.get("ORCID") or "").replace("https://orcid.org/", "") or None,
            }
        )

    date_parts = first_date_parts(message)
    container = message.get("container-title") or []
    doi = normalize_doi(str(message.get("DOI") or ""))
    links = [item.get("URL") for item in (message.get("link") or []) if isinstance(item, dict) and item.get("URL")]
    licenses = [item.get("URL") for item in (message.get("license") or []) if isinstance(item, dict) and item.get("URL")]
    canonical_url = message.get("URL") or (f"https://doi.org/{doi}" if doi else None)

    return {
        "bibliographic": {
            "title": title,
            "authors": authors,
            "year": date_parts[0] if date_parts else None,
            "publication_date": "-".join(str(part) for part in date_parts) if date_parts else None,
            "venue": clean_text(container[0] if container else None),
            "publisher": clean_text(message.get("publisher")),
            "type": message.get("type"),
            "language": message.get("language"),
            "abstract": clean_text(message.get("abstract")),
            "topics": sorted({clean_text(v) for v in (message.get("subject") or []) if clean_text(v)}),
            "citation_count": message.get("is-referenced-by-count"),
        },
        "external_ids": {"doi": doi, "openalex": None, "arxiv": None, "pmid": None, "zotero": None},
        "access": {
            "canonical_url": canonical_url,
            "open_access_url": None,
            "fulltext_urls": links,
            "license_urls": licenses,
        },
        "provider": "crossref",
        "retrieved_url": retrieved_url,
    }


def reconstruct_openalex_abstract(inverted: Any) -> str | None:
    if not isinstance(inverted, dict) or not inverted:
        return None
    positions: dict[int, str] = {}
    for word, indexes in inverted.items():
        if not isinstance(indexes, list):
            continue
        for index in indexes:
            if isinstance(index, int) and index >= 0:
                positions[index] = str(word)
    return " ".join(positions[index] for index in sorted(positions)) or None


def normalize_openalex(work: dict[str, Any], retrieved_url: str) -> dict[str, Any]:
    title = clean_text(work.get("display_name") or work.get("title"))
    if not title:
        raise IntakeError("OpenAlex record is missing a title.")

    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        author_id = (author.get("id") or "").rsplit("/", 1)[-1] or None
        authors.append(
            {
                "name": clean_text(author.get("display_name")) or "Unknown",
                "openalex_id": author_id,
                "orcid": (author.get("orcid") or "").replace("https://orcid.org/", "") or None,
            }
        )

    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    ids = work.get("ids") or {}
    openalex_id = (work.get("id") or ids.get("openalex") or "").rsplit("/", 1)[-1] or None
    doi = normalize_doi(str(work.get("doi") or ids.get("doi") or ""))
    topics = []
    for topic in work.get("topics") or []:
        name = clean_text(topic.get("display_name") if isinstance(topic, dict) else None)
        if name and name not in topics:
            topics.append(name)

    best_oa = work.get("best_oa_location") or {}
    oa = work.get("open_access") or {}
    canonical_url = primary.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else work.get("id"))
    open_access_url = best_oa.get("pdf_url") or best_oa.get("landing_page_url") or oa.get("oa_url")

    return {
        "bibliographic": {
            "title": title,
            "authors": authors,
            "year": work.get("publication_year"),
            "publication_date": work.get("publication_date"),
            "venue": clean_text(source.get("display_name")),
            "publisher": None,
            "type": work.get("type"),
            "language": work.get("language"),
            "abstract": reconstruct_openalex_abstract(work.get("abstract_inverted_index")),
            "topics": topics[:10],
            "citation_count": work.get("cited_by_count"),
        },
        "external_ids": {
            "doi": doi,
            "openalex": openalex_id,
            "arxiv": None,
            "pmid": str(ids.get("pmid") or "").rsplit("/", 1)[-1] or None,
            "zotero": None,
        },
        "access": {
            "canonical_url": canonical_url,
            "open_access_url": open_access_url,
            "fulltext_urls": [open_access_url] if open_access_url else [],
            "license_urls": [best_oa.get("license")] if best_oa.get("license") else [],
        },
        "provider": "openalex",
        "retrieved_url": retrieved_url,
    }


def atom_text(element: ET.Element | None) -> str | None:
    return clean_text(element.text if element is not None else None)


def normalize_arxiv(xml_body: bytes, arxiv_id: str, retrieved_url: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as exc:
        raise IntakeError("arXiv returned invalid Atom XML.") from exc
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise IntakeError(f"No arXiv record found for {arxiv_id}.")
    title = atom_text(entry.find("atom:title", ns))
    if not title:
        raise IntakeError("arXiv record is missing a title.")
    authors = []
    for author in entry.findall("atom:author", ns):
        authors.append({"name": atom_text(author.find("atom:name", ns)) or "Unknown", "orcid": None})
    published = atom_text(entry.find("atom:published", ns))
    doi = normalize_doi(atom_text(entry.find("arxiv:doi", ns)) or "")
    links = [item.attrib.get("href") for item in entry.findall("atom:link", ns) if item.attrib.get("href")]
    categories = sorted({item.attrib.get("term") for item in entry.findall("atom:category", ns) if item.attrib.get("term")})
    canonical_url = f"https://arxiv.org/abs/{arxiv_id}"
    pdf_url = next((url for url in links if "/pdf/" in url), None)

    return {
        "bibliographic": {
            "title": title,
            "authors": authors,
            "year": int(published[:4]) if published and published[:4].isdigit() else None,
            "publication_date": published,
            "venue": atom_text(entry.find("arxiv:journal_ref", ns)) or "arXiv",
            "publisher": "arXiv",
            "type": "preprint",
            "language": None,
            "abstract": atom_text(entry.find("atom:summary", ns)),
            "topics": categories,
            "citation_count": None,
        },
        "external_ids": {"doi": doi, "openalex": None, "arxiv": arxiv_id, "pmid": None, "zotero": None},
        "access": {
            "canonical_url": canonical_url,
            "open_access_url": pdf_url or canonical_url,
            "fulltext_urls": [pdf_url] if pdf_url else [],
            "license_urls": [],
        },
        "provider": "arxiv",
        "retrieved_url": retrieved_url,
    }


def fetch_metadata(identifier: dict[str, str], *, mailto: str | None, openalex_api_key: str | None) -> dict[str, Any]:
    kind = identifier["kind"]
    value = identifier["value"]
    user_agent = f"ResearchCenter-LiteratureIntake/{VERSION}"
    if mailto:
        user_agent += f" (mailto:{mailto})"

    if kind == "doi":
        encoded_doi = urllib.parse.quote(value, safe="/():;<>-")
        payload, retrieved_url = request_json(
            f"https://api.crossref.org/works/{encoded_doi}",
            params={"mailto": mailto} if mailto else None,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )
        message = payload.get("message")
        if not isinstance(message, dict):
            raise IntakeError("Crossref returned an unexpected record shape.")
        return normalize_crossref(message, retrieved_url)

    if kind == "arxiv":
        body, retrieved_url = request_bytes(
            "https://export.arxiv.org/api/query",
            params={"id_list": value},
            headers={"User-Agent": user_agent, "Accept": "application/atom+xml"},
        )
        return normalize_arxiv(body, value, retrieved_url)

    if kind in {"openalex", "pmid"}:
        if not openalex_api_key:
            raise IntakeError(
                f"{kind} lookup requires OPENALEX_API_KEY or --openalex-api-key. "
                "Obtain a free key from https://openalex.org/settings/api"
            )
        external_id = value if kind == "openalex" else f"pmid:{value}"
        encoded_id = urllib.parse.quote(external_id, safe=":")
        payload, retrieved_url = request_json(
            f"https://api.openalex.org/works/{encoded_id}",
            params={"api_key": openalex_api_key},
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )
        return normalize_openalex(payload, retrieved_url)

    raise IntakeError(f"No provider adapter for identifier kind: {kind}")


def canonical_key(metadata: dict[str, Any]) -> str:
    ids = metadata["external_ids"]
    for key in ("doi", "openalex", "arxiv", "pmid"):
        if ids.get(key):
            return f"{key}:{str(ids[key]).casefold()}"
    bib = metadata["bibliographic"]
    return f"title-year:{normalize_title(bib.get('title'))}:{bib.get('year') or ''}"


def build_record(metadata: dict[str, Any], *, project_id: str, input_value: str, now: str | None = None) -> dict[str, Any]:
    timestamp = now or utc_now()
    identity = canonical_key(metadata)
    record_id = "LIT-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12].upper()
    bib = metadata["bibliographic"]
    missing = [field for field in ("title", "authors", "year", "venue") if not bib.get(field)]
    return {
        "schema_version": 1,
        "record_id": record_id,
        "project_id": project_id,
        "status": "needs-review",
        "bibliographic": bib,
        "external_ids": metadata["external_ids"],
        "access": metadata["access"],
        "provenance": {
            "input": input_value,
            "canonical_identity": identity,
            "retrievals": [
                {
                    "source": metadata["provider"],
                    "url": metadata["retrieved_url"],
                    "retrieved_at": timestamp,
                }
            ],
            "review_warnings": ([f"Missing provider metadata: {', '.join(missing)}"] if missing else []),
        },
        "review": {
            "relevance": "unreviewed",
            "source_inspected": "metadata-only",
            "key_findings": [],
            "methods": [],
            "limitations": [],
            "reviewed_by": None,
            "reviewed_at": None,
        },
        "traceability": {
            "idea_ids": [],
            "experiment_ids": [],
            "claim_ids": [],
            "figure_ids": [],
            "table_ids": [],
        },
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def duplicate_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_ids = left.get("external_ids") or {}
    right_ids = right.get("external_ids") or {}
    for key in ("doi", "openalex", "arxiv", "pmid"):
        if left_ids.get(key) and right_ids.get(key) and str(left_ids[key]).casefold() == str(right_ids[key]).casefold():
            return True
    left_bib = left.get("bibliographic") or {}
    right_bib = right.get("bibliographic") or {}
    return bool(
        normalize_title(left_bib.get("title"))
        and normalize_title(left_bib.get("title")) == normalize_title(right_bib.get("title"))
        and left_bib.get("year") == right_bib.get("year")
    )


def load_records(records_dir: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    if not records_dir.exists():
        return []
    records = []
    for path in sorted(records_dir.glob("LIT-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntakeError(f"Cannot read existing record {path}: {exc}") from exc
        if isinstance(payload, dict):
            records.append((path, payload))
    return records


def find_duplicate(records_dir: Path, record: dict[str, Any]) -> tuple[Path, dict[str, Any]] | None:
    for path, existing in load_records(records_dir):
        if duplicate_match(existing, record):
            return path, existing
    return None


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def render_evidence_card(record: dict[str, Any], template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    bib = record["bibliographic"]
    ids = record["external_ids"]
    authors = ", ".join(author.get("name", "Unknown") for author in bib.get("authors") or []) or "Unknown"
    retrieval = record["provenance"]["retrievals"][-1]
    replacements = {
        "{{RECORD_ID}}": record["record_id"],
        "{{DOI}}": ids.get("doi") or "",
        "{{OPENALEX_ID}}": ids.get("openalex") or "",
        "{{ARXIV_ID}}": ids.get("arxiv") or "",
        "{{PMID}}": ids.get("pmid") or "",
        "{{TITLE}}": bib.get("title") or "Untitled work",
        "{{SOURCE}}": retrieval["source"],
        "{{RETRIEVED_AT}}": retrieval["retrieved_at"],
        "{{AUTHORS}}": authors,
        "{{YEAR}}": str(bib.get("year") or "Unknown"),
        "{{VENUE}}": bib.get("venue") or "Unknown",
        "{{URL}}": record["access"].get("canonical_url") or "Unknown",
    }
    for marker, value in replacements.items():
        template = template.replace(marker, str(value))
    return template


def merge_update(existing: dict[str, Any], refreshed: dict[str, Any]) -> dict[str, Any]:
    merged = refreshed
    merged["record_id"] = existing.get("record_id", refreshed["record_id"])
    merged["created_at"] = existing.get("created_at", refreshed["created_at"])
    merged["status"] = existing.get("status", refreshed["status"])
    merged["review"] = existing.get("review", refreshed["review"])
    merged["traceability"] = existing.get("traceability", refreshed["traceability"])
    old_retrievals = (existing.get("provenance") or {}).get("retrievals") or []
    new_retrievals = refreshed["provenance"]["retrievals"]
    merged["provenance"]["retrievals"] = old_retrievals + new_retrievals
    return merged


def rebuild_index(records_dir: Path, index_path: Path) -> None:
    entries = []
    for path, record in load_records(records_dir):
        bib = record.get("bibliographic") or {}
        entries.append(
            {
                "record_id": record.get("record_id"),
                "status": record.get("status"),
                "title": bib.get("title"),
                "year": bib.get("year"),
                "doi": (record.get("external_ids") or {}).get("doi"),
                "record_path": str(Path("records") / path.name).replace("\\", "/"),
                "note_path": str(Path("notes") / f"{record.get('record_id')}.md").replace("\\", "/"),
            }
        )
    content = json.dumps({"schema_version": 1, "works": sorted(entries, key=lambda item: item["record_id"] or "")}, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(index_path, content)


def persist_record(
    record: dict[str, Any],
    *,
    project_dir: Path,
    template_path: Path,
    update: bool,
    dry_run: bool,
) -> dict[str, Any]:
    literature_dir = project_dir / "literature"
    records_dir = literature_dir / "records"
    duplicate = find_duplicate(records_dir, record)
    action = "created"

    if duplicate:
        record_path, existing = duplicate
        if not update:
            return {"action": "duplicate", "record_id": existing["record_id"], "record_path": str(record_path)}
        record = merge_update(existing, record)
        action = "updated"
    else:
        record_path = records_dir / f"{record['record_id']}.json"

    note_path = literature_dir / "notes" / f"{record['record_id']}.md"
    if not dry_run:
        atomic_write_text(record_path, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        if not note_path.exists():
            atomic_write_text(note_path, render_evidence_card(record, template_path))
        rebuild_index(records_dir, literature_dir / "index.json")

    return {
        "action": "dry-run" if dry_run else action,
        "record_id": record["record_id"],
        "record_path": str(record_path),
        "note_path": str(note_path),
        "record": record if dry_run else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identifiers", nargs="+", help="DOI/URL, arXiv ID/URL, OpenAlex W ID, or PMID")
    parser.add_argument("--project-dir", required=True, type=Path, help="Existing ResearchCenter project directory")
    parser.add_argument("--mailto", help="Contact email for polite provider requests; defaults to CROSSREF_EMAIL")
    parser.add_argument("--openalex-api-key", help="OpenAlex API key; defaults to OPENALEX_API_KEY")
    parser.add_argument("--update", action="store_true", help="Refresh provider metadata and preserve curated fields")
    parser.add_argument("--dry-run", action="store_true", help="Resolve and normalize without writing files")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable result JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_dir = args.project_dir.resolve()
    if not project_dir.is_dir():
        print(f"error: project directory does not exist: {project_dir}", file=sys.stderr)
        return 2

    mailto = args.mailto or os.environ.get("CROSSREF_EMAIL")
    openalex_api_key = args.openalex_api_key or os.environ.get("OPENALEX_API_KEY")
    template_path = Path(__file__).resolve().parent.parent / "assets" / "evidence-card.md"
    if not template_path.is_file():
        print(f"error: evidence-card template missing: {template_path}", file=sys.stderr)
        return 2

    results = []
    failures = []
    for value in args.identifiers:
        try:
            identifier = normalize_identifier(value)
            metadata = fetch_metadata(identifier, mailto=mailto, openalex_api_key=openalex_api_key)
            record = build_record(metadata, project_id=project_dir.name, input_value=value)
            result = persist_record(
                record,
                project_dir=project_dir,
                template_path=template_path,
                update=args.update,
                dry_run=args.dry_run,
            )
            result["input"] = value
            results.append(result)
        except IntakeError as exc:
            failures.append({"input": value, "error": str(exc)})

    summary = {"results": results, "failures": failures}
    if args.json_output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"{result['action']}: {result['input']} -> {result['record_id']}")
        for failure in failures:
            print(f"failed: {failure['input']}: {failure['error']}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
