"""
report/build.py
===============

Two-pass build driver.

Pass 1 renders the PDF with empty index tables to learn which page every
heading, figure and table lands on.  Pass 2 re-renders with those page numbers
filled into the List of Figures, List of Tables and Table of Contents, and
writes the DOCX from the same block list.

Page numbering follows the original report: front matter in lower-case roman
numerals, body from Chapter 1 onward in arabic numerals starting at 1.
"""

import pathlib

import build_report as br
import content as C

OUT = pathlib.Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

PDF = OUT / "AI-Powered-Career-Engine-Report.pdf"
DOCX = OUT / "AI-Powered-Career-Engine-Report.docx"


def toc_key_for(entry: str):
    """Map a Table-of-Contents line to the _toc_key the renderer records."""
    fronts = {
        "Abstract": "ABSTRACT",
        "Acknowledgement": "ACKNOWLEDGEMENT",
        "List of Figures": "LIST OF FIGURES",
        "List of Tables": "LIST OF TABLES",
        "Table of Contents": "TABLE OF CONTENTS",
        "References": "REFERENCES",
    }
    if entry in fronts:
        return ("front", fronts[entry])
    if entry.startswith("Chapter "):
        return ("chapter", "CHAPTER " + entry.split()[1])
    return ("h2", entry)


def body(toc, figs, tabs):
    return (C.front_matter(toc, figs, tabs)
            + C.chapter_1() + C.chapter_2()
            + C.chapter_3() + C.chapter_3b()
            + C.chapter_4() + C.chapter_5()
            + C.references())


def label(page_of, key, front_pages):
    """Render a recorded physical page as the label printed on that page."""
    page = page_of.get(key)
    if page is None:
        return ""
    br.FRONT_PAGES = front_pages
    return br._page_label(page)


def front_page_count(blocks):
    """Physical pages occupied by front matter, i.e. everything before Ch 1."""
    for i, b in enumerate(blocks):
        if b[0] == "chapter":
            return i, None
    raise RuntimeError("no chapter block found")


def main():
    # ---- pass 1: blank indexes, just to measure ---------------------------
    blocks = body({}, {}, {})
    br.FRONT_PAGES = 0
    page_of = br.render_pdf(blocks, OUT / "_pass1.pdf")

    ch1 = page_of[("chapter", "CHAPTER 1")]
    front_pages = ch1 - 1

    toc = {e: label(page_of, toc_key_for(e), front_pages) for e in C.TOC_ENTRIES}

    figs, tabs = {}, {}
    for key, page in page_of.items():
        if key[0] == "figure":
            tag = key[1].split(":")[0].strip()
            figs[tag] = label(page_of, key, front_pages)
        elif key[0] == "table":
            tag = key[1].split(":")[0].strip()
            if tag:
                tabs[tag] = label(page_of, key, front_pages)

    # ---- pass 2: real page numbers ----------------------------------------
    blocks = body(toc, figs, tabs)
    br.FRONT_PAGES = front_pages
    page_of2 = br.render_pdf(blocks, PDF)

    # If pagination shifted (index tables grew), repeat once with new numbers.
    if page_of2.get(("chapter", "CHAPTER 1")) != ch1:
        ch1 = page_of2[("chapter", "CHAPTER 1")]
        front_pages = ch1 - 1

    toc = {e: label(page_of2, toc_key_for(e), front_pages) for e in C.TOC_ENTRIES}
    figs, tabs = {}, {}
    for key, page in page_of2.items():
        if key[0] == "figure":
            figs[key[1].split(":")[0].strip()] = label(page_of2, key, front_pages)
        elif key[0] == "table":
            tag = key[1].split(":")[0].strip()
            if tag:
                tabs[tag] = label(page_of2, key, front_pages)

    blocks = body(toc, figs, tabs)
    br.FRONT_PAGES = front_pages
    final = br.render_pdf(blocks, PDF)
    br.render_docx(blocks, DOCX)

    (OUT / "_pass1.pdf").unlink(missing_ok=True)

    from pypdf import PdfReader
    pages = len(PdfReader(str(PDF)).pages)
    print("front matter pages :", front_pages)
    print("total pages        :", pages)
    print("chapter starts     :",
          {k[1]: final[k] for k in final if k[0] == "chapter"})
    missing = [e for e in C.TOC_ENTRIES if not toc.get(e)]
    if missing:
        print("MISSING toc page numbers:", missing)
    missing_f = [k for k, _ in C.FIGURE_INDEX if not figs.get(k)]
    if missing_f:
        print("MISSING figure pages:", missing_f)
    missing_t = [k for k, _ in C.TABLE_INDEX if not tabs.get(k)]
    if missing_t:
        print("MISSING table pages:", missing_t)
    print("PDF  ->", PDF)
    print("DOCX ->", DOCX)


if __name__ == "__main__":
    main()
