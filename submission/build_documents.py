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
CURRENT_EVALUATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "eval"
    / "results"
    / "hardened-agent-evaluation.json"
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


def load_current_evaluation(path: Path = CURRENT_EVALUATION_PATH) -> dict:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    mcp = evidence["mcp"]
    no_tools = evidence["no_tools"]
    comparison = evidence["data_access_comparison"]
    review = evidence["answer_review"]
    issues = [issue for batch in review["batches"] for issue in batch["issues"]]
    issue_ids = [issue["trial"] for issue in issues]
    if (
        evidence["schema_version"] != 1
        or mcp["completed_trials"]
        != mcp["development_trials"]
        + mcp["holdout_trials"]
        + mcp["supplementary_trials"]
        or no_tools["completed_trials"]
        != no_tools["development_trials"] + no_tools["holdout_trials"]
        or not 0 <= mcp["tool_errors"] <= mcp["tool_calls"]
        or comparison["trials_per_arm"]
        != len(comparison["case_ids"]) * comparison["repeats_per_case"]
        or comparison["trials_per_arm"] > no_tools["completed_trials"]
        or comparison["trials_per_arm"] > mcp["completed_trials"]
        or not 0
        <= comparison["mcp_supplied_requested_result"]
        <= comparison["trials_per_arm"]
        or not 0
        <= comparison["no_tools_supplied_requested_result"]
        <= comparison["trials_per_arm"]
        or sum(batch["trials"] for batch in review["batches"])
        != mcp["completed_trials"]
        or len(issue_ids) != len(set(issue_ids))
        or len(issue_ids) != review["identified_issue_trials"]
        or any(issue["category"] not in {"cause", "unit"} for issue in issues)
        or review["other_trials_unverified"] != mcp["completed_trials"] - len(issue_ids)
        or review["scientific_review"] != "UNVERIFIED"
    ):
        raise ValueError("Current agent evaluation has inconsistent counts or review.")
    return evidence


def validate_evidence_sources(
    report: dict, current_evaluation: dict, receipt: dict | None = None
) -> None:
    source = current_evaluation["source"]
    if (
        report.get("evaluation_type") != "scripted_stdio_mcp_integration_not_agent"
        or report.get("source_sha256") != source["public_archive_sha256"]
        or report.get("database_sha256") != source["sqlite_sha256"]
        or (
            receipt is not None
            and (
                receipt["public_source"]["source_sha256"]
                != source["public_archive_sha256"]
                or receipt["database_sha256"] != source["sqlite_sha256"]
            )
        )
    ):
        raise ValueError("Scripted, demo and current agent evidence sources differ.")


