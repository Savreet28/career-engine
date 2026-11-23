"""
docs/make_guide.py
==================

Generates docs/Career-Engine-Guide.pdf -- a plain-language walkthrough of the
project's workflow and every feature, written for a teammate or an examiner.

Run from the project root with the backend virtualenv (reportlab lives in
requirements-dev.txt):

    backend/.venv/bin/python docs/make_guide.py

Notes on rendering, learned the hard way:
  * ReportLab's built-in fonts use WinAnsi encoding, which has NO arrow glyph.
    Arrows are therefore DRAWN as shapes, never typed. Bullets, dashes and
    curly quotes are fine.
  * A Paragraph collapses runs of spaces, so code blocks convert them to
    non-breaking spaces or the alignment is lost.
  * Page breaks are used only at Part boundaries. Forcing one before every
    feature left near-empty stub pages wherever a section overflowed.
"""

import pathlib

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

OUT = pathlib.Path(__file__).parent / "Career-Engine-Guide.pdf"

INK = colors.HexColor("#0f1829")
ACCENT = colors.HexColor("#2f6fe4")
ACCENT_SOFT = colors.HexColor("#e8f0fe")
ACCENT_DARK = colors.HexColor("#1d54bd")
GOOD = colors.HexColor("#15803d")
WARN = colors.HexColor("#b45309")
GREY = colors.HexColor("#5b6677")
LIGHT = colors.HexColor("#f4f6fa")
LINE = colors.HexColor("#d4dae5")

CONTENT_WIDTH = A4[0] - 36 * mm


def build_styles():
    add = lambda **kw: ParagraphStyle(**kw)
    getSampleStyleSheet()
    return {
        "cover_title": add(name="ct", fontName="Helvetica-Bold", fontSize=34,
                           leading=38, textColor=INK, spaceAfter=6),
        "cover_sub": add(name="cs", fontName="Helvetica", fontSize=14, leading=20,
                         textColor=ACCENT_DARK, spaceAfter=18),
        "cover_body": add(name="cb", fontName="Helvetica", fontSize=10.5,
                          leading=16, textColor=GREY),
        "h1": add(name="h1", fontName="Helvetica-Bold", fontSize=18, leading=22,
                  textColor=INK, spaceBefore=4, spaceAfter=3),
        "h1num": add(name="h1n", fontName="Helvetica-Bold", fontSize=10, leading=12,
                     textColor=ACCENT, spaceAfter=2),
        "h2": add(name="h2", fontName="Helvetica-Bold", fontSize=12, leading=15,
                  textColor=ACCENT_DARK, spaceBefore=12, spaceAfter=4),
        "h3": add(name="h3", fontName="Helvetica-Bold", fontSize=10, leading=13,
                  textColor=INK, spaceBefore=8, spaceAfter=3),
        "body": add(name="bd", fontName="Helvetica", fontSize=9.8, leading=14.5,
                    textColor=colors.HexColor("#243040"), spaceAfter=7),
        "bullet": add(name="bl", fontName="Helvetica", fontSize=9.6, leading=13.6,
                      textColor=colors.HexColor("#243040"), leftIndent=12,
                      bulletIndent=2, spaceAfter=3.5),
        "small": add(name="sm", fontName="Helvetica", fontSize=8.6, leading=12,
                     textColor=GREY, spaceAfter=5),
        "cell": add(name="cl", fontName="Helvetica", fontSize=8.7, leading=12,
                    textColor=colors.HexColor("#243040")),
        "cellb": add(name="clb", fontName="Helvetica-Bold", fontSize=8.7, leading=12,
                     textColor=INK),
        "cellhead": add(name="clh", fontName="Helvetica-Bold", fontSize=8.4,
                        leading=11, textColor=colors.white),
        "mono": add(name="mn", fontName="Courier", fontSize=8.6, leading=12.6,
                    textColor=colors.HexColor("#1b2430")),
        "callout": add(name="co", fontName="Helvetica", fontSize=9.2, leading=13.5,
                       textColor=colors.HexColor("#243040")),
        "centre": add(name="ce", fontName="Helvetica", fontSize=9, leading=13,
                      textColor=GREY, alignment=TA_CENTER),
    }


ST = build_styles()


def rule(colour=ACCENT, width=CONTENT_WIDTH, thickness=1.6):
    d = Drawing(width, thickness + 1)
    d.add(Line(0, 1, width, 1, strokeColor=colour, strokeWidth=thickness))
    return d


def heading(number, title):
    return KeepTogether([Paragraph(number.upper(), ST["h1num"]),
                         Paragraph(title, ST["h1"]), rule(), Spacer(1, 8)])


def bullets(items):
    return [Paragraph(t, ST["bullet"], bulletText="•") for t in items]


def table(rows, widths, head=True, align_right=None):
    data = []
    for r_i, row in enumerate(rows):
        out = []
        for c_i, cell in enumerate(row):
            style = "cellhead" if (head and r_i == 0) else ("cellb" if c_i == 0 else "cell")
            out.append(Paragraph(str(cell), ST[style]))
        data.append(out)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
             ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
             ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
             ("BOX", (0, 0), (-1, -1), 0.6, LINE)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT_DARK))
        for i in range(1, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    for col in align_right or []:
        style.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle(style))
    return t


