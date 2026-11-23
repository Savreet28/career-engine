"""
report/build_report.py
======================

Renders the major-project report to BOTH PDF and DOCX from one content model,
so the two can never drift apart.

Why two renderers rather than a DOCX-to-PDF conversion: neither Microsoft Word
nor LibreOffice is installed on this machine, so there is no converter to call.
Defining the document once as a list of blocks and rendering it twice keeps the
content identical and the formatting under our control.

Formatting is measured from the original finalg3.pdf (Word 2021) so the output
matches it exactly:

    page            A4, 595.6 x 842.3 pt
    left margin     98.8 pt   (1.372 in)
    right margin    15.1 pt   (0.21 in)
    body            Times New Roman 12 pt, JUSTIFIED
    line spacing    27.6 pt   (double spacing on 12 pt)
    section heading Times New Roman 14 pt bold, left
    chapter heading Times New Roman 16 pt bold, centred
    page number     centred in the footer
"""

from __future__ import annotations

import pathlib
from typing import List, Tuple

from PIL import Image

HERE = pathlib.Path(__file__).parent
IMAGES = HERE / "images"

# --- measured from the original document -----------------------------------
PAGE_W, PAGE_H = 595.6, 842.3
MARGIN_L = 98.8
MARGIN_R = 15.1
MARGIN_T = 65.0
MARGIN_B = 72.0
TEXT_W = PAGE_W - MARGIN_L - MARGIN_R          # 481.7 pt

BODY_FONT = "Times New Roman"
BODY_SIZE = 12
LEADING = 27.6                                  # double spacing on 12 pt
PARA_AFTER = 14
H2_SIZE = 14
H1_SIZE = 16


# ---------------------------------------------------------------------------
# Block model. Every block is a tuple whose first item names its kind.
# ---------------------------------------------------------------------------
def chapter(number: str, title: str): return ("chapter", number, title)
def front(title: str):                return ("front", title)
def h2(text: str):                    return ("h2", text)
def h3(text: str):                    return ("h3", text)
def p(text: str):                     return ("p", text)
def bullet(text: str):                return ("bullet", text)
def num(text: str):                   return ("num", text)
def bold(text: str):                  return ("bold", text)
def figure(img: str, caption: str, width_in: float = 5.6):
    return ("figure", img, caption, width_in)
def table(caption: str, rows: List[List[str]], widths: List[float]):
    return ("table", caption, rows, widths)
def pagebreak():                      return ("pagebreak",)
def spacer(points: float = 12):       return ("spacer", points)


def image_size(name: str, width_in: float) -> Tuple[float, float]:
    """Scale an image to the requested width, preserving aspect ratio."""
    with Image.open(IMAGES / name) as im:
        w, h = im.size
    width_pt = width_in * 72
    return width_pt, width_pt * h / w


