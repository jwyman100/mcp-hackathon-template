"""Adapt the official GSA deck/document templates using recorded local evidence."""

import argparse
import json
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches as DocInches
from docx.shared import Pt as DocPt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

AGENT_EVALUATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "eval"
    / "results"
    / "candidate-v7-agent-evaluation.json"
)


def load_agent_evaluation(path: Path = AGENT_EVALUATION_PATH) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    trial_count = (
        sum(len(batch["cases"]) for batch in evidence["batches"])
        * evidence["repeats_per_case"]
    )
    if (
        evidence["schema_version"] != 1
        or trial_count != evidence["trial_count"]
        or evidence["completed_trial_count"] != evidence["trial_count"]
    ):
        raise ValueError("Agent evaluation manifest has inconsistent trial counts.")
    cases = evidence["case_findings"]
    batch_case_ids = [
        case_id for batch in evidence["batches"] for case_id in batch["cases"]
    ]
    if set(batch_case_ids) != {case["id"] for case in cases}:
        raise ValueError("Agent evaluation batches and case findings do not match.")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Agent evaluation manifest contains duplicate cases.")
    if evidence["scientific_review_status"] != "UNVERIFIED":
        raise ValueError("Agent evaluation review status requires manual verification.")
    if "targeted_feedback" in evidence:
        feedback = evidence["targeted_feedback"]
        if feedback["trial"].split(":")[0] not in batch_case_ids:
            raise ValueError("Targeted feedback refers to an unknown trial case.")
    calls = evidence["tool_call_counts"]
    if calls["successful"] + calls["failed"] != calls["total"]:
        raise ValueError("Agent evaluation tool-call counts are inconsistent.")
    return evidence


