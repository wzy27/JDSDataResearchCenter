import json
import tempfile
import unittest
from pathlib import Path

import literature_intake as intake


CROSSREF_FIXTURE = {
    "DOI": "10.1234/Example.1",
    "title": ["A Reproducible Experiment"],
    "author": [
        {"given": "Ada", "family": "Lovelace", "ORCID": "https://orcid.org/0000-0001-0000-0001"},
        {"given": "Grace", "family": "Hopper"},
    ],
    "published-online": {"date-parts": [[2025, 4, 3]]},
    "container-title": ["Journal of Tests"],
    "publisher": "Example Publisher",
    "type": "journal-article",
    "language": "en",
    "abstract": "<jats:p>Measured result with <b>controls</b>.</jats:p>",
    "subject": ["Reproducibility", "Experiments"],
    "is-referenced-by-count": 12,
    "URL": "https://doi.org/10.1234/example.1",
    "link": [{"URL": "https://example.org/paper.pdf"}],
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


OPENALEX_FIXTURE = {
    "id": "https://openalex.org/W123",
    "display_name": "A Reproducible Experiment",
    "publication_year": 2025,
    "publication_date": "2025-04-03",
    "type": "article",
    "language": "en",
    "doi": "https://doi.org/10.1234/example.1",
    "authorships": [
        {"author": {"id": "https://openalex.org/A1", "display_name": "Ada Lovelace", "orcid": None}}
    ],
    "primary_location": {
        "landing_page_url": "https://doi.org/10.1234/example.1",
        "source": {"display_name": "Journal of Tests"},
    },
    "best_oa_location": {"landing_page_url": "https://example.org/open", "pdf_url": None, "license": "cc-by"},
    "open_access": {"oa_url": "https://example.org/open"},
    "abstract_inverted_index": {"Measured": [0], "result": [1], "controls": [3], "with": [2]},
    "topics": [{"display_name": "Reproducible research"}],
    "cited_by_count": 11,
    "ids": {"openalex": "https://openalex.org/W123", "pmid": "https://pubmed.ncbi.nlm.nih.gov/42"},
}


ARXIV_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>https://arxiv.org/abs/2501.01234v1</id>
    <updated>2025-01-04T00:00:00Z</updated>
    <published>2025-01-03T00:00:00Z</published>
    <title>  A Test Preprint  </title>
    <summary>Evidence from a controlled evaluation.</summary>
    <author><name>Ada Lovelace</name></author>
    <category term="cs.AI" />
    <link href="https://arxiv.org/abs/2501.01234v1" rel="alternate" />
    <link href="https://arxiv.org/pdf/2501.01234v1" rel="related" type="application/pdf" />
    <arxiv:doi>10.1234/preprint.1</arxiv:doi>
  </entry>
</feed>
"""


class LiteratureIntakeTest(unittest.TestCase):
    def test_identifier_normalization(self):
        self.assertEqual(intake.normalize_identifier("https://doi.org/10.1234/Example.1")["value"], "10.1234/example.1")
        self.assertEqual(intake.normalize_identifier("https://openalex.org/W123")["value"], "W123")
        self.assertEqual(intake.normalize_identifier("arXiv:2501.01234v2")["value"], "2501.01234v2")
        self.assertEqual(intake.normalize_identifier("PMID:42")["value"], "42")

    def test_generic_url_is_rejected(self):
        with self.assertRaises(intake.IntakeError):
            intake.normalize_identifier("https://example.org/paper")

    def test_crossref_normalization(self):
        metadata = intake.normalize_crossref(CROSSREF_FIXTURE, "https://api.crossref.org/example")
        self.assertEqual(metadata["external_ids"]["doi"], "10.1234/example.1")
        self.assertEqual(metadata["bibliographic"]["year"], 2025)
        self.assertEqual(metadata["bibliographic"]["authors"][0]["name"], "Ada Lovelace")
        self.assertEqual(metadata["bibliographic"]["abstract"], "Measured result with controls.")

    def test_openalex_abstract_and_ids(self):
        metadata = intake.normalize_openalex(OPENALEX_FIXTURE, "https://api.openalex.org/works/W123")
        self.assertEqual(metadata["bibliographic"]["abstract"], "Measured result with controls")
        self.assertEqual(metadata["external_ids"]["openalex"], "W123")
        self.assertEqual(metadata["external_ids"]["pmid"], "42")

    def test_arxiv_normalization(self):
        metadata = intake.normalize_arxiv(ARXIV_FIXTURE, "2501.01234v1", "https://export.arxiv.org/api/query")
        self.assertEqual(metadata["bibliographic"]["title"], "A Test Preprint")
        self.assertEqual(metadata["external_ids"]["doi"], "10.1234/preprint.1")
        self.assertEqual(metadata["external_ids"]["arxiv"], "2501.01234v1")

    def test_record_id_is_stable(self):
        metadata = intake.normalize_crossref(CROSSREF_FIXTURE, "https://api.crossref.org/example")
        first = intake.build_record(metadata, project_id="demo", input_value="doi:10.1234/example.1", now="2025-01-01T00:00:00Z")
        second = intake.build_record(metadata, project_id="demo", input_value="https://doi.org/10.1234/example.1", now="2026-01-01T00:00:00Z")
        self.assertEqual(first["record_id"], second["record_id"])

    def test_persist_duplicate_and_update_preserve_review(self):
        metadata = intake.normalize_crossref(CROSSREF_FIXTURE, "https://api.crossref.org/example")
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "demo"
            project.mkdir()
            template = Path(__file__).resolve().parent.parent / "assets" / "evidence-card.md"
            record = intake.build_record(metadata, project_id="demo", input_value="10.1234/example.1", now="2025-01-01T00:00:00Z")
            created = intake.persist_record(record, project_dir=project, template_path=template, update=False, dry_run=False)
            self.assertEqual(created["action"], "created")

            record_path = Path(created["record_path"])
            saved = json.loads(record_path.read_text(encoding="utf-8"))
            saved["review"]["relevance"] = "include"
            record_path.write_text(json.dumps(saved), encoding="utf-8")

            duplicate = intake.persist_record(record, project_dir=project, template_path=template, update=False, dry_run=False)
            self.assertEqual(duplicate["action"], "duplicate")

            refreshed = intake.build_record(metadata, project_id="demo", input_value="10.1234/example.1", now="2026-01-01T00:00:00Z")
            updated = intake.persist_record(refreshed, project_dir=project, template_path=template, update=True, dry_run=False)
            after = json.loads(Path(updated["record_path"]).read_text(encoding="utf-8"))
            self.assertEqual(updated["action"], "updated")
            self.assertEqual(after["review"]["relevance"], "include")
            self.assertEqual(after["created_at"], "2025-01-01T00:00:00Z")
            self.assertEqual(len(after["provenance"]["retrievals"]), 2)


if __name__ == "__main__":
    unittest.main()