# ===========================================================================
# PDF renderer
# ===========================================================================
def render_pdf(blocks, out_path: pathlib.Path, toc_pages=None) -> dict:
    """
    Render to PDF. Returns a map of heading/figure key -> page number, so a
    second pass can fill in the contents pages and list of figures.
    """
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate, Frame, Image as RLImage, KeepTogether, PageBreak,
        PageTemplate, Paragraph, Spacer, Table as RLTable, TableStyle,
    )
    from reportlab.lib import colors

    _register_times(pdfmetrics, TTFont)

    styles = {
        "chapter": ParagraphStyle("chapter", fontName="Times-Bold", fontSize=H1_SIZE,
                                  leading=LEADING, alignment=TA_CENTER,
                                  spaceBefore=0, spaceAfter=PARA_AFTER),
        "front": ParagraphStyle("front", fontName="Times-Bold", fontSize=H1_SIZE,
                                leading=LEADING, alignment=TA_CENTER,
                                spaceBefore=0, spaceAfter=PARA_AFTER),
        "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=H2_SIZE,
                             leading=LEADING, alignment=TA_LEFT,
                             spaceBefore=6, spaceAfter=PARA_AFTER),
        "h3": ParagraphStyle("h3", fontName="Times-Bold", fontSize=BODY_SIZE,
                             leading=LEADING, alignment=TA_LEFT,
                             spaceBefore=4, spaceAfter=PARA_AFTER),
        "bold": ParagraphStyle("boldp", fontName="Times-Bold", fontSize=BODY_SIZE,
                               leading=LEADING, alignment=TA_LEFT,
                               spaceAfter=PARA_AFTER),
        "p": ParagraphStyle("p", fontName="Times-Roman", fontSize=BODY_SIZE,
                            leading=LEADING, alignment=TA_JUSTIFY,
                            spaceAfter=PARA_AFTER),
        "bullet": ParagraphStyle("bullet", fontName="Times-Roman", fontSize=BODY_SIZE,
                                 leading=LEADING, alignment=TA_LEFT,
                                 leftIndent=18, bulletIndent=4,
                                 spaceAfter=PARA_AFTER),
        "cap": ParagraphStyle("cap", fontName="Times-Roman", fontSize=BODY_SIZE,
                              leading=LEADING, alignment=TA_CENTER, spaceAfter=6),
        "cell": ParagraphStyle("cell", fontName="Times-Roman", fontSize=11,
                               leading=15, alignment=TA_LEFT),
        "cellh": ParagraphStyle("cellh", fontName="Times-Bold", fontSize=11,
                                leading=15, alignment=TA_LEFT),
    }

    page_of: dict = {}
    state = {"page": 0}

    class Doc(BaseDocTemplate):
        def afterFlowable(self, flowable):
            key = getattr(flowable, "_toc_key", None)
            if key:
                page_of[key] = self.page

    def footer(canvas, doc):
        state["page"] = doc.page
        canvas.saveState()
        canvas.setFont("Times-Roman", BODY_SIZE)
        label = _page_label(doc.page)
        canvas.drawCentredString(MARGIN_L + TEXT_W / 2, MARGIN_B / 2 + 6, label)
        canvas.restoreState()

    doc = Doc(str(out_path), pagesize=(PAGE_W, PAGE_H),
              leftMargin=MARGIN_L, rightMargin=MARGIN_R,
              topMargin=MARGIN_T, bottomMargin=MARGIN_B,
              title="AI Powered Career Engine - Major Project Report",
              author="Manpreet Kaur, Mansi, Savreet Kaur")
    frame = Frame(MARGIN_L, MARGIN_B, TEXT_W, PAGE_H - MARGIN_T - MARGIN_B, id="body")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])

    flow = []
    for b in blocks:
        kind = b[0]
        if kind == "pagebreak":
            flow.append(PageBreak())
        elif kind == "spacer":
            flow.append(Spacer(1, b[1]))
        elif kind == "chapter":
            a = Paragraph(b[1], styles["chapter"])
            a._toc_key = ("chapter", b[1])
            flow += [a, Paragraph(b[2], styles["chapter"])]
        elif kind == "front":
            a = Paragraph(b[1], styles["front"])
            a._toc_key = ("front", b[1])
            flow.append(a)
        elif kind in ("h2", "h3"):
            a = Paragraph(_esc(b[1]), styles[kind])
            a._toc_key = (kind, b[1])
            flow.append(a)
        elif kind == "bold":
            flow.append(Paragraph(_esc(b[1]), styles["bold"]))
        elif kind == "p":
            flow.append(Paragraph(_esc(b[1]), styles["p"]))
        elif kind == "bullet":
            flow.append(Paragraph(_esc(b[1]), styles["bullet"], bulletText="•"))
        elif kind == "num":
            flow.append(Paragraph(_esc(b[1]), styles["bullet"]))
        elif kind == "figure":
            _, img, caption, win = b
            w, h = image_size(img, win)
            pic = RLImage(str(IMAGES / img), width=w, height=h)
            cap = Paragraph(_esc(caption), styles["cap"])
            cap._toc_key = ("figure", caption)
            flow.append(KeepTogether([pic, Spacer(1, 4), cap]))
        elif kind == "table":
            _, caption, rows, widths = b
            data = [[Paragraph(_esc(str(c)), styles["cellh"] if r == 0 else styles["cell"])
                     for c in row] for r, row in enumerate(rows)]
            t = RLTable(data, colWidths=[w * TEXT_W for w in widths], repeatRows=1)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]))
            cap = Paragraph(_esc(caption), styles["cap"])
            cap._toc_key = ("table", caption)
            flow += [cap, Spacer(1, 2), t, Spacer(1, PARA_AFTER)]
        elif kind == "titlepage":
            flow += _pdf_title_page(styles, RLImage, Paragraph, Spacer)
    doc.build(flow)
    return page_of


def _register_times(pdfmetrics, TTFont):
    """Use the real Times New Roman if macOS has it; fall back to base-14."""
    candidates = [
        ("/System/Library/Fonts/Supplemental/Times New Roman.ttf",
         "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"),
    ]
    for regular, boldf in candidates:
        if pathlib.Path(regular).exists() and pathlib.Path(boldf).exists():
            try:
                pdfmetrics.registerFont(TTFont("Times-Roman", regular))
                pdfmetrics.registerFont(TTFont("Times-Bold", boldf))
                return
            except Exception:
                pass
    # reportlab's built-in Times is metrically the same family.


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<b>", "\x01").replace("</b>", "\x02")
                .replace("<", "&lt;").replace(">", "&gt;")
                .replace("\x01", "<b>").replace("\x02", "</b>"))