def make_deck(
    template: Path,
    output: Path,
    report: dict,
    receipt: dict | None = None,
    agent_evaluation: dict | None = None,
) -> None:
    benchmark_path = Path(__file__).resolve().parents[1] / "eval" / "benchmark.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    baseline = benchmark["baseline"]
    agent_evaluation = agent_evaluation or load_agent_evaluation()
    trial_count = agent_evaluation["trial_count"]
    tool_calls = agent_evaluation["tool_call_counts"]
    feedback = agent_evaluation.get("targeted_feedback")
    cases = {case["id"]: case for case in agent_evaluation["case_findings"]}
    presentation = Presentation(template)
    presentation.core_properties.title = "Fisheries SI-Ready Gateway"
    presentation.core_properties.author = ""
    presentation.core_properties.last_modified_by = ""
    presentation.core_properties.subject = ""
    presentation.core_properties.keywords = ""
    presentation.core_properties.comments = ""
    if len(presentation.slides) != 12:
        raise ValueError("GSA deck structure changed; review the template.")

    navy = RGBColor.from_string("102D3D")
    teal = RGBColor.from_string("087F82")
    ink = RGBColor.from_string("1D3642")
    muted = RGBColor.from_string("536B75")
    pale = RGBColor.from_string("EAF4F2")
    light = RGBColor.from_string("F3F7F8")
    gold = RGBColor.from_string("FFF2D6")
    white = RGBColor.from_string("FFFFFF")

    def rectangle(slide, x, y, width, height, fill):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x),
            Inches(y),
            Inches(width),
            Inches(height),
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        shape.line.fill.background()
        shape.adjustments[0] = 0.08
        return shape

    def text(slide, x, y, width, height, value, size=16, color=ink, bold=False):
        shape = slide.shapes.add_textbox(
            Inches(x), Inches(y), Inches(width), Inches(height)
        )
        frame = shape.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = 0
        frame.margin_top = frame.margin_bottom = 0
        paragraph = frame.paragraphs[0]
        paragraph.text = value
        paragraph.font.name = "Arial"
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = color
        return shape

    def card(slide, x, y, width, height, heading, body, fill=light):
        rectangle(slide, x, y, width, height, fill)
        size = 11 if width < 2 else 15
        text(slide, x + 0.17, y + 0.16, width - 0.34, 0.34, heading, size, teal, True)
        text(
            slide,
            x + 0.17,
            y + 0.58,
            width - 0.34,
            height - 0.68,
            body,
            13 if width < 2 else 15,
        )

    def start(slide, number, title, section):
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = white
        text(slide, 0.48, 0.24, 8.9, 0.25, section.upper(), 10, teal, True)
        text(slide, 0.48, 0.62, 9.05, 0.58, title, 26, navy, True)
        text(
            slide,
            0.48,
            5.32,
            8.9,
            0.17,
            f"PUBLIC NOAA SNAPSHOT  |  EVIDENCE-AWARE FISHERIES MCP    {number:02}",
            8,
            muted,
        )

    for slide in presentation.slides:
        for shape in list(slide.shapes):
            element = shape._element
            element.getparent().remove(element)
        for relation in list(slide.part.rels.values()):
            if relation.reltype.endswith(("/image", "/chart")):
                slide.part.drop_rel(relation.rId)

    slide = presentation.slides[0]
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = navy
    text(
        slide,
        0.65,
        0.55,
        8.5,
        0.3,
        "GSA DATASET ACCESS SERVER  /  PROTOTYPE",
        12,
        white,
        True,
    )
    text(slide, 0.65, 1.22, 8.7, 1.2, "Fisheries\nSI-Ready Gateway", 36, white, True)
    text(
        slide,
        0.68,
        2.73,
        8.5,
        0.7,
        "A scientist-centered path from public data to bounded MCP tools.",
        20,
        white,
    )
    rectangle(slide, 0.65, 3.78, 8.7, 0.76, teal)
    text(
        slide,
        0.9,
        4.00,
        8.2,
        0.4,
        "PUBLIC NOAA PROTOTYPE  |  2021-2025  |  local and read-only",
        16,
        white,
        True,
    )
    text(
        slide,
        0.68,
        5.15,
        8.6,
        0.24,
        "Demonstrated public prototype; enterprise controls are planned, not deployed.",
        10,
        white,
    )

    slide = presentation.slides[1]
    start(slide, 2, "Less friction, with scientific context intact", "The challenge")
    card(
        slide,
        0.5,
        1.55,
        2.85,
        2.15,
        "THE QUESTION",
        "Researchers navigate schema, filters and repeated clarification "
        "before analysis.",
    )
    card(
        slide,
        3.58,
        1.55,
        2.85,
        2.15,
        "THE RISK",
        "An answer can confuse missing records with zero or catch with abundance.",
        gold,
    )
    card(
        slide,
        6.66,
        1.55,
        2.85,
        2.15,
        "THE HANDOFF",
        "Give scientists traceable, bounded evidence they can judge and reuse.",
        pale,
    )
    text(
        slide,
        0.56,
        4.19,
        8.8,
        0.55,
        "Intended benefit: reduce access and handoff friction; time savings "
        "are not measured.",
        16,
        muted,
    )

    slide = presentation.slides[2]
    start(slide, 3, "Five focused tools for the public demonstration", "The solution")
    cards = [
        ("01  FIND", "Search published species names."),
        ("02  SUMMARIZE", "Catch and measurement completeness."),
        ("03  COMPARE", "Two species, matching scope."),
        ("04  COVERAGE", "Station, cruise and stratum counts."),
        ("05  CONTEXT", "Curated, cited 2023/2025 NOAA facts; not expert-approved."),
    ]
    for index, (heading, body) in enumerate(cards):
        if index < 3:
            x, y, width = 0.5 + index * 3.08, 1.48, 2.85
        else:
            x, y, width = 0.5 + (index - 3) * 4.62, 3.18, 4.39
        card(slide, x, y, width, 1.48, heading, body, pale if index == 4 else light)
    text(
        slide,
        0.55,
        4.86,
        8.9,
        0.22,
        "Source checking is separate from scientific review; status is not reviewed.",
        11,
        muted,
    )

    slide = presentation.slides[3]
    start(slide, 4, "What runs today—and what is only planned", "Architecture")
    stages = [
        ("PUBLIC ZIP", "NOAA\narchive"),
        ("PREPARE", "Pinned hash\n+ validated joins"),
        ("SNAPSHOT", "Read-only\nSQLite"),
        ("MCP TOOLS", "Typed requests\n+ caveats"),
        ("CLIENT", "Answer +\nhuman review"),
    ]
    for index, (heading, body) in enumerate(stages):
        x = 0.5 + index * 1.87
        card(slide, x, 1.68, 1.56, 1.62, heading, body, pale if index == 3 else light)
        if index < 4:
            text(slide, x + 1.61, 2.25, 0.2, 0.4, ">", 19, teal, True)
    card(
        slide,
        0.5,
        3.62,
        4.35,
        1.28,
        "DEMONSTRATED",
        "Public snapshot, typed read-only tools, local stdio; no private data.",
        pale,
    )
    card(
        slide,
        5.15,
        3.62,
        4.35,
        1.28,
        "PLANNED ENTERPRISE",
        "Authorized Oracle access, SSO, per-tool authorization, guardrails and audit.",
        gold,
    )

    slide = presentation.slides[4]
    start(slide, 5, "A pinned, portable snapshot", "Technical decisions")
    card(slide, 0.5, 1.5, 2.85, 1.55, "2021-2025", "Spring survey; two species.")
    card(slide, 3.58, 1.5, 2.85, 1.55, "1,570", "Selected station records.")
    card(slide, 6.66, 1.5, 2.85, 1.55, "758", "Selected catch records.")
    rectangle(slide, 0.5, 3.42, 9.0, 1.4, pale)
    text(
        slide,
        0.72,
        3.58,
        8.5,
        0.42,
        "Offline/read-only snapshot | non-root container | pinned images and lockfile",
        14,
        ink,
    )
    text(
        slide,
        0.72,
        4.03,
        8.5,
        0.56,
        "CI is configured to audit dependencies, scan secrets and build the container. "
        "HTTP is loopback-only by default; ingress acknowledgement is not "
        "authentication.",
        12,
        ink,
    )

    slide = presentation.slides[5]
    start(
        slide,
        6,
        "Define a scientific schema contract",
        "Technical decisions",
    )
    card(
        slide,
        0.5,
        1.48,
        4.35,
        2.8,
        "CONTRACT RECORDS",
        "Analysis grain, filters, source identity, units, missingness and "
        "supported conclusions.",
        pale,
    )
    card(
        slide,
        5.15,
        1.48,
        4.35,
        2.8,
        "EXPERTS MUST REVIEW",
        "Population meaning, sampling design, valid joins, scientific limits "
        "and acceptable interpretations.",
        gold,
    )
    text(
        slide,
        0.56,
        4.65,
        8.9,
        0.38,
        "Provisional example only—not approved by a fisheries subject-matter expert.",
        15,
        muted,
    )

    slide = presentation.slides[6]
    start(
        slide,
        7,
        "Co-design, version, and test schemas",
        "Technical decisions",
    )
    card(
        slide,
        0.5,
        1.55,
        2.85,
        2.35,
        "BOUNDED INPUT",
        "Typed years and strata, distinct species, and explicit request scope.",
    )
    card(
        slide,
        3.58,
        1.55,
        2.85,
        2.35,
        "SAFE HANDOFF",
        "Search labels work in catch tools; unknown and empty states stay explicit.",
        pale,
    )
    card(
        slide,
        6.66,
        1.55,
        2.85,
        2.35,
        "SCHEMA LIFECYCLE",
        "Proposed expert review, versioned semantics, tests and re-review on change.",
    )
    text(
        slide,
        0.55,
        4.3,
        8.9,
        0.55,
        "Direct tests check the label fix; expert approval and preflight are "
        "not implemented.",
        15,
        muted,
    )

    slide = presentation.slides[7]
    start(
        slide,
        8,
        "A real scripted workflow with a replayable receipt",
        "Demonstrated public prototype",
    )
    rectangle(slide, 0.5, 1.39, 5.42, 2.58, light)
    text(
        slide,
        0.7,
        1.56,
        5.0,
        0.27,
        "SEARCH  >  RETURNED LABEL  >  SUMMARY",
        12,
        teal,
        True,
    )
    columns = [
        (0.7, 0.7, "YEAR", "2022", "2023"),
        (1.55, 1.2, "WEIGHT*", "609.780", "416.396"),
        (3.0, 1.65, "STATION RECORDS", "378", "77"),
        (4.8, 0.8, "STRATA", "82", "13"),
    ]
    for x, width, heading, first, second in columns:
        text(slide, x, 1.99, width, 0.30, heading, 11, muted, True)
        text(slide, x, 2.47, width, 0.35, first, 15, ink, True)
        text(slide, x, 3.04, width, 0.35, second, 15, ink, True)
    text(
        slide,
        0.7,
        3.57,
        5.0,
        0.22,
        "* Expanded catch weight, unspecified source units.",
        11,
        muted,
    )
    card(
        slide,
        6.15,
        1.39,
        3.35,
        2.58,
        "PUBLIC CONTEXT + RECEIPT",
        (
            "NOAA: 70 of 377 planned trawl stations; distinct from 77 snapshot "
            "station records.\n\n"
            f"Receipt: {len(receipt['tool_calls'])} exact calls/results, public "
            "source, database and code hashes; replay verified."
            if receipt
            else "Receipt not supplied to the document builder."
        ),
        pale,
    )
    text(
        slide,
        0.55,
        4.28,
        8.9,
        0.64,
        "Human handoff: survey disruption is context, not proof of cause. "
        "Which sampling locations and conditions are comparable?",
        16,
        navy,
        True,
    )
    text(
        slide,
        0.55,
        5.02,
        8.9,
        0.19,
        "Calls are scripted, not model-selected. Full hashes and results are in "
        "the public-only receipt; scientific review remains unverified.",
        10,
        muted,
    )

    slide = presentation.slides[8]
    start(
        slide,
        9,
        "Three layers answer different evaluation questions",
        "Evaluation design",
    )
    card(
        slide,
        0.5,
        1.55,
        2.85,
        2.28,
        "1  EDGE CASES",
        "Invented fixtures test missing values, errors and importer boundaries.",
    )
    card(
        slide,
        3.58,
        1.55,
        2.85,
        2.28,
        "2  SCRIPTED MCP",
        "12 cases x 3; checked against independent public-CSV calculations.",
        pale,
    )
    card(
        slide,
        6.66,
        1.55,
        2.85,
        2.28,
        "3  AGENT TRIALS",
        "Historical model-chosen calls; answers remain selectively reviewed.",
    )
    text(
        slide,
        0.55,
        4.18,
        8.9,
        0.66,
        f"Candidate-v7: {trial_count} model-selected trials; answer reviews "
        "remain UNVERIFIED.",
        15,
        muted,
    )

    slide = presentation.slides[9]
    start(slide, 10, "Evidence, not a perfect score", "Candidate-v7 evaluation")
    metrics = [
        (
            f"{baseline['scripted_passed']}/{baseline['scripted_trials']}",
            "historical scripted baseline",
        ),
        (f"{report['passed']}/{report['trial_count']}", "separate scripted checks"),
        (str(trial_count), "model-selected trials completed"),
        (
            f"{tool_calls['successful']}/{tool_calls['total']}",
            "successful tool calls",
        ),
    ]
    for index, (value, label) in enumerate(metrics):
        x = 0.5 + index * 2.31
        rectangle(slide, x, 1.5, 2.08, 1.45, pale if index == 1 else light)
        text(slide, x + 0.16, 1.68, 1.76, 0.54, value, 26, teal, True)
        text(slide, x + 0.16, 2.31, 1.76, 0.52, label, 12, ink)
    text(
        slide,
        0.55,
        3.35,
        8.8,
        0.38,
        f"{tool_calls['failed']} malformed tool calls recovered; "
        "successful retrieval is not an answer grade.",
        16,
        navy,
        True,
    )
    text(
        slide,
        0.55,
        3.9,
        8.8,
        0.36,
        "Numerical tool outputs aligned with supplied references in reviewed cases.",
        15,
    )
    text(
        slide,
        0.55,
        4.42,
        8.8,
        0.5,
        f"All {trial_count} trial reviews remain UNVERIFIED; no overall "
        "agent pass rate is claimed.",
        15,
        muted,
    )
    text(
        slide,
        0.55,
        5.02,
        8.8,
        0.34,
        "Candidate-v7 trials used FastMCP "
        f"{agent_evaluation['configuration']['versions']['fastmcp']}; "
        "the upgraded runtime was not agent-rerun.",
        11,
        muted,
    )

    slide = presentation.slides[10]
    start(slide, 11, "What the candidate-v7 trials taught us", "Agent evidence")
    findings = [
        ("D01", cases["NOAA-D01"]["slide_summary"]),
        ("A02 / C01", cases["NOAA-A02"]["slide_summary"]),
        ("Q10", cases["Q10"]["slide_summary"]),
        ("Q12", cases["Q12"]["slide_summary"]),
    ]
    for index, (label, body) in enumerate(findings):
        y = 1.4 + index * 0.77
        rectangle(slide, 0.5, y, 9.0, 0.61, light if index % 2 == 0 else pale)
        text(slide, 0.66, y + 0.16, 1.45, 0.31, label, 14, teal, True)
        text(slide, 2.1, y + 0.15, 7.16, 0.35, body, 14)
    text(
        slide,
        0.55,
        4.64,
        8.9,
        0.46,
        "All trial records remain UNVERIFIED; these are evaluation observations, "
        "not expert scientific approval.",
        13,
        muted,
    )

    slide = presentation.slides[11]
    start(
        slide,
        12,
        "Mission fit is the purpose; trust is the work",
        "Mission and next steps",
    )
    card(
        slide,
        0.5,
        1.48,
        4.35,
        2.43,
        "NEFSC MISSION",
        "Provide scientific information and tools for productive, sustainable, "
        "healthy marine ecosystems and coastal communities.",
        pale,
    )
    card(
        slide,
        5.15,
        1.48,
        4.35,
        2.43,
        "NEXT: GOVERNED ENTERPRISE",
        "Co-design each schema with experts; validate identity, authorization, "
        "audit and deployment controls before internal use.",
        gold,
    )
    text(
        slide,
        0.55,
        4.22,
        8.9,
        0.46,
        (
            "Limited subject-matter input on one claim flagged spatial context; "
            "no scientific approval or enterprise readiness is claimed."
            if feedback is not None
            else "No scientific approval or enterprise readiness is claimed."
        ),
        15,
        navy,
        True,
    )
    text(
        slide,
        0.55,
        4.79,
        8.9,
        0.3,
        "https://www.fisheries.noaa.gov/about/northeast-fisheries-science-center",
        11,
        muted,
    )

    notes = [
        "Public, read-only demonstration of a research-access idea. The fixed NOAA "
        "snapshot is not the internal database or an official stock assessment.",
        "The intended benefit is less schema-navigation and handoff friction. "
        "No quantified researcher time savings have been measured.",
        "The fifth tool is a manually curated source card for 2023 and 2025. "
        "Its source-check date is not scientific approval; status is not reviewed. "
        "It is not a live web or report-retrieval tool.",
        "Today: public snapshot, typed read-only tools and local stdio. The future "
        "Oracle/SSO/authorization/guardrail/audit design is planned only. SSO "
        "identifies a user; it does not grant data access by itself.",
        "Selected public snapshot: five cruises, 1,570 station records, 758 catch "
        "records; Atlantic cod and haddock. Extraction June 25, 2026.",
        "No valid-haul filtering, area weighting, effort standardization or vessel "
        "calibration. Unknown source units do not prove units are not kg or pounds.",
        "The scientific schema contract is provisional. Domain experts would "
        "confirm grain, identifiers, filters, units, missingness and interpretation "
        "before a future governed release.",
        "Run the scripted demo with --receipt to create exact public MCP request/"
        "result evidence. Replay checks source, database, server and result identity. "
        "It is not an agent-selected run or a security audit.",
        "The 12-question holdout is repository-visible, not blind. A01/B01/C01 "
        "remain historical source-assisted cases. Candidate-v7 adds three "
        "repetitions each for A02, D01 and C01; D01 tests a curated context card, "
        "not live report discovery.",
        f"Candidate-v7 includes {trial_count} model-selected trials across 15 "
        "questions, three repeats each. "
        f"{tool_calls['successful']} of {tool_calls['total']} recorded MCP calls "
        f"succeeded; {tool_calls['failed']} malformed calls recovered. All "
        "scientific reviews remain UNVERIFIED. Recorded code, question and "
        "database hashes identify the evaluated candidate. These runs are not "
        "a matched before/after model comparison.",
        "Observed interpretation issues include unsupported causal explanations "
        "in D01, missing-versus-zero reasoning in Q10:2, and an incorrect lowest "
        "weight statement in Q12:3. These findings do not establish that the "
        "tools resolved interpretation risk.",
        "NEFSC's published mission is to provide scientific information and tools "
        "for sustainable marine ecosystems and coastal communities. This project "
        "is an independent prototype, not official NOAA/DOC communication or "
        "endorsement. "
        + (
            f"Targeted feedback on {feedback['trial']} addresses one excerpt only: "
            f"{feedback['responses'][0]['detail']} {feedback['limitations']} "
            if feedback is not None
            else ""
        )
        + "No enterprise readiness is claimed.",
    ]
    for slide, note in zip(presentation.slides, notes, strict=True):
        slide.notes_slide.notes_text_frame.text = note
    presentation.save(output)