def make_deck(
    template: Path,
    output: Path,
    report: dict,
    receipt: dict | None = None,
    agent_evaluation: dict | None = None,
    current_evaluation: dict | None = None,
) -> None:
    agent_evaluation = agent_evaluation or load_agent_evaluation()
    current_evaluation = current_evaluation or load_current_evaluation()
    validate_evidence_sources(report, current_evaluation, receipt)
    mcp = current_evaluation["mcp"]
    comparison = current_evaluation["data_access_comparison"]
    review = current_evaluation["answer_review"]
    issues = [issue for batch in review["batches"] for issue in batch["issues"]]
    causal_issues = sum(issue["category"] == "cause" for issue in issues)
    feedback = agent_evaluation.get("targeted_feedback")
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
        "Helping AI use public fisheries data responsibly.",
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
        "A public-data prototype, not an official NOAA assessment.",
        10,
        white,
    )

    slide = presentation.slides[1]
    start(slide, 2, "Fisheries data can be hard to use", "The challenge")
    card(
        slide,
        0.5,
        1.55,
        2.85,
        2.15,
        "THE QUESTION",
        "How can scientists find the data they need?",
    )
    card(
        slide,
        3.58,
        1.55,
        2.85,
        2.15,
        "THE RISK",
        "AI can mistake missing data for zero or catch for fish population.",
        gold,
    )
    card(
        slide,
        6.66,
        1.55,
        2.85,
        2.15,
        "THE GOAL",
        "Show the numbers, their source and their limits.",
        pale,
    )
    text(
        slide,
        0.56,
        4.19,
        8.8,
        0.55,
        "We hope to save researchers time; we have not measured that yet.",
        16,
        muted,
    )

    slide = presentation.slides[2]
    start(slide, 3, "Five tools for public fisheries data", "The solution")
    cards = [
        ("01  FIND", "Find the right fish."),
        ("02  SUMMARIZE", "Show catch and missing data."),
        ("03  COMPARE", "Compare two fish using the same filters."),
        ("04  COVERAGE", "Show station records and survey groups."),
        ("05  CONTEXT", "Show selected facts from NOAA reports."),
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
        "Report facts are selected summaries, not a live search or "
        "scientific approval.",
        11,
        muted,
    )

    slide = presentation.slides[3]
    start(slide, 4, "How the prototype works", "Architecture")
    stages = [
        ("PUBLIC DATA", "NOAA\nsurvey files"),
        ("PREPARE", "Check source\nand select data"),
        ("SNAPSHOT", "Local, read-only\ndatabase"),
        ("MCP TOOLS", "Find data\nand context"),
        ("AI CLIENT", "AI answer +\nhuman review"),
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
        "TODAY",
        "Use a public copy of the data on this computer.",
        pale,
    )
    card(
        slide,
        5.15,
        3.62,
        4.35,
        1.28,
        "LATER",
        "Approved access and security controls for internal data.",
        gold,
    )

    slide = presentation.slides[4]
    start(slide, 5, "A small public snapshot", "Technical decisions")
    card(slide, 0.5, 1.5, 2.85, 1.55, "2021-2025", "Spring surveys; cod and haddock.")
    card(slide, 3.58, 1.5, 2.85, 1.55, "1,570", "Station records in our data.")
    card(slide, 6.66, 1.5, 2.85, 1.55, "758", "Catch records in our data.")
    rectangle(slide, 0.5, 3.42, 9.0, 1.4, pale)
    text(
        slide,
        0.72,
        3.58,
        8.5,
        0.42,
        "Public data | works offline | read-only tools",
        14,
        ink,
    )
    text(
        slide,
        0.72,
        4.03,
        8.5,
        0.56,
        "Automated checks look for security issues. "
        "The server has no built-in sign-in.",
        12,
        ink,
    )

    slide = presentation.slides[5]
    start(
        slide,
        6,
        "Make the data understandable",
        "Technical decisions",
    )
    card(
        slide,
        0.5,
        1.48,
        4.35,
        2.8,
        "EXPLAIN THE DATA",
        "Show where the data came from and what we know about it.",
        pale,
    )
    card(
        slide,
        5.15,
        1.48,
        4.35,
        2.8,
        "ASK SCIENTISTS",
        "Scientists would check what the numbers mean and how to use them.",
        gold,
    )
    text(
        slide,
        0.56,
        4.65,
        8.9,
        0.38,
        "Scientists have not approved this example; the review process is not "
        "yet in place.",
        15,
        muted,
    )

    slide = presentation.slides[6]
    start(
        slide,
        7,
        "Clear questions, clear boundaries",
        "Technical decisions",
    )
    card(
        slide,
        0.5,
        1.55,
        2.85,
        2.35,
        "SET LIMITS",
        "Only ask for fish and years in this dataset.",
    )
    card(
        slide,
        3.58,
        1.55,
        2.85,
        2.35,
        "MISSING DATA",
        "Missing data stays unknown; it is not treated as zero.",
        pale,
    )
    card(
        slide,
        6.66,
        1.55,
        2.85,
        2.35,
        "ASK SCIENTISTS",
        "Review what the data means when sources change.",
    )
    text(
        slide,
        0.55,
        4.3,
        8.9,
        0.55,
        "This expert-review process is planned, not yet in place.",
        15,
        muted,
    )

    slide = presentation.slides[7]
    start(
        slide,
        8,
        "Demo: a question with a trap",
        "Scripted public-data demo",
    )
    rectangle(slide, 0.5, 1.39, 5.42, 2.58, light)
    text(
        slide,
        0.7,
        1.56,
        5.0,
        0.27,
        "FIND COD  >  SHOW CATCH  >  ADD CONTEXT",
        12,
        teal,
        True,
    )
    columns = [
        (0.7, 0.7, "YEAR", "2022", "2023"),
        (1.55, 1.2, "WEIGHT*", "609.780", "416.396"),
        (3.0, 1.65, "STATION RECORDS", "378", "77"),
        (4.8, 0.8, "GROUPS", "82", "13"),
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
        "* Expanded weight; unit unknown. Groups are survey strata.",
        11,
        muted,
    )
    card(
        slide,
        6.15,
        1.39,
        3.35,
        2.58,
        "NOAA CONTEXT",
        "NOAA: 70 of 377 planned trawl stations.\n\n"
        "That is not the same count as the 77 station records in our data.",
        pale,
    )
    text(
        slide,
        0.55,
        4.28,
        8.9,
        0.64,
        "The survey changed. That is context, not proof of why catch differed.",
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
        "This example is scripted; it is not an AI-selected answer.",
        10,
        muted,
    )

    slide = presentation.slides[8]
    start(
        slide,
        9,
        "How did we check it?",
        "Evaluation",
    )
    card(
        slide,
        0.5,
        1.55,
        2.85,
        2.28,
        "1  CHECK THE EDGES",
        "Try missing data, invalid requests and import errors.",
    )
    card(
        slide,
        3.58,
        1.55,
        2.85,
        2.28,
        "2  CHECK DATA",
        "Compare tool results with a separate calculation from NOAA files.",
        pale,
    )
    card(
        slide,
        6.66,
        1.55,
        2.85,
        2.28,
        "3  CHECK AI ANSWERS",
        "Let the AI use the tools, then review its answers.",
    )
    text(
        slide,
        0.55,
        4.18,
        8.9,
        0.66,
        "Questions were repeated three times and were visible, not secret.",
        15,
        muted,
    )

    slide = presentation.slides[9]
    start(
        slide,
        10,
        "Getting data is only the first step",
        "Current evaluation",
    )
    metrics = [
        (
            f"{report['passed']}/{report['trial_count']}",
            "scripted tool checks passed",
        ),
        (str(mcp["completed_trials"]), "AI trials with tools"),
        (
            f"{mcp['tool_calls'] - mcp['tool_errors']}/{mcp['tool_calls']}",
            "tool calls had no errors",
        ),
        (
            f"{comparison['mcp_supplied_requested_result']}/"
            f"{comparison['trials_per_arm']}",
            "requested result included",
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
        f"Without tools: {comparison['no_tools_supplied_requested_result']}/"
        f"{comparison['trials_per_arm']}; that AI had no access to the records.",
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
        "This checks data access, not whether every answer is correct.",
        15,
    )
    text(
        slide,
        0.55,
        4.42,
        8.8,
        0.5,
        f"{len(comparison['case_ids'])} questions, "
        f"{comparison['repeats_per_case']} tries each; "
        "the questions were visible, not secret.",
        15,
        muted,
    )
    text(
        slide,
        0.55,
        5.02,
        8.8,
        0.34,
        f"The {mcp['tool_calls']} calls came from the {mcp['completed_trials']} "
        "main AI trials; extra test runs are separate.",
        11,
        muted,
    )

    slide = presentation.slides[10]
    start(slide, 11, "The AI spotted a useful clue", "Answer review")
    findings = [
        (
            f"{causal_issues} ANSWERS",
            "Linked lower catches to reduced sampling; that context matters.",
        ),
        (
            "DATA CHECK",
            "Checked tool results matched calculations from NOAA files.",
        ),
        (
            f"{review['other_trials_unverified']} OTHER",
            "Not fully reviewed; no pass or fail claim.",
        ),
        ("NEXT", "Ask scientists to check how strongly we explain the results."),
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
        "The catch comparison cannot measure how much sampling explains. "
        "Review was partial and AI-assisted.",
        13,
        muted,
    )

    slide = presentation.slides[11]
    start(
        slide,
        12,
        "Useful access, with scientists in the loop",
        "Mission and next steps",
    )
    card(
        slide,
        0.5,
        1.48,
        4.35,
        2.43,
        "THE MISSION",
        "Make fisheries data easier to use to support healthy oceans.",
        pale,
    )
    card(
        slide,
        5.15,
        1.48,
        4.35,
        2.43,
        "BEFORE INTERNAL USE",
        "Scientists review the meaning; approved access and security are needed.",
        gold,
    )
    text(
        slide,
        0.55,
        4.22,
        8.9,
        0.46,
        (
            "We received limited feedback on one earlier claim. "
            "This is not scientific approval."
            if feedback is not None
            else "This is not scientific approval or a system ready for internal use."
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
        "Fisheries scientists study the ocean to support healthy fish populations "
        "and sustainable fishing. Our prototype helps an AI assistant find "
        "public NOAA survey data and understand what the numbers can tell us.",
        "Finding the right data can take work, and an AI can sound confident "
        "even when it gets the meaning wrong. We want to make the data easier "
        "to find while keeping its source and limits visible.",
        "These five read-only tools help the assistant find a fish, show and "
        "compare catches, count survey records, and share selected facts from "
        "NOAA reports. The data cover cod and haddock from 2021 through 2025.",
        "The server uses a public copy of NOAA data on this computer. It does "
        "not connect to our private database. Any internal use would need "
        "approved access and security controls.",
        "This is a small, fixed selection of public survey records for cod and "
        "haddock. The tools cannot change the data. The server has no built-in "
        "sign-in, so this is not a system ready for internal use.",
        "We want the assistant to show where a number came from, what it "
        "means, and what is missing. This is an early example: a scientist "
        "still needs to check what the numbers mean and how they should be used.",
        "The server limits requests to the fish and years in this public "
        "dataset. It keeps missing values visible instead of turning them into "
        "zeros. We plan to work with scientists on a review process; that "
        "process is not in place yet.",
        "This is a scripted example using the real server, not an AI-selected "
        "answer. It compares cod catch in 2022 and 2023. The lower total does "
        "not prove the fish population declined or explain why catch differed. "
        "The weight unit is unknown, and NOAA's 70 trawl stations are not the "
        "same count as our 77 station records. The survey groups counted here "
        "are not a measure of geographic area.",
        "We try difficult cases, compare tool results with separate calculations "
        "from NOAA files, and review AI answers. The questions were repeated "
        "three times and were visible, not a blind test.",
        (
            f"Across {mcp['completed_trials']} main trials, all "
            f"{mcp['tool_calls'] - mcp['tool_errors']} recorded tool calls "
            "returned without an error. For "
            f"{len(comparison['case_ids'])} questions repeated "
            f"{comparison['repeats_per_case']} times, the AI with tools "
            "included the requested result in "
            f"{comparison['mcp_supplied_requested_result']} of "
            f"{comparison['trials_per_arm']} answers; without access to the "
            "records, the no-tool arm included it in "
            f"{comparison['no_tools_supplied_requested_result']} of "
            f"{comparison['trials_per_arm']}. This shows data access, not an "
            "overall accuracy rate. The checked numerical tool results matched "
            "separate calculations from original NOAA files. The questions "
            "were visible, not a blind test."
        ),
        (
            f"In {causal_issues} reviewed answers, the AI linked lower catches "
            "to reduced sampling. That's useful context for interpreting the "
            "result, but these catch totals cannot measure how much sampling "
            "explains. "
            "This partial review was AI-assisted, not a "
            "scientific verdict; "
            f"{review['other_trials_unverified']} other "
            "trials were not fully reviewed. Fisheries scientists should help "
            "check the interpretation."
        ),
        (
            "Our goal is to help scientists find useful data and see its "
            "limits. This is not an official NOAA assessment or scientific "
            "approval. Before internal use, we would need scientific review "
            "and approved access and security controls."
        ),
    ]
    for slide, note in zip(presentation.slides, notes, strict=True):
        slide.notes_slide.notes_text_frame.text = note
    presentation.save(output)


def make_video_deck(source: Path, output: Path) -> None:
    presentation = Presentation(source)
    if len(presentation.slides) != 12:
        raise ValueError("The full deck must contain 12 slides.")
    keep = {0, 2, 7, 9, 10, 11}
    # python-pptx has no public slide-deletion API.
    for index in reversed(range(len(presentation.slides))):
        if index not in keep:
            slide_id = presentation.slides._sldIdLst[index]
            presentation.slides._sldIdLst.remove(slide_id)
            presentation.part.drop_rel(slide_id.rId)
    for number, slide in enumerate(presentation.slides, start=1):
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text.startswith("PUBLIC NOAA SNAPSHOT"):
                paragraph = shape.text_frame.paragraphs[0]
                paragraph.runs[0].text = (
                    "PUBLIC NOAA SNAPSHOT  |  EVIDENCE-AWARE FISHERIES MCP"
                    f"    {number:02}"
                )
    demo = presentation.slides[2]
    replacements = {
        "SCRIPTED PUBLIC-DATA DEMO": "LIVE DEMO  |  PUBLIC DATA",
        "FIND COD  >  SHOW CATCH  >  ADD CONTEXT": (
            "REFERENCE VALUES FROM OUR PUBLIC DATA"
        ),
        "This example is scripted; it is not an AI-selected answer.": (
            "Reference values shown; the live recording is a separate example."
        ),
    }
    for shape in demo.shapes:
        if shape.has_text_frame and shape.text in replacements:
            shape.text_frame.paragraphs[0].runs[0].text = replacements.pop(shape.text)
    if replacements:
        raise ValueError("Video demo slide changed; review its labels.")
    demo.notes_slide.notes_text_frame.text = (
        "Play your live demo recording here. We ask the assistant to find cod "
        "and compare catch in 2022 and 2023. This question has a trap: a lower "
        "catch does not necessarily mean fewer fish in the ocean. NOAA's 2023 "
        "survey was shortened. That is relevant context, but these catch totals "
        "alone cannot show how much survey changes explain the difference. "
        "We check the tool calls, numbers, sources and limitations. This is one "
        "live example, separate from the evaluation."
    )
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
    current_evaluation: dict | None = None,
) -> None:
    agent_evaluation = agent_evaluation or load_agent_evaluation()
    current_evaluation = current_evaluation or load_current_evaluation()
    validate_evidence_sources(report, current_evaluation)
    mcp = current_evaluation["mcp"]
    no_tools = current_evaluation["no_tools"]
    comparison = current_evaluation["data_access_comparison"]
    review = current_evaluation["answer_review"]
    issues = [issue for batch in review["batches"] for issue in batch["issues"]]
    causal_issues = sum(issue["category"] == "cause" for issue in issues)

    document = Document(template)
    document.core_properties.title = "NOAA Fisheries Data Gateway: Evaluation"
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.subject = ""
    document.core_properties.keywords = ""
    document.core_properties.comments = ""
    normal = next(style for style in document.styles if style.style_id == "Normal")
    normal.font.size = DocPt(10)
    normal.paragraph_format.space_after = DocPt(4)
    normal.paragraph_format.line_spacing = 1.08
    for name, size in (("Heading 1", 15), ("Heading 2", 12)):
        document.styles[name].font.size = DocPt(size)
    for element in list(document.element.body):
        if not element.tag.endswith("}sectPr"):
            document.element.body.remove(element)

    document.add_heading("NOAA Fisheries Data Gateway: Evaluation", 0)
    document.add_paragraph("GSA MCP and AI Agent Hackathon")
    document.add_paragraph(
        "A read-only prototype helps AI assistants retrieve public NOAA survey "
        "data. The results are not an official NOAA assessment."
    )
    sections = [
        (
            "1. Overview and Objectives",
            [
                "Make public cod and haddock data easier to find while showing "
                "sources, survey coverage and scientific limits. The fixed snapshot "
                "covers spring 2021-2025.",
                "This supports research access; time savings have not been measured.",
            ],
        ),
        (
            "2. Testing Methodology",
            [
                "We tested missing data and invalid requests, then ran 12 scripted "
                "MCP questions three times each. An independent calculation from "
                "the NOAA CSV files supplied the reference values.",
                f"The AI chose its own tools in {mcp['completed_trials']} main "
                "trials. A separate no-tool arm completed "
                f"{no_tools['completed_trials']} trials. Each arm also had one "
                "smoke trial.",
                "For paired questions, both arms had the same model endpoint and "
                "data dictionary. The no-tool arm had no underlying records and "
                "different access instructions. Questions were repository-visible, "
                "not a blind test.",
                "We checked tool data against independently recalculated values "
                "and partially reviewed the AI's answers. This review was "
                "AI-assisted, not independent scientific review.",
            ],
        ),
        (
            "3. Performance Metrics",
            [
                f"Scripted tools: {report['passed']}/{report['trial_count']} checks "
                "passed. These test tools, not AI reasoning.",
                f"AI with MCP: {mcp['completed_trials']} main trials completed; "
                f"{mcp['tool_calls'] - mcp['tool_errors']}/{mcp['tool_calls']} "
                "recorded tool calls returned without an error.",
                f"Data access: for {len(comparison['case_ids'])} questions repeated "
                f"{comparison['repeats_per_case']} times, MCP supplied the requested "
                f"result in {comparison['mcp_supplied_requested_result']}/"
                f"{comparison['trials_per_arm']} trials; the no-tool arm supplied it "
                f"in {comparison['no_tools_supplied_requested_result']}/"
                f"{comparison['trials_per_arm']}. This includes no-record results "
                "and measures result presence, not overall accuracy or an MCP "
                "advantage over equally informed SQL or files.",
                f"Answer review: {causal_issues} answers linked lower catches to "
                "reduced sampling. This is useful context, although the totals "
                "cannot measure how much it explains; the review flagged how "
                "strongly some explanations were stated. "
                "The "
                f"{review['other_trials_unverified']} trials were not fully "
                "reviewed. This partial AI-assisted review is not an overall "
                "accuracy score or scientific approval. Scientific review "
                "remains UNVERIFIED.",
            ],
        ),
        (
            "4. Security Considerations",
            [
                "The server uses a fixed public snapshot, read-only queries and "
                "bounded tools. It has no arbitrary SQL tool.",
                "The container uses a non-root user and pinned dependencies. "
                "HTTP defaults to local access; an ingress setting does not "
                "authenticate users. CI includes tests and security checks.",
                "Authentication, data authorization and audit controls for "
                "internal use are future work, not established by this prototype.",
            ],
        ),
        (
            "5. Lessons Learned & Recommendations",
            [
                "The AI's use of survey context helps readers interpret catches, "
                "but the totals cannot measure the effect of survey changes.",
                (
                    "Limited subject-matter feedback concerned one historical "
                    "excerpt, not the full evaluation. No scientific approval "
                    "is claimed."
                    if "targeted_feedback" in agent_evaluation
                    else "No scientific approval is claimed."
                ),
                "Have scientists review interpretations before research use. "
                "Test any future changes before claiming improvement.",
            ],
        ),
    ]
    for heading, paragraphs in sections:
        paragraph = document.add_heading(heading, 1)
        if heading == "4. Security Considerations":
            paragraph.paragraph_format.page_break_before = True
        for text in paragraphs:
            document.add_paragraph(text)
    document.add_heading("Sources and details", 1)
    document.add_paragraph(
        "NOAA metadata: https://www.fisheries.noaa.gov/inport/item/22561"
    )
    document.add_paragraph(
        "Repository: eval/results/hardened-agent-evaluation.json contains the "
        "current run details and review limits. Earlier evidence is preserved "
        "in eval/results/candidate-v7-agent-evaluation.json."
    )
    document.add_paragraph(
        "Method, source links and reproduction: eval/README.md and "
        "submission/README.md. Raw account-specific exports are not included."
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
        "--current-evaluation", type=Path, default=CURRENT_EVALUATION_PATH
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("submission/candidate-v7")
    )
    args = parser.parse_args()
    report = json.loads(args.results.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    agent_evaluation = load_agent_evaluation(args.agent_evaluation)
    current_evaluation = load_current_evaluation(args.current_evaluation)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    make_deck(
        args.deck_template,
        args.output_dir / "fisheries-deck.pptx",
        report,
        receipt,
        agent_evaluation,
        current_evaluation,
    )
    make_video_deck(
        args.output_dir / "fisheries-deck.pptx",
        args.output_dir / "fisheries-video-deck.pptx",
    )
    make_document(
        args.evaluation_template,
        args.output_dir / "fisheries-evaluation.docx",
        report,
        agent_evaluation,
        current_evaluation,
    )
    print("Generated the full deck, video deck and evaluation document.")


if __name__ == "__main__":
    main()