ROMAN = ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
FRONT_PAGES = 0          # set by build(); pages before Chapter 1


def _page_label(page: int) -> str:
    """Front matter is numbered i, ii, iii...; the body restarts at 1."""
    if page == 1:
        return ""                       # title page carries no number
    if page <= FRONT_PAGES:
        return ROMAN[page - 1]
    return str(page - FRONT_PAGES)


def _pdf_title_page(styles, RLImage, Paragraph, Spacer):
    """The cover, rebuilt to match the original layout."""
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    big = ParagraphStyle("tp_big", fontName="Times-Bold", fontSize=24, leading=30,
                         alignment=TA_CENTER, spaceAfter=18)
    mid = ParagraphStyle("tp_mid", fontName="Times-Bold", fontSize=14, leading=22,
                         alignment=TA_CENTER, spaceAfter=4)
    small = ParagraphStyle("tp_small", fontName="Times-Roman", fontSize=12, leading=18,
                           alignment=TA_CENTER, spaceAfter=3)
    left = ParagraphStyle("tp_l", fontName="Times-Roman", fontSize=12, leading=18,
                          alignment=0)
    right = ParagraphStyle("tp_r", fontName="Times-Roman", fontSize=12, leading=18,
                           alignment=2)
    from reportlab.platypus import Table as RLTable, TableStyle
    w, h = image_size("logo.png", 1.6)
    names = RLTable([[
        Paragraph("<b>Submitted By:</b><br/>Manpreet Kaur (2302607)<br/>"
                  "Mansi (2302610)<br/>Savreet Kaur (2302668)", left),
        Paragraph("<b>Submitted To:</b><br/>Dr. Manpreet Kaur", right),
    ]], colWidths=[TEXT_W * 0.55, TEXT_W * 0.45])
    names.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return [
        Spacer(1, 10),
        Paragraph("AI Powered Career Engine", big),
        Paragraph("MAJOR PROJECT REPORT", mid),
        Spacer(1, 8),
        Paragraph("SUBMITTED IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR", small),
        Paragraph("THE AWARD OF THE DEGREE OF", small),
        Paragraph("<b>BACHELOR OF TECHNOLOGY</b>", mid),
        Paragraph("(Computer Science and Engineering)", small),
        Spacer(1, 16),
        RLImage(str(IMAGES / "logo.png"), width=w, height=h),
        Spacer(1, 16),
        names,
        Spacer(1, 20),
        Paragraph("Department of Computer Science and Engineering", mid),
        Paragraph("GURU NANAK DEV ENGINEERING COLLEGE,", mid),
        Paragraph("LUDHIANA, 141006", mid),
    ]


