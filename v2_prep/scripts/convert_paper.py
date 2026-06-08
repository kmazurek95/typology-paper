"""
Convert the markdown paper draft to Word (.docx) and PDF.

Reads paper/typology_paper_draft.md (the updated V2 draft),
produces paper/typology_paper_draft.docx and paper/typology_paper_draft.pdf.

Embeds the typology scatter plot figure where the placeholder appears.
"""

import re
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parent.parent
PAPER_DIR = ROOT / "paper"
FIGURES_DIR = ROOT / "figures"
MD_PATH = PAPER_DIR / "typology_paper_draft_v2.md"
DOCX_PATH = PAPER_DIR / "typology_paper_draft.docx"
PDF_PATH = PAPER_DIR / "typology_paper_draft.pdf"


def setup_styles(doc):
    """Configure document styles for academic paper."""
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Times New Roman"
    font.size = Pt(12)
    pf = style.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.5

    for level, size in [(1, 16), (2, 14), (3, 12)]:
        hstyle = doc.styles[f"Heading {level}"]
        hstyle.font.name = "Times New Roman"
        hstyle.font.size = Pt(size)
        hstyle.font.bold = True
        hstyle.font.color.rgb = RGBColor(0, 0, 0)
        hstyle.paragraph_format.space_before = Pt(18 if level == 1 else 12)
        hstyle.paragraph_format.space_after = Pt(6)


def add_paragraph(doc, text, style="Normal", bold=False, italic=False,
                  alignment=None, space_after=None):
    """Add a paragraph with optional formatting."""
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    if alignment is not None:
        p.alignment = alignment
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def process_inline(paragraph, text):
    """Process inline markdown (bold, italic) within a paragraph."""
    # Split on bold (**...**) and italic (*...*)
    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            paragraph.add_run(part)


def convert_md_to_docx(md_text, doc):
    """Convert markdown text to Word document."""
    lines = md_text.split("\n")
    i = 0
    in_abstract = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip horizontal rules
        if stripped == "---":
            i += 1
            continue

        # Empty line
        if not stripped:
            i += 1
            continue

        # Headings
        if stripped.startswith("# ") and not stripped.startswith("## "):
            # Title
            title_text = stripped[2:]
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(title_text)
            run.bold = True
            run.font.size = Pt(16)
            run.font.name = "Times New Roman"
            i += 1
            continue

        if stripped.startswith("## "):
            heading_text = stripped[3:]
            doc.add_heading(heading_text, level=1)
            if heading_text == "Abstract":
                in_abstract = True
            else:
                in_abstract = False
            i += 1
            continue

        if stripped.startswith("### "):
            heading_text = stripped[4:]
            doc.add_heading(heading_text, level=2)
            in_abstract = False
            i += 1
            continue

        if stripped.startswith("#### "):
            heading_text = stripped[5:]
            doc.add_heading(heading_text, level=3)
            i += 1
            continue

        # Figure placeholder — insert actual figure
        if "[TO BE COMPLETED WITH DATA:" in stripped or "typology_scatter" in stripped.lower():
            scatter_path = FIGURES_DIR / "typology_scatter.png"
            if scatter_path.exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(str(scatter_path), width=Inches(5.5))
                cap = doc.add_paragraph()
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = cap.add_run(
                    "Figure 1. OECD countries mapped on the two-dimensional "
                    "typology space. Axis 1 (horizontal): task-profile composition "
                    "from PIAAC skill-use data. Axis 2 (vertical): dualization gap "
                    "from OECD EPL indicators."
                )
                run.italic = True
                run.font.size = Pt(10)
            # Skip the whole bracketed placeholder block
            while i < len(lines) and "]" not in lines[i]:
                i += 1
            i += 1
            continue

        # Preference figure placeholder
        if "preference" in stripped.lower() and "[TO BE COMPLETED" in stripped:
            pref_path = FIGURES_DIR / "preference_by_cluster.png"
            if pref_path.exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture(str(pref_path), width=Inches(5.5))
                cap = doc.add_paragraph()
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = cap.add_run(
                    "Figure 2. Welfare preferences by typology cluster. "
                    "Data from OECD Risks that Matter Survey 2022."
                )
                run.italic = True
                run.font.size = Pt(10)
            while i < len(lines) and "]" not in lines[i]:
                i += 1
            i += 1
            continue

        # Author / affiliation (centered lines right after title)
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) < 100:
            inner = stripped[2:-2]
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(inner)
            run.bold = True
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            i += 1
            continue

        # Italic standalone line (affiliation, date)
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            inner = stripped[1:-1]
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(inner)
            run.italic = True
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            i += 1
            continue

        # Plain centered line (e.g., "University of Amsterdam")
        if i > 0 and i < 10 and len(stripped) < 80 and not stripped.startswith("#"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(stripped)
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            i += 1
            continue

        # Keywords line
        if stripped.startswith("**Keywords:**"):
            p = doc.add_paragraph()
            run = p.add_run("Keywords: ")
            run.bold = True
            run = p.add_run(stripped.replace("**Keywords:**", "").strip())
            run.italic = True
            i += 1
            continue

        # Regular paragraph — collect continuation lines
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if (not next_line or next_line.startswith("#") or
                    next_line == "---" or next_line.startswith("[TO BE")):
                break
            para_lines.append(next_line)
            i += 1

        full_text = " ".join(para_lines)
        p = doc.add_paragraph()
        process_inline(p, full_text)

        if in_abstract:
            p.paragraph_format.first_line_indent = Inches(0)
        else:
            p.paragraph_format.first_line_indent = Inches(0.5)


def main():
    # Read updated markdown
    md_text = MD_PATH.read_text(encoding="utf-8")

    # Create document
    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.25)
    section.right_margin = Inches(1.25)

    setup_styles(doc)
    convert_md_to_docx(md_text, doc)

    # Save docx
    doc.save(str(DOCX_PATH))
    print(f"Saved {DOCX_PATH}")

    # Convert to PDF
    try:
        from docx2pdf import convert
        convert(str(DOCX_PATH), str(PDF_PATH))
        print(f"Saved {PDF_PATH}")
    except Exception as e:
        print(f"PDF conversion failed: {e}")
        print("You can open the .docx in Word and Save As PDF manually.")


if __name__ == "__main__":
    main()