def add_evidence_appendix(document, path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    paragraph = []

    def plain(text: str) -> str:
        return text.replace("**", "").replace("`", "").replace("*", "")

    def flush() -> None:
        if paragraph:
            document.add_paragraph(plain(" ".join(paragraph)))
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush()
        elif line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            document.add_heading(plain(line[level:].strip()), min(level, 3))
        elif line.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [
                    cell.strip() for cell in lines[index].strip().strip("|").split("|")
                ]
                if not all(set(cell) <= set("-: ") for cell in cells):
                    rows.append(cells)
                index += 1
            if not rows or any(len(row) != len(rows[0]) for row in rows):
                raise ValueError("Invalid public evidence table.")
            table = document.add_table(rows=0, cols=len(rows[0]))
            table.autofit = False
            if len(rows[0]) == 7:
                widths = (0.55, 1.15, 1.15, 1.0, 1.05, 0.6, 1.15)
            elif rows[0][0] == "Case" and len(rows[0]) == 4:
                widths = (1.0, 0.5, 1.4, 3.75)
            else:
                widths = (6.65 / len(rows[0]),) * len(rows[0])
            for column, width in zip(table.columns, widths, strict=True):
                column.width = DocInches(width)
            for row_index, row in enumerate(rows):
                table_row = table.add_row()
                row_properties = table_row._tr.get_or_add_trPr()
                row_properties.append(OxmlElement("w:cantSplit"))
                if row_index == 0:
                    row_properties.append(OxmlElement("w:tblHeader"))
                for cell, value, width in zip(
                    table_row.cells, row, widths, strict=True
                ):
                    cell.width = DocInches(width)
                    cell.text = plain(value)
                    cell.paragraphs[0].paragraph_format.space_after = DocPt(0)
                    if row_index == 0:
                        shading = OxmlElement("w:shd")
                        shading.set(qn("w:fill"), "EAF4F2")
                        cell._tc.get_or_add_tcPr().append(shading)
                    for run in cell.paragraphs[0].runs:
                        run.font.size = DocPt(8.5)
                        run.bold = row_index == 0
            continue
        else:
            if line.startswith("- "):
                flush()
            paragraph.append(line)
        index += 1
    flush()


def add_agent_evaluation(document, evidence: dict) -> None:
    calls = evidence["tool_call_counts"]
    configuration = evidence["configuration"]
    document.add_heading("Candidate-v7 model-selected agent evaluation", 1)
    document.add_paragraph(
        f"{evidence['trial_count']} trials were completed across "
        f"{sum(len(batch['cases']) for batch in evidence['batches'])} questions "
        f"with {evidence['repeats_per_case']} repeats per question. "
        f"{calls['successful']} of {calls['total']} recorded MCP calls succeeded; "
        f"{calls['failed']} malformed calls recovered. All trial scientific-review "
        f"statuses remain {evidence['scientific_review_status']}."
    )
    document.add_paragraph(
        f"Recorded endpoint: {configuration['endpoint']}; "
        f"options: {json.dumps(configuration['options'], sort_keys=True)}. "
        f"Temperature was not recorded. The fixed public snapshot SHA-256 is "
        f"{evidence['dataset']['source_sha256']}; the SQLite SHA-256 is "
        f"{evidence['dataset']['sqlite_sha256']}. Recorded code, question and "
        "database hashes match the local candidate-v7 files checked. This "
        "identifies the evaluated candidate but is not a security audit. These "
        "runs do not form a matched before/after model comparison."
    )
    document.add_paragraph(
        evidence["numerical_payload_review"]["scope"]
        + " "
        + "The original public CSV archive was not independently reprocessed, "
        "and no fisheries expert review was performed as part of this bundle "
        "review. Numerical agreement is not scientific approval."
    )
    feedback = evidence.get("targeted_feedback")
    if feedback is not None:
        document.add_heading("Targeted subject-matter feedback", 2)
        document.add_paragraph(
            f"{feedback['date']}; historical {feedback['trial']}. "
            f"{feedback['scope']} The question concerned {feedback['question']}"
        )
        for response in feedback["responses"]:
            document.add_paragraph(
                f"{response['perspective']} — {response['assessment']}: "
                f"{response['detail']}"
            )
        document.add_paragraph(feedback["limitations"])
    document.add_heading("Per-question observations", 2)
    table = document.add_table(rows=1, cols=3)
    table.autofit = False
    widths = (0.85, 2.45, 3.35)
    for column, width in zip(table.columns, widths, strict=True):
        column.width = DocInches(width)
    for cell, label, width in zip(
        table.rows[0].cells,
        ("Case", "Observed result", "Observed limitation"),
        widths,
        strict=True,
    ):
        cell.width = DocInches(width)
        cell.text = label
    for case in evidence["case_findings"]:
        row = table.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, value, width in zip(
            row.cells,
            (case["id"], case["finding"], case["observed_issue"]),
            widths,
            strict=True,
        ):
            cell.width = DocInches(width)
            cell.text = value
            cell.paragraphs[0].paragraph_format.space_after = DocPt(0)
    for row_index, row in enumerate(table.rows):
        if row_index == 0:
            row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = DocPt(8)
                    run.bold = row_index == 0


def make_document(
    template: Path,
    output: Path,
    report: dict,
    agent_evaluation: dict | None = None,
) -> None:
    benchmark_path = Path(__file__).resolve().parents[1] / "eval" / "benchmark.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    baseline = benchmark["baseline"]
    candidate = benchmark["candidate"]
    agent_evaluation = agent_evaluation or load_agent_evaluation()
    agent_trials = agent_evaluation["trial_count"]
    tool_calls = agent_evaluation["tool_call_counts"]
    evaluated_fastmcp = agent_evaluation["configuration"]["versions"]["fastmcp"]
    document = Document(template)
    document.core_properties.title = "Fisheries SI-Ready Gateway: Evaluation"
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.subject = ""
    document.core_properties.keywords = ""
    document.core_properties.comments = ""
    normal = next(style for style in document.styles if style.style_id == "Normal")
    normal.font.size = DocPt(10)
    normal.paragraph_format.space_after = DocPt(4)
    normal.paragraph_format.line_spacing = 1.08
    for name, size in (("Heading 1", 15), ("Heading 2", 12), ("Heading 3", 11)):
        document.styles[name].font.size = DocPt(size)
    for element in list(document.element.body):
        if not element.tag.endswith("}sectPr"):
            document.element.body.remove(element)
    document.add_heading("Fisheries SI-Ready Gateway: Evaluation", 0)
    document.add_paragraph("GSA MCP and AI Agent Hackathon")
    document.add_paragraph(f"Scripted benchmark run: {report['run_utc']}")
    document.add_paragraph(
        "Status: scripted MCP integration, partial development numerical checks, "
        f"and {agent_trials} candidate-v7 model-selected trials. Correct retrieval "
        "coexists with interpretation errors. Overall scientific quality remains "
        "UNVERIFIED. "
        + (
            "Limited subject-matter feedback addressed one historical excerpt; "
            "no full scientific review or approval is claimed. "
            if "targeted_feedback" in agent_evaluation
            else "No full scientific review or approval is claimed. "
        )
        + "Not an official NOAA assessment."
    )
    document.add_paragraph(
        "Mission alignment: NEFSC's published mission is to provide scientific "
        "information and tools necessary for productive, sustainable, healthy "
        "marine ecosystems and coastal communities. This independent public-data "
        "prototype illustrates a research-access method; it is not NOAA endorsement. "
        "Reduced researcher effort is an intended benefit, not a measured result."
    )
    document.add_heading("Evidence at a glance", 1)
    document.add_paragraph(
        f"Supplied scripted MCP checks: {report['passed']}/{report['trial_count']} "
        "against independent public-CSV calculations. Candidate-v7 agent trials: "
        f"{agent_trials} completed, with {tool_calls['successful']} successful "
        f"calls out of {tool_calls['total']}; {tool_calls['failed']} malformed "
        "calls recovered. These are different kinds of evidence, not an agent grade."
    )
    document.add_paragraph(
        "The revised server now accepts exact returned species labels and offers "
        "curated, cited NOAA context cards. Candidate-v7 agent trials now include "
        "A02 and D01. D01 exercises the curated card, not live report discovery."
    )
    sections = [
        (
            "1. Overview and Objectives",
            [
                "Evaluate a local public-data server for Atlantic cod/haddock spring "
                "catch, matched comparisons and coverage. Fixed 2021-2025 slice; "
                "NOAA extraction June 25, 2026.",
                "Measure correct retrieval and explicit limits, not merely successful "
                "tool execution. No overall agent pass rate or MCP lift is claimed.",
                "Alignment: GSA Dataset Access Server track, using already-public "
                "government data in a sandbox prototype. Required outputs are a "
                "documented GitHub repository, deck with functionality demo, and "
                "evaluation document. The event specifies no "
                "public prototype deployment.",
                "The NEFSC mission connection is directly relevant: provide "
                "scientific information and tools for sustainable marine ecosystems "
                "and coastal communities. This prototype does not establish a "
                "measured time-to-insight improvement.",
            ],
        ),
        (
            "2. Testing Methodology",
            [
                "Framework & reproducibility: pytest edge cases plus a separate MCP "
                "stdio process. eval/run.py independently reads original CSVs and "
                "aggregates Decimal values without application query helpers.",
                "Golden dataset: eval/questions.json contains 12 versioned, rubric-"
                "bearing questions adapted to the public snapshot. The development/"
                "holdout split is prospective and visible, not blind. Each selected "
                "scripted case repeats three times; the runner supplies tool "
                "arguments.",
                f"Before/after: baseline {baseline['scripted_passed']}/"
                f"{baseline['scripted_trials']}; candidate "
                f"{candidate['scripted_passed']}/{candidate['scripted_trials']} "
                f"(development {candidate['development']['passed']}/"
                f"{candidate['development']['trials']}; prospective holdout "
                f"{candidate['holdout']['passed']}/{candidate['holdout']['trials']}). "
                "This checks deterministic MCP/data behavior, not an agent.",
                "Evaluators: exact identifier/count comparison; floating values use "
                "relative tolerance 1e-10 and absolute tolerance 1e-8. Validate tool "
                "output schemas and intended explicit error messages.",
                "Test design: invented fixtures cover null/zero/absent values, "
                "aliases, "
                "invalid scope, duplicate keys, orphan rows and atomic import failure.",
                "A shared eight-question development agent run supplied answers for "
                "public-CSV numerical checks on Q01, Q02, Q03, Q07, Q09 and Q10. "
                "The development tool traces, snapshot identity, and full scientific "
                "rubric remain unverified; see the public-data evidence appendix.",
                "The scripted public demo can export exact tool requests/results "
                "with public-source, database, and server hashes. Replay fails on "
                "source or response mismatch; it does not certify scientific validity.",
                "A supplied repeat set adds 3 trials each for NOAA A01/B01/C01 and "
                "Q01/Q02/Q03/Q05/Q07/Q08/Q09/Q10. This is 33 runs, not contiguous "
                "Q01-Q09; Q04/Q06 were omitted. The 76 successful payloads matched "
                "independent raw-CSV references. Six name errors (three Q02, three "
                "B01) recovered on retry; Q08 made no MCP call. No companion model "
                "configuration or evaluated database checksum was supplied.",
                f"Candidate-v7 adds {agent_trials} model-selected trials across "
                "15 questions with three repeats each. The recorded endpoint, "
                "options, question hash, server bundle and SQLite identity are "
                "consistent across batches; temperature was not recorded. These "
                "are new candidate-v7 results, not a matched comparison to the "
                "earlier model trials.",
                "Supplementary NOAA A01/B01/C01 cases are source-assisted, separate "
                "from the frozen 12 questions. The prompts supply report context; "
                "they do not measure autonomous report retrieval. C01 is a "
                "reconciliation-limits preflight, not the original full comparison.",
                "Template deviation: the upstream example recommends Phoenix, "
                "LangChain and LLM judges. This project uses a bounded model-selected "
                "MCP loop, MLflow traces and explicit manual review dimensions. "
                "No automated judge or Phoenix run is claimed. GSA requires "
                "evaluation methodology/results, not that specific framework.",
                "Prepared next experiment: a hardened-source agent rerun and an "
                "optional same-model no-tool arm. The latter retains dictionary "
                "context but has no numerical-data access; it measures access "
                "plus tooling, not MCP against equally informed SQL. Neither new "
                "run is claimed complete. Hash-bound analyst reviews separately "
                "assess numerical fidelity, missing/zero, ranking, provenance, "
                "causal claims, scope and tool use; scientific approval remains "
                "UNVERIFIED.",
            ],
        ),
        (
            "3. Performance Metrics",
            [
                f"Scripted conformance: {report['passed']}/{report['trial_count']} "
                "trials passed, including intended errors. See JSON case traces.",
                "Baseline/candidate comparison confirms no scripted regression; "
                "no LLM agent improvement is claimed.",
                f"Scripted benchmark environment: {json.dumps(report['environment'])}.",
                f"Candidate-v7 agent trials: {agent_trials}/{agent_trials} completed, "
                "which is execution completion, not answer correctness. Of "
                f"{tool_calls['total']} recorded MCP calls, "
                f"{tool_calls['successful']} succeeded and "
                f"{tool_calls['failed']} malformed search calls recovered. "
                "All trial scientific-review statuses remain UNVERIFIED.",
                "Tool payloads reviewed against the packaged references were "
                "consistent in the requested numerical cases. Final answers still "
                "include unsupported causal claims, a missing-versus-zero error, "
                "and an incorrect lowest-weight statement. No overall agent pass "
                "rate or independent CSV reprocessing is claimed.",
                "Failure analysis: inspect trial errors in the selected results "
                "JSON; intended scope/alias rejections are successes, not "
                "unexpected server failures.",
                "In historical A01 repeats, 395 matches 370 + 25, but the answer "
                "repeats "
                "the prompt's wrong page-1 locator (Overview is physical page 3).",
                "B01 repeats: correct data and recovered name error in all three; "
                "all three overstate what stratum counts show about area/cause.",
                "C01 repeats: all 18 payloads match independent CSV reference; "
                "answers decline haul reconciliation but overstate unit/method "
                "certainty. Full payloads are now available.",
                "Q02 repeats the same recovered label error 3/3. Q08 safely refuses "
                "without a tool call; scripted tests separately cover server behavior.",
                "Q10's empty stratum result is correct, but answers claim no tows or "
                "no effort, which the snapshot alone cannot establish.",
                f"All {agent_trials} candidate-v7 records say "
                "scientific_review=UNVERIFIED. Three repetitions per question on "
                "one endpoint are an observed sample, not a statistical reliability "
                "estimate, overall pass rate, or controlled before/after result.",
            ],
        ),
        (
            "4. Security Considerations",
            [
                "Data classification: only the official public extract and independent "
                "invented test fixtures. No internal records or credentials.",
                "Scope containment: fixed snapshot, read-only SQLite and bound "
                "parameters. No arbitrary SQL tool or runtime external connector.",
                "Preparation: fixed HTTPS URL, no redirects, size limits and pinned "
                "SHA-256. Ambiguous selected keys fail import.",
                "Transport: stdio by default; local HTTP is loopback-only. "
                "Platform ports and non-loopback binds fail closed unless the "
                "operator explicitly acknowledges trusted ingress. The setting "
                "does not authenticate callers.",
                "Container: digest-pinned images, locked dependencies, non-root "
                "runtime and read-only snapshot. CI is configured for a dependency "
                "audit with CycloneDX inventory, history secret scan and PR "
                "dependency review. The container build, runtime protections and "
                "MCP queries were verified locally; the GitHub workflow has not "
                "been run on this worktree.",
                "Historical boundary: candidate-v7 trials used FastMCP "
                f"{evaluated_fastmcp}; the later security dependency upgrade was "
                "tested separately and was not a model rerun.",
                "Future enterprise design: SSO for identity, separate per-tool and "
                "per-dataset authorization, approved egress, guardrails and auditable "
                "operations. These controls are planned, not implemented or assessed "
                "here; SSO alone is not data authorization.",
                "Evidence boundary: only public-source findings belong in the "
                "release. Credentials and raw account-specific traces are not "
                "included. Ingress authentication, injection resistance, multi-user "
                "authorization, privacy-reviewed logs, and production authorization "
                "were not established by these tests.",
            ],
        ),
        (
            "5. Lessons Learned & Recommendations",
            [
                "Successful data retrieval does not establish a correct explanation. "
                "Historical B01 recovered from a returned-label mismatch, then "
                "made unsupported "
                "interpretive claims. C01 found a valid boundary but overstated why "
                "it exists. A01 exposed an evaluator-authored citation error.",
                "The revised catch tools now accept exact returned labels; direct "
                "tests cover both species. New server caveats address area, empty "
                "station results and unknown units. Curated NOAA context cards "
                "cover 2023 and 2025 without live report retrieval. The candidate-v7 "
                "agent runs demonstrate card use and also expose interpretation "
                "errors; they do not prove the changes resolved those errors.",
                "Unknown measurements are not zeros. Catch totals and station counts "
                "are not standardized abundance indices. Published weight units "
                "remain unspecified in the linked metadata.",
                "Limitations: two species, five years, small datasets, and no "
                "full independent scientific review. The earlier repeat set lacks "
                "a verified evaluated database identity. Full representative-haul "
                "reconciliation remains "
                "unresolved. Do not convert unknown units into a claimed conversion.",
                "Future work: use the observed errors to guide expert review and "
                "candidate mitigations. Evaluate any changed prompt, schema or "
                "tool behavior in a matched study before claiming improvement.",
                "Future operating model: experts define and approve each versioned "
                "schema contract; developers implement bounded tools and regression "
                "tests; reviewers revalidate on source or methodology changes. "
                "The included example is provisional and has no expert approval.",
                "Release gates: confirm agency permission, repository visibility, "
                "participant-only upload route and current deadline cutoff; the "
                "public event page may lag participant updates. No push, public "
                "deployment or submission is performed by generating these files.",
            ],
        ),
    ]
    for heading, paragraphs in sections:
        document.add_heading(heading, 1)
        for text in paragraphs:
            document.add_paragraph(text)
    add_evidence_appendix(document, Path(__file__).with_name("schema-contract.md"))
    add_evidence_appendix(
        document, Path(__file__).with_name("public-evaluation-appendix.md")
    )
    add_agent_evaluation(document, agent_evaluation)
    document.add_heading("Sources and reproduction", 1)
    document.add_paragraph("https://www.fisheries.noaa.gov/inport/item/22561")
    document.add_paragraph(
        "https://www.fisheries.noaa.gov/about/northeast-fisheries-science-center"
    )
    document.add_paragraph(
        "https://www.fisheries.noaa.gov/new-england-mid-atlantic/ecosystems/"
        "2023-northeast-spring-bottom-trawl-survey-summary"
    )
    document.add_paragraph("https://repository.library.noaa.gov/view/noaa/72382")
    document.add_paragraph(f"Public archive SHA-256: {report['source_sha256']}")
    document.add_paragraph(
        "Scripted run evidence and reproduction details: submission/README.md."
    )
    document.add_paragraph(
        r"uv run python eval\run.py --archive C:\path\to\public-survey.zip "
        r"--output C:\path\to\new-scripted-results.json"
    )
    document.add_paragraph(
        r"Scripted MCP demo: uv run python submission\demo.py "
        r"--receipt C:\path\to\new-demo-receipt.json; replay with "
        r"--replay C:\path\to\new-demo-receipt.json. "
        r"(or .\.venv\Scripts\python.exe submission\demo.py on Windows)."
    )
    document.add_paragraph(
        "Read eval/README.md for the complete methodology and limits. "
        "Acknowledgement: NOAA/NMFS/NEFSC. Not official NOAA/DOC communication."
    )
    document.add_paragraph(
        "GSA instructions: "
        "https://www.gsa.gov/super-intelligence/si-community-of-practice/"
        "events-and-training/mcp-server-and-si-agent-government-hackathon"
    )
    document.add_paragraph(
        "Template alignment and release checklist: submission/README.md. "
        "Upstream: https://github.com/GSA-TTS/mcp-hackathon-template"
    )
    for section in document.sections:
        section.left_margin = section.right_margin = DocInches(0.8)
    document.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck-template", type=Path, required=True)
    parser.add_argument("--evaluation-template", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--agent-evaluation", type=Path, default=AGENT_EVALUATION_PATH)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("submission/candidate-v7")
    )
    args = parser.parse_args()
    report = json.loads(args.results.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    agent_evaluation = load_agent_evaluation(args.agent_evaluation)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    make_deck(
        args.deck_template,
        args.output_dir / "fisheries-deck.pptx",
        report,
        receipt,
        agent_evaluation,
    )
    make_document(
        args.evaluation_template,
        args.output_dir / "fisheries-evaluation.docx",
        report,
        agent_evaluation,
    )
    print("Generated fisheries-deck.pptx and fisheries-evaluation.docx.")


if __name__ == "__main__":
    main()
