from pathlib import Path

import pytest


def test_agent_evaluation_manifest_validates_counts_and_review_status(
    tmp_path: Path,
) -> None:
    import json

    from submission.build_documents import load_agent_evaluation

    manifest = load_agent_evaluation()
    assert manifest["trial_count"] == 45
    assert manifest["completed_trial_count"] == manifest["trial_count"]
    assert len(manifest["case_findings"]) == 15
    assert manifest["scientific_review_status"] == "UNVERIFIED"
    feedback = manifest["targeted_feedback"]
    assert feedback["trial"] == "NOAA-D01:2"
    assert [item["assessment"] for item in feedback["responses"]] == [
        "unsure",
        "no",
        "unable to assess",
    ]

    manifest["trial_count"] = 44
    corrupted = tmp_path / "agent-evaluation.json"
    corrupted.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="inconsistent trial counts"):
        load_agent_evaluation(corrupted)

    manifest["trial_count"] = 45
    manifest["completed_trial_count"] = 44
    corrupted.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="inconsistent trial counts"):
        load_agent_evaluation(corrupted)

    manifest["completed_trial_count"] = 45
    manifest["targeted_feedback"]["trial"] = "UNKNOWN:1"
    corrupted.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown trial case"):
        load_agent_evaluation(corrupted)


def test_evidence_appendix_survives_document_roundtrip(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    pytest.importorskip("pptx")
    from submission.build_documents import add_evidence_appendix

    appendix = tmp_path / "appendix.md"
    appendix.write_text(
        "# Evidence\n\n"
        "Reported and recalculated values.\n\n"
        "| Year | Weight |\n"
        "|---|---|\n"
        "| 2025 | null / null |\n\n"
        "- Scientific review remains unverified.\n",
        encoding="utf-8",
    )
    document = docx.Document()
    for style in document.styles:
        if style.name == "Table Grid":
            style.element.getparent().remove(style.element)
            break
    add_evidence_appendix(document, appendix)
    output = tmp_path / "evaluation.docx"
    document.save(output)
    saved = docx.Document(output)

    assert [cell.text for cell in saved.tables[0].rows[1].cells] == [
        "2025",
        "null / null",
    ]
    assert any("review remains unverified" in p.text for p in saved.paragraphs)


def test_generated_deliverables_preserve_discrepancies(tmp_path: Path) -> None:
    import json

    docx = pytest.importorskip("docx")
    pptx = pytest.importorskip("pptx")
    from submission.build_documents import (
        load_agent_evaluation,
        make_deck,
        make_document,
    )

    root = Path(__file__).resolve().parents[1]
    report = json.loads(
        (root / "eval" / "results" / "candidate-v2-all.json").read_text(
            encoding="utf-8"
        )
    )
    deck_template = tmp_path / "template.pptx"
    deck = pptx.Presentation()
    for _ in range(12):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.shapes.add_textbox(0, 0, 1000000, 1000000).text = "SAMPLE CLAIM"
    deck.save(deck_template)
    doc_template = tmp_path / "template.docx"
    document = docx.Document()
    document.add_paragraph("SAMPLE CLAIM")
    document.save(doc_template)

    deck_path = tmp_path / "deck.pptx"
    doc_path = tmp_path / "evaluation.docx"
    receipt = {
        "tool_calls": [{}, {}, {}],
        "public_source": {"source_sha256": "a" * 64},
        "database_sha256": "b" * 64,
    }
    agent_evaluation = load_agent_evaluation()
    make_deck(deck_template, deck_path, report, receipt, agent_evaluation)
    make_document(doc_template, doc_path, report, agent_evaluation)
    saved_deck = pptx.Presentation(deck_path)
    deck_text = "\n".join(
        shape.text
        for slide in saved_deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
    )
    saved_doc = docx.Document(doc_path)
    document_text = "\n".join(
        [p.text for p in saved_doc.paragraphs]
        + [
            cell.text
            for table in saved_doc.tables
            for row in table.rows
            for cell in row.cells
        ]
    )

    for text in (deck_text, document_text):
        assert "SAMPLE CLAIM" not in text
        assert "UNVERIFIED" in text
        assert "scientific approval" in text
        assert "p95" not in text
        assert "duration" not in text.lower()
        assert "latency" not in text.lower()
    assert "45 model-selected trials" in deck_text
    assert "82/84" in deck_text
    assert "All three find the context card" in deck_text
    assert "Five focused tools" in deck_text
    assert "PUBLIC CONTEXT + RECEIPT" in deck_text
    assert "70 of 377" in deck_text
    assert "609.780" in deck_text and "416.396" in deck_text
    assert "Calls are scripted, not model-selected" in deck_text
    assert "no overall agent pass rate is claimed" in deck_text
    assert "A02 and D01 are" not in deck_text
    assert "Fisheries" in deck_text and "SI-Ready Gateway" in deck_text
    assert "NEFSC MISSION" in deck_text
    assert "45 completed, with 82 successful calls out of 84" in document_text
    assert "no tows" in document_text
    assert "Temperature was not recorded" in document_text
    assert "Q10:2" in document_text and "Q12:3" in document_text
    assert "Candidate-v7 agent trials now include A02 and D01" in document_text
    assert "FastMCP 2.14.7" in deck_text and "FastMCP 2.14.7" in document_text
    assert "loopback-only" in deck_text
    assert "Limited subject-matter input on one claim" in deck_text
    assert "Targeted subject-matter feedback" in document_text
    assert "historical NOAA-D01:2" in document_text
    assert "unsure" in document_text and "unable to assess" in document_text
    assert "not the complete answer or the trial suite" in document_text
    assert "no full scientific review or approval" in document_text
    assert "CycloneDX inventory" in document_text
    assert "does not authenticate callers" in document_text
    assert (
        "No agent rerun has been performed after the latest changes"
        not in document_text
    )
    assert "not live report discovery" in document_text
    assert (
        "trial-FAIL recommendations remain assistant evidence judgments"
        in document_text
    )
    assert "Discrepancies and their owners" in document_text
    assert "Overview is on physical PDF page 3" in document_text
    for heading in (
        "1. Overview and Objectives",
        "2. Testing Methodology",
        "3. Performance Metrics",
        "4. Security Considerations",
        "5. Lessons Learned & Recommendations",
    ):
        assert heading in document_text
    assert "Provisional scientific schema contract" in document_text
    assert "not an expert-approved" in document_text
    assert "SSO alone is not data authorization" in document_text
    assert "schema-contract" not in document_text

    del agent_evaluation["targeted_feedback"]
    legacy_manifest = tmp_path / "legacy-manifest.json"
    legacy_manifest.write_text(json.dumps(agent_evaluation), encoding="utf-8")
    legacy_evaluation = load_agent_evaluation(legacy_manifest)
    make_deck(deck_template, deck_path, report, receipt, legacy_evaluation)
    make_document(doc_template, doc_path, report, legacy_evaluation)
    legacy_deck = pptx.Presentation(deck_path)
    legacy_deck_text = "\n".join(
        shape.text
        for slide in legacy_deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
    )
    legacy_notes = legacy_deck.slides[-1].notes_slide.notes_text_frame.text
    legacy_doc_text = "\n".join(p.text for p in docx.Document(doc_path).paragraphs)
    assert "Limited subject-matter input on one claim" not in legacy_deck_text
    assert (
        "No scientific approval or enterprise readiness is claimed" in legacy_deck_text
    )
    assert "Targeted feedback on" not in legacy_notes
    assert "Targeted subject-matter feedback" not in legacy_doc_text
    assert "No full scientific review or approval is claimed" in legacy_doc_text
