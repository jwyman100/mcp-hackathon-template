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


def test_current_evaluation_rejects_inconsistent_review(tmp_path: Path) -> None:
    import copy
    import json

    from submission.build_documents import load_current_evaluation

    manifest = load_current_evaluation()
    corrupted = tmp_path / "current-evaluation.json"
    variants = []

    wrong_trials = copy.deepcopy(manifest)
    wrong_trials["mcp"]["completed_trials"] -= 1
    variants.append(wrong_trials)

    duplicate_issue = copy.deepcopy(manifest)
    issues = duplicate_issue["answer_review"]["batches"][0]["issues"]
    issues[1]["trial"] = issues[0]["trial"]
    variants.append(duplicate_issue)

    unapproved_review = copy.deepcopy(manifest)
    unapproved_review["answer_review"]["scientific_review"] = "PASS"
    variants.append(unapproved_review)

    wrong_comparison = copy.deepcopy(manifest)
    wrong_comparison["data_access_comparison"]["trials_per_arm"] -= 1
    variants.append(wrong_comparison)

    for variant in variants:
        corrupted.write_text(json.dumps(variant), encoding="utf-8")
        with pytest.raises(ValueError, match="inconsistent counts or review"):
            load_current_evaluation(corrupted)


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
        load_current_evaluation,
        make_deck,
        make_document,
        make_video_deck,
    )

    root = Path(__file__).resolve().parents[1]
    report = json.loads(
        (root / "eval" / "results" / "candidate-v7-hardened-scripted.json").read_text(
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
    video_deck_path = tmp_path / "video-deck.pptx"
    doc_path = tmp_path / "evaluation.docx"
    current_evaluation = load_current_evaluation()
    receipt = {
        "tool_calls": [{}, {}, {}],
        "public_source": {
            "source_sha256": current_evaluation["source"]["public_archive_sha256"]
        },
        "database_sha256": current_evaluation["source"]["sqlite_sha256"],
    }
    agent_evaluation = load_agent_evaluation()
    make_deck(deck_template, deck_path, report, receipt, agent_evaluation)
    make_video_deck(deck_path, video_deck_path)
    make_document(doc_template, doc_path, report, agent_evaluation)
    saved_deck = pptx.Presentation(deck_path)
    saved_video = pptx.Presentation(video_deck_path)
    assert len(saved_video.slides) == 6
    expected_titles = (
        "SI-Ready Gateway",
        "Five tools for public fisheries data",
        "Demo: a question with a trap",
        "Getting data is only the first step",
        "The AI spotted a useful clue",
        "Useful access, with scientists in the loop",
    )
    for number, (slide, title) in enumerate(
        zip(saved_video.slides, expected_titles, strict=True), start=1
    ):
        assert any(
            title in shape.text for shape in slide.shapes if shape.has_text_frame
        )
        if number > 1:
            footer = next(
                shape.text
                for shape in slide.shapes
                if shape.has_text_frame
                and shape.text.startswith("PUBLIC NOAA SNAPSHOT")
            )
            assert footer.endswith(f"{number:02}")

    script_lines = (
        (root / "submission" / "VIDEO.md")
        .read_text(encoding="utf-8")
        .split("## Script\n", 1)[1]
        .splitlines()
    )
    script = []
    quote = []
    for line in script_lines + [""]:
        if line.startswith("> "):
            quote.append(line[2:])
        elif quote:
            script.append(" ".join(quote))
            quote = []
    assert script == [
        " ".join(slide.notes_slide.notes_text_frame.text.split())
        for slide in saved_video.slides
    ]
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
        assert "scientific approval" in text
        assert "p95" not in text
        assert "duration" not in text.lower()
        assert "latency" not in text.lower()
    assert "UNVERIFIED" in document_text
    assert "NOAA Fisheries Data Gateway: Evaluation" in document_text
    assert "Five tools for public fisheries data" in deck_text
    assert "36/36" in deck_text
    assert "80/80" in deck_text
    assert "24/24" in deck_text
    assert "Without tools: 0/24" in deck_text
    assert "6 ANSWERS" in deck_text and "DATA CHECK" in deck_text
    assert "37 OTHER" in deck_text
    assert "that context matters" in deck_text
    assert "cannot measure how much sampling explains" in deck_text
    assert "Checked tool results matched calculations from NOAA files." in deck_text
    assert "claims the evidence did not support" not in deck_text
    assert "70 of 377" in deck_text
    assert "609.780" in deck_text and "416.396" in deck_text
    assert "This example is scripted; it is not an AI-selected answer." in deck_text
    assert "not whether every answer is correct" in deck_text
    assert "Fisheries" in deck_text and "SI-Ready Gateway" in deck_text
    assert "a scientist still needs to check" in (
        saved_deck.slides[5].notes_slide.notes_text_frame.text
    )
    video_demo_text = "\n".join(
        shape.text for shape in saved_video.slides[2].shapes if shape.has_text_frame
    )
    assert "LIVE DEMO" in video_demo_text
    assert "REFERENCE VALUES FROM OUR PUBLIC DATA" in video_demo_text
    assert "live recording is a separate example" in video_demo_text
    assert "This example is scripted" not in video_demo_text
    assert "separate from the evaluation" in (
        saved_video.slides[2].notes_slide.notes_text_frame.text
    )
    review_script = saved_video.slides[4].notes_slide.notes_text_frame.text
    assert "That's useful context" in review_script
    assert "cannot measure how much sampling explains" in review_script
    assert "not a scientific verdict" in review_script
    assert "45 main trials completed" in document_text
    assert "80/80" in document_text
    assert "24/24" in document_text and "0/24" in document_text
    assert "no underlying records" in document_text
    assert "37 trials were not fully reviewed" in document_text
    assert "This is useful context" in document_text
    assert "AI-assisted, not independent scientific review" in document_text
    assert "No scientific approval is claimed" in document_text
    assert "not a blind test" in document_text
    assert "does not authenticate users" in document_text
    assert "Neither new run is claimed complete" not in document_text
    for heading in (
        "1. Overview and Objectives",
        "2. Testing Methodology",
        "3. Performance Metrics",
        "4. Security Considerations",
        "5. Lessons Learned & Recommendations",
    ):
        assert heading in document_text
    assert "hardened-agent-evaluation.json" in document_text
    assert "candidate-v7-agent-evaluation.json" in document_text

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
    assert "We received limited feedback on one earlier claim" not in legacy_deck_text
    assert "not scientific approval or a system ready for internal use" in (
        legacy_deck_text
    )
    assert "Limited feedback addressed" not in legacy_notes
    assert "Limited subject-matter feedback" not in legacy_doc_text
    assert "No scientific approval is claimed" in legacy_doc_text

    receipt["database_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="evidence sources differ"):
        make_deck(deck_template, deck_path, report, receipt, agent_evaluation)