def callout(title, body, tone="accent"):
    bg, bar = {"accent": (ACCENT_SOFT, ACCENT),
               "good": (colors.HexColor("#eaf7ef"), GOOD),
               "warn": (colors.HexColor("#fdf3e3"), WARN)}[tone]
    inner = [Paragraph(f"<b>{title}</b>", ST["h3"]), Paragraph(body, ST["callout"])]
    t = Table([[inner]], colWidths=[CONTENT_WIDTH], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                           ("LEFTPADDING", (0, 0), (-1, -1), 11),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    return t


def code(lines):
    def esc(line):
        return (line.replace("&", "&amp;").replace("<", "&lt;").replace(" ", "&nbsp;"))
    body = "<br/>".join(esc(l) for l in lines)
    t = Table([[Paragraph(body, ST["mono"])]], colWidths=[CONTENT_WIDTH], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f3f8")),
                           ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                           ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    return t


def _down_arrow(d, x, y, length):
    d.add(Line(x, y, x, y - length + 5, strokeColor=ACCENT, strokeWidth=1.3))
    d.add(Polygon([x - 3.5, y - length + 6, x + 3.5, y - length + 6, x, y - length],
                  fillColor=ACCENT, strokeColor=ACCENT))


def flow_down(steps, width=CONTENT_WIDTH, box_h=30, gap=12):
    total = len(steps) * box_h + (len(steps) - 1) * gap
    d = Drawing(width, total)
    box_w = width * 0.82
    x0 = (width - box_w) / 2
    y = total
    for i, (label, note) in enumerate(steps):
        y -= box_h
        d.add(Rect(x0, y, box_w, box_h, rx=4, ry=4, fillColor=colors.white,
                   strokeColor=ACCENT, strokeWidth=1.1))
        if note:
            d.add(String(x0 + 13, y + box_h - 12, label, fontName="Helvetica-Bold",
                         fontSize=9.2, fillColor=INK))
            d.add(String(x0 + 13, y + 8, note, fontName="Helvetica", fontSize=7.8,
                         fillColor=GREY))
        else:
            d.add(String(x0 + 13, y + box_h / 2 - 3, label, fontName="Helvetica-Bold",
                         fontSize=9.2, fillColor=INK))
        if i < len(steps) - 1:
            _down_arrow(d, width / 2, y, gap)
            y -= gap
    return d


def fan_out(width=CONTENT_WIDTH):
    h = 125
    d = Drawing(width, h)
    box_w, box_h = width * 0.34, 36
    d.add(Rect((width - box_w) / 2, h - box_h, box_w, box_h, rx=4, ry=4,
               fillColor=ACCENT_DARK, strokeColor=ACCENT_DARK))
    for i, line in enumerate(["Resume + GitHub + Role", "+ Experience + Job Description"]):
        d.add(String(width / 2, h - 14 - i * 11, line, textAnchor="middle",
                     fontName="Helvetica-Bold", fontSize=8.2, fillColor=colors.white))
    labels = ["ATS Score", "Job Match", "Role Fit", "Roadmap", "Interview Prep"]
    notes = ["0-100", "0-100", "all 6 roles", "phased plan", "likely questions"]
    out_w = width / 5 - 7
    for i in range(5):
        x = i * (out_w + 8.75)
        d.add(Line(width / 2, h - box_h, x + out_w / 2, 46, strokeColor=ACCENT,
                   strokeWidth=1.0))
        d.add(Polygon([x + out_w / 2 - 3.5, 46, x + out_w / 2 + 3.5, 46,
                       x + out_w / 2, 40], fillColor=ACCENT, strokeColor=ACCENT))
        d.add(Rect(x, 6, out_w, 34, rx=4, ry=4, fillColor=colors.white,
                   strokeColor=ACCENT, strokeWidth=1.1))
        d.add(String(x + out_w / 2, 26, labels[i], textAnchor="middle",
                     fontName="Helvetica-Bold", fontSize=8, fillColor=INK))
        d.add(String(x + out_w / 2, 14, notes[i], textAnchor="middle",
                     fontName="Helvetica", fontSize=7, fillColor=GREY))
    return d


def decorate(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Helvetica", 7.8)
        canvas.setFillColor(GREY)
        canvas.drawString(18 * mm, 12 * mm, "Career Engine - Workflow & Feature Guide")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, str(doc.page))
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 15.5 * mm, A4[0] - 18 * mm, 15.5 * mm)
    canvas.restoreState()


def story():
    s = []

    # ============================== COVER ==============================
    s += [
        Spacer(1, 30 * mm),
        Paragraph("Career Engine", ST["cover_title"]),
        Paragraph("Workflow &amp; Feature Guide", ST["cover_sub"]),
        rule(thickness=2.4), Spacer(1, 12),
        Paragraph(
            "A local web application that analyses a student's resume, GitHub profile "
            "and target job role. It returns a transparent ATS score, an explainable "
            "job match built with RAG over job-description data, and a plan for "
            "closing the gaps it finds.", ST["cover_body"]),
        Spacer(1, 14),
        callout("The one thing to remember",
                "Every number and every sentence this application produces is computed "
                "by rules you can read in the source code. <b>No language model is used "
                "anywhere.</b> The same resume always produces the same result, and "
                "every point traces back to the exact text that earned it.", "good"),
        Spacer(1, 14),
        table([
            ["Objective 1", "Analyse a resume, GitHub profile and target job role to "
                            "generate an ATS score"],
            ["Objective 2", "Use RAG over job-description data for explainable "
                            "job/role matching"],
            ["Objective 3", "Career recommendations, a learning roadmap and interview "
                            "preparation"],
        ], [28 * mm, CONTENT_WIDTH - 28 * mm], head=False),
        Spacer(1, 10),
        table([
            ["At a glance", "", "", ""],
            ["112 skills in the taxonomy", "12 job descriptions", "261 vector chunks",
             "384 dimensions"],
            ["9 ATS components", "4 match components", "87 prerequisite edges",
             "65 interview questions"],
            ["17 API endpoints", "9 pipeline stages", "213 automated tests",
             "0 language models"],
        ], [CONTENT_WIDTH / 4] * 4),
        PageBreak(),
    ]

    # ============================== PART 1 ==============================
    s += [heading("Part 1", "What the project does")]
    s += [Paragraph(
        "Most job applications are filtered by an Applicant Tracking System (ATS) "
        "before a human ever reads them. Students get rejected with no idea why. The "
        "tools that claim to help are opaque: they either return a score with no "
        "explanation, or they hand the whole resume to an AI model and repeat whatever "
        "it says. Neither tells a student what to actually change.", ST["body"])]
    s += [Paragraph(
        "Career Engine takes the opposite approach. A student gives it five things and "
        "gets back five, and every part of the answer traces to a rule.", ST["body"])]
    s += [Spacer(1, 6), fan_out(), Spacer(1, 14)]

    s += [Paragraph("What you give it", ST["h2"])]
    s += bullets([
        "<b>Resume</b> - a PDF or DOCX file (required)",
        "<b>GitHub username</b> - optional, but it adds evidence that backs up what "
        "the resume claims",
        "<b>Target job role</b> - one of six, e.g. AI/ML Engineer, Backend Developer",
        "<b>Experience level</b> - Fresher, 2-4 years, or 5+ years",
        "<b>Job description</b> - pasted from the posting being applied to",
    ])
    s += [Paragraph("What you get back", ST["h2"])]
    s += bullets([
        "<b>An ATS score out of 100</b> from nine weighted components, each showing "
        "the points earned, the reason, and the literal text that earned them.",
        "<b>A job match score out of 100.</b> The requirements being measured are "
        "pulled out of real job-description passages found by semantic search.",
        "<b>A role-fit ranking</b> across all six roles, because your resume may suit "
        "a different one better than the one you picked.",
        "<b>A learning roadmap</b> ordering the gaps by what unlocks what.",
        "<b>Interview questions</b> you are likely to face, split into skills you can "
        "defend and skills you cannot yet.",
    ])

    s += [Spacer(1, 4), Paragraph("The distinction that matters", ST["h2"])]
    s += [table([
        ["Output", "How it is produced"],
        ["ATS score", "A deterministic, rule-based calculation over the fields pulled "
                      "out of the resume."],
        ["Job match score", "A fixed weighted formula comparing the candidate's "
                            "evidence against requirements retrieved by RAG."],
        ["Roadmap and prep", "Ordered by a prerequisite graph and by how strongly the "
                             "retrieved job descriptions demanded each skill."],
    ], [34 * mm, CONTENT_WIDTH - 34 * mm])]
    s += [Spacer(1, 10), Paragraph(
        "Nothing in that table involves artificial intelligence making a judgement. "
        "That is deliberate: the score is <b>reproducible</b> (anyone can recompute it "
        "by hand from the report) and <b>defensible</b> (every point is attributable "
        "to a named rule).", ST["body"])]
    # No break: Part 1 overflows by two lines, and a forced break
    # here left a page containing only those two lines.
    s += [Spacer(1, 20)]

    # ============================== PART 2 ==============================
    s += [heading("Part 2", "The workflow, step by step")]
    s += [Paragraph(
        "When the user clicks <b>Analyze</b>, the backend runs nine stages in order. "
        "This is one function in <font name='Courier' size='9'>backend/main.py</font> "
        "called <font name='Courier' size='9'>run_pipeline()</font>, written as a "
        "generator - meaning it reports progress as it goes rather than going silent "
        "until finished. That is how the loading screen shows real stages instead of a "
        "fake progress bar. The whole pipeline takes about 300 milliseconds.",
        ST["body"])]
    s += [Spacer(1, 6)]
    s += [flow_down([
        ("1.  Parse the resume", "PDF or DOCX into structured fields"),
        ("2.  Analyse GitHub", "public repositories into skill evidence"),
        ("3.  Retrieve JD evidence", "semantic search over job descriptions"),
        ("4.  Calculate the ATS score", "nine weighted rules"),
        ("5.  Match against requirements", "evidence vs what was retrieved"),
        ("6.  Rank all six roles", "which role actually fits best"),
        ("7.  Build the roadmap", "order the gaps by what unlocks what"),
        ("8.  Select interview questions", "by skill tag and experience level"),
        ("9.  Build the summary", "three sections of bullets"),
    ], box_h=27, gap=10)]
    s += [Spacer(1, 12)]
    s += [callout(
        "The idea that holds it all together: one shared vocabulary",
        "A file called <font name='Courier' size='8.6'>skills_data.py</font> defines "
        "112 skills, each with its alternative spellings - \"JavaScript\" also matches "
        "\"js\", \"React\" also matches \"reactjs\". Resume text, GitHub data, job "
        "descriptions and interview questions are <b>all</b> translated into these same "
        "names. That is what makes \"Python in the resume\", \"Python on GitHub\" and "
        "\"Python required by the job\" directly comparable - they are literally the "
        "same word by the time they are compared.")]
    s += [Spacer(1, 18)]

    # ============================== FEATURE 1 ==============================
    s += [heading("Feature 1", "Resume parsing")]
    s += [Paragraph("<b>What it does.</b> Turns an uploaded PDF or DOCX into organised "
                    "data the rest of the system can work with.", ST["body"])]
    s += [Paragraph("How it works", ST["h2"])]
    s += bullets([
        "<b>Read the text.</b> pdfplumber for PDFs, python-docx for Word files, "
        "including tables, since students often put skills in them.",
        "<b>Find the sections.</b> Headings vary enormously, so a vocabulary maps them "
        "to standard names - \"EDUCATION\", \"Academic Background\" and "
        "\"Qualifications\" all become <i>education</i>.",
        "<b>Pull out the fields.</b> Patterns find the email, phone, LinkedIn and "
        "GitHub links, degrees and CGPA. The shared vocabulary finds skills.",
        "<b>Separate claimed from demonstrated.</b> Skills in a Skills section are "
        "tracked apart from skills mentioned inside a project description.",
        "<b>Spot quantified achievements.</b> Lines containing a real number. "
        "Education percentages are excluded - a CGPA is a qualification, not impact.",
    ])
    s += [Paragraph("Two problems that were fixed along the way", ST["h2"])]
    s += bullets([
        "PDF readers output <font name='Courier' size='8.6'>(cid:127)</font> where a "
        "bullet should be. These were appearing in evidence quoted back to the user.",
        "Word does not store list bullets in the text, so every DOCX appeared to have "
        "none - meaning every Word resume scored zero on formatting.",
    ])
    s += [Spacer(1, 16)]

    # ============================== FEATURE 2 ==============================
    s += [heading("Feature 2", "GitHub analysis")]
    s += [Paragraph("<b>What it does.</b> Reads a public GitHub profile and works out "
                    "which skills the person has actually used in code.", ST["body"])]
    s += [Paragraph("Evidence comes from three public signals per repository: the "
                    "<b>language</b> GitHub detected, the <b>topics</b> the author "
                    "tagged it with, and the <b>name and description</b>. Forked "
                    "repositories are ignored - forking is not writing.", ST["body"])]
    s += [callout(
        "The most important rule in this feature",
        "GitHub evidence is <b>never merged</b> into resume skills. They stay in "
        "separate columns: resume-only, GitHub-only, and both. A skill in both is a "
        "claim backed by public code, which is stronger than either alone. Every piece "
        "of evidence records <i>why</i> it matched - \"Topic 'react' on repository X\" "
        "- because a description mentioning a technology is not proof of skill, and "
        "the app says so rather than over-claiming.")]
    s += [Spacer(1, 8), callout(
        "Before any demonstration",
        "Without a token, GitHub allows 60 requests per hour and one analysis uses up "
        "to 7. A <b>free</b> GitHub token raises this to 5000. It is not a paid "
        "feature. Create one with <i>no permissions ticked</i> and put it in "
        "<font name='Courier' size='8.6'>backend/.env</font>.", "warn")]
    # No break here: the block above is short, and forcing one left a
    # near-empty page. Headings use KeepTogether so they never orphan.
    s += [Spacer(1, 20)]

    # ============================== FEATURE 3 ==============================
    s += [heading("Feature 3", "ATS scoring - the deterministic core")]
    s += [Paragraph(
        "<b>What it does.</b> Scores the resume out of 100 using nine rules, and "
        "explains every single point.", ST["body"])]
    s += [Paragraph(
        "An ATS is not intelligent. It opens a document, looks for fields and "
        "keywords, and ranks the result. Modelling that with plain rules gives three "
        "things an AI model cannot: it is <b>deterministic</b> (same resume, same "
        "number), <b>reproducible</b> (you can add up the nine components by hand), "
        "and <b>explainable</b> (every point belongs to a named component with a "
        "stated reason and the evidence that earned it).", ST["body"])]
    s += [Spacer(1, 4), table([
        ["Component", "Max", "What it owns"],
        ["Contact Information", "10", "Email 3, phone 2, name 2, LinkedIn 2, GitHub link 1"],
        ["Skills", "15", "Skills section 3, how many skills 8, category diversity 4"],
        ["Target Role Relevance", "18", "Overlap with the skills this role needs"],
        ["Job Description Keywords", "20", "Share of this posting's keywords present"],
        ["Experience &amp; Projects", "14", "Section 4, then entry count and detail 10"],
        ["Education", "8", "Section 3, entry 2, degree 2, CGPA or percentage 1"],
        ["Quantifiable Achievements", "5", "Section 1, lines with a real metric 4"],
        ["Formatting &amp; Readability", "5", "Summary section, bullets, verbs, length"],
        ["GitHub Profile Evidence", "5", "Profile, original repos, descriptions, skills"],
        ["TOTAL", "100", "The sum of the nine above - nothing else is added"],
    ], [42 * mm, 14 * mm, CONTENT_WIDTH - 56 * mm], align_right=[1])]

    s += [Spacer(1, 10), callout(
        "One fact, one component",
        "An earlier version had a separate \"Resume Sections\" component that gave "
        "points for <i>having</i> an Education section, a Skills section and so on - "
        "and then the Education, Skills and Experience components gave points for "
        "those same sections again. One fact moved the total twice, which made the "
        "score impossible to reason about.<br/><br/>"
        "Section presence now lives inside the component that owns that content. The "
        "test suite enforces it: removing any one section from a resume must shift "
        "<b>exactly one</b> component, and it must be the one that owns it.")]

    s += [Spacer(1, 10), Paragraph("Why these particular weights", ST["h2"])]
    s += bullets([
        "<b>Contact and Formatting</b> model what an ATS <i>parser</i> needs. If the "
        "software cannot find your email or read your headings, nothing else matters.",
        "<b>Job Description Keywords carries the largest weight (20)</b> because "
        "matching the specific posting is closest to how real ATS ranking works. Role "
        "Relevance (18) generalises that to the role.",
        "<b>GitHub is only 5 points on purpose.</b> A real ATS never sees a GitHub "
        "profile. Weighting it heavily would make the score less faithful to the thing "
        "it models.",
    ])
    s += [Spacer(1, 16)]

    # ============================== FEATURE 4 ==============================
    s += [heading("Feature 4", "Experience levels - fair scoring for freshers")]
    s += [Paragraph(
        "<b>The problem.</b> A final-year student will never have every skill in a job "
        "description. Scoring them against a senior candidate's standard makes the "
        "number meaningless - a fresher matching 20 of 55 requirements is doing "
        "<i>well</i>, not badly.", ST["body"])]
    s += [Paragraph(
        "<b>The wrong fix</b> would be to add bonus points to freshers. That is "
        "arbitrary, and an examiner would ask \"why that many points?\" <b>What this "
        "project does instead</b> is change the <i>expectation</i> rather than the "
        "arithmetic:", ST["body"])]
    s += [Spacer(1, 4), code(["scaled_coverage = min(1.0, actual_coverage / expected_coverage)"])]
    s += [Spacer(1, 10), table([
        ["Experience level", "Coverage for full marks", "Skills for full breadth",
         "Quantified achievements", "Experience / Projects split"],
        ["Fresher (0-1 years)", "50%", "10", "2", "3 / 7"],
        ["2-4 years", "70%", "15", "3", "5 / 5"],
        ["5+ years", "85%", "20", "4", "5 / 5"],
    ], [32 * mm, 26 * mm, 26 * mm, 34 * mm, CONTENT_WIDTH - 118 * mm],
        align_right=[1, 2, 3])]
    s += [Spacer(1, 10), callout(
        "A worked example",
        "A candidate covers 36% of a role's requirements.<br/><br/>"
        "<b>As a fresher:</b> 36 / 50 = <b>72%</b> of the available points.<br/>"
        "<b>As a senior candidate:</b> 36 / 85 = <b>42%</b> of the available points."
        "<br/><br/>Same resume, same arithmetic, different expectation.")]
    s += [Spacer(1, 10), Paragraph(
        "Structural components never change with career stage - contact details, "
        "sections, education, formatting. A missing email is missing at any level. "
        "And in job matching, <b>Evidence Corroboration is deliberately not scaled</b>: "
        "whether your claims are backed by public code does not get easier with "
        "experience, so scaling it would be dishonest leniency.", ST["body"])]
    # No break here: the block above is short, and forcing one left a
    # near-empty page. Headings use KeepTogether so they never orphan.
    s += [Spacer(1, 20)]

    # ============================== FEATURE 5 ==============================
    s += [heading("Feature 5", "The RAG pipeline - Objective 2")]
    s += [Paragraph(
        "<b>What RAG means.</b> Retrieval-Augmented Generation: instead of relying on "
        "what a system was built to know, you <i>retrieve</i> the relevant documents "
        "first and work from those. Here it means the job requirements come from real "
        "job descriptions rather than a hard-coded list.", ST["body"])]
    s += [Spacer(1, 4), flow_down([
        ("12 job-description files", "JSON, across 6 roles"),
        ("Chunking", "261 small pieces, one idea each"),
        ("Embedding", "each piece becomes 384 numbers"),
        ("FAISS vector index", "stored on disk, reused"),
        ("Search by meaning", "query compared against every chunk"),
        ("Top matching passages", "with similarity scores"),
    ], box_h=26, gap=11)]

    s += [Spacer(1, 12), Paragraph("Chunking: why not use whole documents?", ST["h2"])]
    s += [Paragraph(
        "Each bullet becomes its own chunk, because a bullet is already one idea. "
        "Longer prose is split into overlapping 70-word windows so a sentence crossing "
        "a boundary is still captured. If you turned a 600-word document into one set "
        "of numbers, those numbers would represent the <i>average</i> of everything in "
        "it - a search for \"required Python skills\" would match the whole document "
        "with no indication of which part was relevant.", ST["body"])]

    s += [Paragraph("Embeddings: what are they?", ST["h2"])]
    s += [Paragraph(
        "An embedding model turns text into a fixed list of numbers - 384 here - "
        "trained so that text with <i>similar meaning</i> gets similar numbers. That "
        "is why searching \"vector database embeddings\" finds \"Experience with "
        "vector databases such as FAISS, Chroma, Pinecone or Qdrant\" despite "
        "completely different wording. The model is "
        "<font name='Courier' size='8.6'>all-MiniLM-L6-v2</font>: free, about 90 MB, "
        "and it runs on your own laptop.", ST["body"])]

    s += [Paragraph("The vector store: how the search works", ST["h2"])]
    s += [Paragraph(
        "The 261 chunk vectors live in <b>FAISS</b>, a local search library, in an "
        "index called <font name='Courier' size='8.6'>IndexFlatIP</font>. <b>Flat</b> "
        "means every stored vector is compared against the query - exact, no "
        "approximation, instant at this size. <b>IP</b> means inner product; because "
        "every vector is scaled to the same length first, the inner product <i>is</i> "
        "the cosine similarity, a score from 0 to 1 where higher means closer in "
        "meaning.", ST["body"])]
    s += [Paragraph(
        "So the whole of \"vector similarity search\" reduces to one sentence: scale "
        "everything to the same length, multiply the query by each stored vector, and "
        "keep the highest scores.", ST["body"])]

    s += [Spacer(1, 6), callout(
        "A decision backed by measurement",
        "An earlier version prefixed every chunk with \"<i>Job title at Company | "
        "section:</i>\". Measured on the search \"vector database embeddings\", that "
        "prefix dropped the correct passage from <b>0.58 to 0.30</b> similarity and "
        "let an unrelated SQL passage outrank it - on a short chunk, the prefix "
        "dominates the meaning. It was removed, and the role is filtered using stored "
        "metadata instead.")]
    s += [Spacer(1, 8), Paragraph(
        "<b>If there is no internet,</b> the system switches to a simpler method "
        "(TF-IDF with Truncated SVD) built into scikit-learn that needs no download. "
        "Less good at paraphrases, but nothing breaks.", ST["body"])]
    s += [PageBreak()]

    # ============================== FEATURE 6 ==============================
    s += [heading("Feature 6", "Job matching - putting it together")]
    s += [Paragraph("<b>What it does.</b> Compares what the candidate can evidence "
                    "against what the job actually asks for.", ST["body"])]
    s += [callout(
        "The rule this feature exists to enforce",
        "The system does <b>not</b> hand a resume and a job description to an AI model "
        "and ask \"is this a good match?\" Instead: requirements are extracted from the "
        "retrieved passages, the candidate's evidence is collected from the resume and "
        "GitHub separately, and the two are compared using a published formula.")]
    s += [Spacer(1, 10), Paragraph("How requirements are decided", ST["h2"])]
    s += bullets([
        "A skill named in a <b>\"required skills\"</b> passage becomes a <b>core</b> "
        "requirement.",
        "Skills from <b>preferred skills, responsibilities or qualifications</b> "
        "become <b>preferred</b>.",
        "A skill is <b>not</b> promoted to core just because the posting mentions it. "
        "Something under \"nice to have\" stays a nice-to-have.",
        "For a job description you <b>paste in</b>, headings are detected as the text "
        "is processed - bullets under \"Required skills:\" become core.",
    ])
    s += [Spacer(1, 4), table([
        ["Component", "Max", "What it measures"],
        ["Core skill coverage", "55", "Share of must-have requirements evidenced"],
        ["Preferred skill coverage", "20", "Share of nice-to-haves evidenced"],
        ["Retrieved JD coverage", "15", "Coverage against what the search returned"],
        ["Evidence corroboration", "10", "Skills in both the resume and GitHub"],
        ["TOTAL", "100", "The sum of the four above"],
    ], [42 * mm, 14 * mm, CONTENT_WIDTH - 56 * mm], align_right=[1])]
    s += [Spacer(1, 8), Paragraph("Every row can be audited:", ST["body"])]
    s += [code([
        'skill                     : "React"',
        'required                  : true  (core)',
        'sources                   : ["resume"]',
        'why_required              : "Named in 2 retrieved job-description chunks"',
        'job_description_evidence  : "Deep React experience including hooks"',
        'resume_evidence           : "Listed in the resume\'s skills section"',
        'retrieval_similarity      : 0.536',
    ])]
    s += [PageBreak()]

    # ======================= OBJECTIVE 3 INTRO =======================
    s += [heading("Part 3", "Objective 3 - turning the analysis into action")]
    s += [Paragraph(
        "Objectives 1 and 2 tell a student <i>where they stand</i>. That is a "
        "diagnosis, not a plan. Objective 3 adds three features that answer the "
        "obvious follow-up questions, and none of them needed new machinery - they all "
        "consume output the first two objectives already produce.", ST["body"])]
    s += [Spacer(1, 4), table([
        ["Question a student asks", "Feature", "What it reuses"],
        ["Am I even aiming at the right role?", "Role recommendations",
         "The matcher, run six times instead of once"],
        ["What should I learn, and in what order?", "Learning roadmap",
         "The missing-skills list, plus a prerequisite graph"],
        ["What will they ask me?", "Interview preparation",
         "The matched and missing skills, plus a question bank"],
    ], [48 * mm, 36 * mm, CONTENT_WIDTH - 84 * mm])]
    s += [Spacer(1, 16)]

    # ============================== FEATURE 7 ==============================
    s += [heading("Feature 7", "Role recommendations")]
    s += [Paragraph(
        "<b>What it does.</b> A student picks one target role, but their resume may "
        "fit another better. This scores them against all six roles and ranks them.",
        ST["body"])]
    s += [Paragraph(
        "No new machinery: it runs the same matcher six times, each against that "
        "role's own retrieved requirements. The whole sweep adds about 100 "
        "milliseconds.", ST["body"])]
    s += [Spacer(1, 4), code([
        "3 roles fit you better than Frontend Developer (4/6 core requirements),",
        "led by Full Stack Developer at 9/11.",
        "",
        " 1. Full Stack Developer   9/11 core (82%)   match 90/100",
        " 2. AI/ML Engineer        11/15 core (73%)   match 90/100",
        " 3. Software Engineer      9/13 core (69%)   match 87/100",
        " 4. Frontend Developer      4/6 core (67%)   match 73/100  <- your target",
        " 5. Backend Developer      7/11 core (64%)   match 88/100",
        " 6. Data Scientist          5/8 core (62%)   match 83/100",
    ])]
    s += [Spacer(1, 10), Paragraph("Two decisions worth knowing", ST["h2"])]
    s += [callout(
        "Ranked by raw core coverage, not by the match score",
        "Notice that row 5 has a <i>higher</i> match score than row 4 yet ranks lower. "
        "That is deliberate. The experience-level adjustment caps a component once the "
        "expected coverage is reached - correct for scoring one role, but it flattens "
        "a comparison across six. At fresher level a candidate covering 62% and one "
        "covering 67% both hit the 50% target, both components max out, and the "
        "ranking then turns on incidental preferred skills. Ranking on unadjusted core "
        "coverage keeps the ordering meaningful.")]
    s += [Spacer(1, 8), callout(
        "A pasted job description is deliberately ignored here",
        "A posting you pasted describes one specific job. Feeding it into the other "
        "five roles would contaminate their requirements and make the comparison "
        "meaningless, so the sweep is role-generic. A test asserts a pasted posting "
        "does not change the ranking at all.")]
    s += [Spacer(1, 16)]

    # ============================== FEATURE 8 ==============================
    s += [heading("Feature 8", "The learning roadmap")]
    s += [Paragraph(
        "<b>What it does.</b> Turns the gap list into an ordered plan. The matcher "
        "produces a <i>set</i> of missing skills, and a set is not actionable - \"learn "
        "PyTorch\" is useless advice to someone who does not yet know Python.",
        ST["body"])]
    s += [Paragraph("Three signals decide the order, all derived rather than invented:",
                    ST["body"])]
    s += bullets([
        "<b>Prerequisites</b> - an 87-edge graph saying what must come first, "
        "validated for cycles and unknown skills by the test suite.",
        "<b>Demand</b> - the RAG similarity scores the matcher already computed, so "
        "the loudest requirements lead within a phase.",
        "<b>Requirement level</b> - core before preferred.",
    ])
    s += [Spacer(1, 4), code([
        "21 skills to work through for AI/ML Engineer, across 3 phases.",
        "",
        "Assumed knowledge: the job descriptions never listed Linux, but the",
        "skills you are missing depend on it. It leads the plan.",
        "",
        "Phase 1 - Foundations",
        "  1. Python           core   ready now    unlocks Machine Learning, NumPy",
        "  3. Linux            assumed knowledge   unlocks Monitoring",
        "  5. Machine Learning core   after Python, Statistics",
        "  7. Deep Learning    core   after Machine Learning",
        "  9. LLMs             core   after Deep Learning, NLP",
    ])]
    s += [Spacer(1, 10), Paragraph("Three design choices", ST["h2"])]
    s += bullets([
        "<b>Hidden prerequisites are surfaced.</b> Someone missing PyTorch may also "
        "lack Deep Learning, which no posting listed because it is assumed. Those lead "
        "the plan, flagged as assumed knowledge.",
        "<b>The plan is closed under prerequisites.</b> Each phase shows a limited "
        "number of steps, but the cap relaxes wherever cutting one would leave a later "
        "step blocked by something absent. Without this, a weak resume produced a plan "
        "whose Phase 2 said \"blocked by Machine Learning\" while Machine Learning "
        "appeared nowhere.",
        "<b>No time estimates, deliberately.</b> \"Learn Docker in 3 weeks\" would be "
        "invented precision. Each skill carries a <i>depth</i> computed from the graph "
        "instead, which is a real derived property. A test asserts no step contains a "
        "duration field.",
    ])
    s += [PageBreak()]

    # ============================== FEATURE 9 ==============================
    s += [heading("Feature 9", "Interview preparation")]
    s += [Paragraph(
        "<b>What it does.</b> Shows the questions this candidate is most likely to "
        "face, from a bank of 65 questions each tagged with the skills it tests, a "
        "kind, and a difficulty matching the experience levels.", ST["body"])]
    s += [Spacer(1, 4), table([
        ["Group", "What it contains", "Why it matters"],
        ["Be ready to prove these", "Skills you claim that this role requires",
         "You will be asked to demonstrate them, not just list them"],
        ["Be ready to handle these gaps", "Requirements you cannot evidence yet",
         "You will probably still be asked. An honest prepared answer beats an "
         "improvised one"],
        ["About you and your projects", "Project and behavioural questions",
         "Asked in almost every interview, regardless of role"],
    ], [38 * mm, 44 * mm, CONTENT_WIDTH - 82 * mm])]
    s += [Spacer(1, 10), code([
        "Q: Your model scores 99% on training data and 62% on test data.",
        "   What is happening and what do you do?",
        "",
        "   [Machine Learning]  [technical]",
        "",
        "   What they are checking: whether you recognise overfitting and can",
        "   name concrete remedies rather than just the word.",
    ])]
    s += [Spacer(1, 12), callout(
        "Why this does NOT use RAG",
        "Objective 2 uses semantic retrieval because the job-description corpus is "
        "large and written by other people - embeddings find relevance nobody "
        "labelled. The question bank is the opposite: small, and <b>we wrote the "
        "tags</b>. Looking up a tag we set ourselves is exact; embedding the questions "
        "and retrieving them by similarity would only be approximate.<br/><br/>"
        "Using the weaker tool because it is the more impressive one would be the "
        "wrong call. RAG still does the <i>ordering</i> - questions rank by how "
        "strongly the retrieved job descriptions demanded the skill they test.")]
    s += [Spacer(1, 8), callout(
        "No model answers, deliberately",
        "Each question states <b>what the interviewer is checking for</b>, not an "
        "answer. Writing 65 authoritative answers across 66 skills is a large surface "
        "area for stating something subtly wrong, and a wrong answer in revision "
        "material is worse than none. A test asserts no question ships an answer "
        "field.<br/><br/>"
        "A question above your level appears only when that skill has nothing easier, "
        "and is flagged as a <b>stretch</b> - otherwise a skill whose only question is "
        "\"mid\" would vanish for a fresher.", "warn")]
    s += [Spacer(1, 16)]

    # ============================== FEATURE 10 ==============================
    s += [heading("Feature 10", "The summary")]
    s += [Paragraph(
        "<b>What it does.</b> Condenses everything into three sections anyone can read "
        "in fifteen seconds: what the ATS score means, which requirements are and are "
        "not evidenced, and the two or three highest-impact fixes, ranked by points "
        "recoverable.", ST["body"])]
    s += [Paragraph("Why rules instead of an AI model", ST["h2"])]
    s += bullets([
        "<b>Deterministic</b> - the same analysis produces the same words every time.",
        "<b>Grounded</b> - it can only state facts that were computed. It cannot "
        "invent a skill or a number, because it has no mechanism to produce one.",
        "<b>Free and offline</b> - no API key, no account, no cost per use.",
    ])
    s += [Paragraph(
        "The honest trade-off: the phrasing is formulaic, and it will not notice a "
        "pattern no rule looks for. For a tool whose purpose is explaining <i>why</i> "
        "a score is what it is, that is the right trade.", ST["body"])]
    # No break here: the block above is short, and forcing one left a
    # near-empty page. Headings use KeepTogether so they never orphan.
    s += [Spacer(1, 20)]

    # ============================== PART 4 ==============================
    s += [heading("Part 4", "Technology, testing and honest limits")]
    s += [Paragraph("What it is built with", ST["h2"])]
    s += [table([
        ["Layer", "Technology", "Why"],
        ["Frontend", "React 19, Vite 7, Tailwind CSS 4",
         "Component dashboard with a fast development server"],
        ["Backend", "Python, FastAPI, Uvicorn",
         "Fast API with automatically generated documentation"],
        ["Resume reading", "pdfplumber, python-docx", "Text and table extraction"],
        ["GitHub", "GitHub REST API", "Public profile and repository data"],
        ["Embeddings", "sentence-transformers (all-MiniLM-L6-v2)",
         "Free, 384 dimensions, runs locally"],
        ["Vector search", "FAISS (IndexFlatIP)", "Exact cosine search, no server"],
        ["Offline backup", "scikit-learn TF-IDF + SVD", "Works with no download"],
        ["Everything else", "Plain Python rules", "No AI model, no API key"],
    ], [26 * mm, 50 * mm, CONTENT_WIDTH - 76 * mm])]

    s += [Spacer(1, 10), callout(
        "What AI is actually used?",
        "Exactly one model: <font name='Courier' size='8.6'>all-MiniLM-L6-v2</font>, a "
        "sentence-transformer that converts text into 384-dimensional embeddings. It "
        "is used <b>only</b> for semantic retrieval in the RAG pipeline. It is not "
        "generative - it cannot write a sentence. No large language model is used "
        "anywhere: the ATS score, the job match, the roadmap, the interview selection "
        "and the written summary are all produced by deterministic rules.")]

    s += [Spacer(1, 12), Paragraph("Testing", ST["h2"])]
    s += [Paragraph(
        "<b>213 automated checks</b> in "
        "<font name='Courier' size='8.6'>backend/tests/test_api.py</font>, run with "
        "the backend running:", ST["body"])]
    s += [code(["cd backend && python tests/test_api.py"])]
    s += [Spacer(1, 8)]
    s += bullets([
        "Resume parsing in both formats, and every failure mode",
        "A PDF and a DOCX of the same resume producing identical skills",
        "The ATS total always equalling the sum of its components",
        "No fact being double counted - removing a section shifts exactly one component",
        "Experience-level scaling behaving consistently across levels",
        "Retrieval returning genuinely relevant passages",
        "The roadmap never referring to a blocker absent from the plan",
        "No backend file importing an AI provider - the \"no model\" claim is checked "
        "structurally, not just stated",
    ])

    s += [Spacer(1, 12), Paragraph("Limitations - state these honestly", ST["h2"])]
    s += [table([
        ["Limitation", "Why it matters"],
        ["The 12 job descriptions are sample data",
         "Written for this project. Match scores are relative, not absolute."],
        ["The prerequisite graph and question bank are authored",
         "87 edges and 65 questions reflect our judgement. They validate "
         "structurally, but the opinions inside them are opinions."],
        ["Skill detection is list-based",
         "It finds the 112 skills it knows. A passing mention counts the same as deep "
         "use."],
        ["GitHub evidence is shallow",
         "It reads repository descriptions and languages, not the code itself."],
        ["It models an ATS; it is not one",
         "Real systems are proprietary and differ between vendors."],
        ["Scanned PDFs are rejected", "There is no OCR step."],
        ["The sign-in is not real authentication",
         "No user database, no password. Anyone opening the app can use it."],
        ["The 213 tests are correctness tests",
         "Not a retrieval-accuracy benchmark. Do not quote a precision figure."],
    ], [52 * mm, CONTENT_WIDTH - 52 * mm])]

    s += [Spacer(1, 14), callout(
        "The sentence to remember for a viva",
        "\"The ATS score is a deterministic rule-based calculation. The job match "
        "compares structured resume and GitHub evidence against requirements retrieved "
        "from real job descriptions by semantic search. The roadmap and interview prep "
        "are built on top of that same output. One embedding model powers the "
        "retrieval; no language model is used anywhere.\"", "good")]

    return s


def main():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="Career Engine - Workflow & Feature Guide",
        author="Career Engine",
        subject="Project workflow and feature explanation",
    )
    doc.build(story(), onFirstPage=decorate, onLaterPages=decorate)
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