# ===========================================================================
# DOCX renderer
# ===========================================================================
def render_docx(blocks, out_path: pathlib.Path) -> None:
    import docx
    from docx.enum.section import WD_SECTION
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, Inches, Emu

    document = docx.Document()
    section = document.sections[0]
    section.page_width = Emu(int(PAGE_W / 72 * 914400))
    section.page_height = Emu(int(PAGE_H / 72 * 914400))
    section.left_margin = Emu(int(MARGIN_L / 72 * 914400))
    section.right_margin = Emu(int(MARGIN_R / 72 * 914400))
    section.top_margin = Emu(int(MARGIN_T / 72 * 914400))
    section.bottom_margin = Emu(int(MARGIN_B / 72 * 914400))

    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    def para(text="", size=BODY_SIZE, bold_=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             after=PARA_AFTER, indent=0, style=None):
        par = document.add_paragraph(style=style)
        par.alignment = align
        pf = par.paragraph_format
        pf.line_spacing = Pt(LEADING)
        pf.space_after = Pt(after)
        pf.space_before = Pt(0)
        if indent:
            pf.left_indent = Pt(indent)
        _add_runs(par, text, size, bold_)
        return par

    def _add_runs(par, text, size, bold_):
        """Honour the <b>...</b> markers used in the content."""
        for piece, is_bold in _split_bold(text):
            run = par.add_run(piece)
            run.font.name = BODY_FONT
            run.font.size = Pt(size)
            run.bold = bold_ or is_bold
            run._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    # centred page number in the footer
    footer_par = section.footer.paragraphs[0]
    footer_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_par.add_run()
    for instr in ("begin", "PAGE", "end"):
        el = OxmlElement("w:fldChar") if instr in ("begin", "end") else OxmlElement("w:instrText")
        if instr in ("begin", "end"):
            el.set(qn("w:fldCharType"), instr)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        run._r.append(el)
    run.font.name = BODY_FONT
    run.font.size = Pt(BODY_SIZE)

    for b in blocks:
        kind = b[0]
        if kind == "pagebreak":
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif kind == "spacer":
            para("", after=b[1])
        elif kind == "titlepage":
            _docx_title_page(document, para, WD_ALIGN_PARAGRAPH, Pt, Inches)
        elif kind == "chapter":
            para(b[1], size=H1_SIZE, bold_=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            para(b[2], size=H1_SIZE, bold_=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        elif kind == "front":
            para(b[1], size=H1_SIZE, bold_=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        elif kind == "h2":
            para(b[1], size=H2_SIZE, bold_=True, align=WD_ALIGN_PARAGRAPH.LEFT)
        elif kind == "h3":
            para(b[1], size=BODY_SIZE, bold_=True, align=WD_ALIGN_PARAGRAPH.LEFT)
        elif kind == "bold":
            para(b[1], bold_=True, align=WD_ALIGN_PARAGRAPH.LEFT)
        elif kind == "p":
            para(b[1])
        elif kind == "bullet":
            para("•  " + b[1], align=WD_ALIGN_PARAGRAPH.LEFT, indent=18)
        elif kind == "num":
            para(b[1], align=WD_ALIGN_PARAGRAPH.LEFT, indent=18)
        elif kind == "figure":
            _, img, caption, win = b
            pic_par = document.add_paragraph()
            pic_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pic_par.paragraph_format.space_after = Pt(4)
            pic_par.paragraph_format.line_spacing = 1.0
            pic_par.add_run().add_picture(str(IMAGES / img), width=Inches(win))
            para(caption, align=WD_ALIGN_PARAGRAPH.CENTER, after=PARA_AFTER)
        elif kind == "table":
            _, caption, rows, widths = b
            para(caption, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
            t = document.add_table(rows=len(rows), cols=len(rows[0]))
            t.style = "Table Grid"
            for r_i, row in enumerate(rows):
                for c_i, cell in enumerate(row):
                    tc = t.cell(r_i, c_i)
                    tc.width = Emu(int(widths[c_i] * TEXT_W / 72 * 914400))
                    tp = tc.paragraphs[0]
                    tp.paragraph_format.line_spacing = 1.0
                    tp.paragraph_format.space_after = Pt(2)
                    for piece, is_bold in _split_bold(str(cell)):
                        run = tp.add_run(piece)
                        run.font.name = BODY_FONT
                        run.font.size = Pt(11)
                        run.bold = (r_i == 0) or is_bold
            para("", after=PARA_AFTER)

    document.save(str(out_path))


def _docx_title_page(document, para, ALIGN, Pt, Inches):
    para("AI Powered Career Engine", size=24, bold_=True, align=ALIGN.CENTER, after=18)
    para("MAJOR PROJECT REPORT", size=14, bold_=True, align=ALIGN.CENTER, after=10)
    para("SUBMITTED IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR",
         align=ALIGN.CENTER, after=2)
    para("THE AWARD OF THE DEGREE OF", align=ALIGN.CENTER, after=6)
    para("BACHELOR OF TECHNOLOGY", size=14, bold_=True, align=ALIGN.CENTER, after=2)
    para("(Computer Science and Engineering)", align=ALIGN.CENTER, after=14)
    pic = document.add_paragraph()
    pic.alignment = ALIGN.CENTER
    pic.add_run().add_picture(str(IMAGES / "logo.png"), width=Inches(1.6))
    para("", after=12)
    t = document.add_table(rows=1, cols=2)
    left, right = t.cell(0, 0), t.cell(0, 1)
    for cell, lines, al in (
        (left, ["Submitted By:", "Manpreet Kaur (2302607)", "Mansi (2302610)",
                "Savreet Kaur (2302668)"], ALIGN.LEFT),
        (right, ["Submitted To:", "Dr. Manpreet Kaur"], ALIGN.RIGHT)):
        cp = cell.paragraphs[0]
        cp.alignment = al
        for i, line in enumerate(lines):
            if i:
                cp.add_run().add_break()
            run = cp.add_run(line)
            run.font.name = BODY_FONT
            run.font.size = Pt(BODY_SIZE)
            run.bold = (i == 0)
    para("", after=16)
    para("Department of Computer Science and Engineering", size=14, bold_=True,
         align=ALIGN.CENTER, after=2)
    para("GURU NANAK DEV ENGINEERING COLLEGE,", size=14, bold_=True,
         align=ALIGN.CENTER, after=2)
    para("LUDHIANA, 141006", size=14, bold_=True, align=ALIGN.CENTER, after=0)


def _split_bold(text: str):
    """Split '<b>bold</b> plain' into [(piece, is_bold), ...]."""
    out, rest = [], text
    while "<b>" in rest and "</b>" in rest:
        before, _, after = rest.partition("<b>")
        inner, _, rest = after.partition("</b>")
        if before:
            out.append((before, False))
        out.append((inner, True))
    if rest:
        out.append((rest, False))
    return out or [(text, False)]
