"""Renders a concluded manuscript to a PDF keepsake. Deliberately not a screenshot of
the illustrated console -- a clean, single-column document with a letterhead, built with
fpdf2 (pure-Python, no system-level dependencies like Pango/Cairo)."""

import os
from datetime import date

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_HERE = os.path.dirname(__file__)
FONT_DIR = os.path.join(_HERE, "assets", "fonts")

INK = (31, 29, 26)
BRASS = (184, 134, 59)
SLATE = (107, 100, 89)

# The vendored latin-subset webfonts don't reliably cover "smart" typographic
# punctuation that LLM-generated prose leans on constantly (em/en dashes, curly
# quotes, ellipsis) -- fpdf2 raises rather than substituting, so normalize to plain
# ASCII equivalents before anything gets rendered. This is defensive by design: the
# story text is model output we don't fully control the character set of.
_SMART_PUNCTUATION = str.maketrans({
    "—": "-", "–": "-",       # em dash, en dash
    "‘": "'", "’": "'",       # curly single quotes
    "“": '"', "”": '"',       # curly double quotes
    "…": "...",                    # ellipsis
    " ": " ",                      # non-breaking space
})


def _pdf_safe(text: str) -> str:
    return (text or "").translate(_SMART_PUNCTUATION)


def _today_iso() -> str:
    return date.today().isoformat()


def render_pdf(req) -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(22, 22, 22)
    pdf.add_page()

    pdf.add_font("Fraunces", "", os.path.join(FONT_DIR, "Fraunces", "Fraunces-Bold.ttf"))
    pdf.add_font("Literata", "", os.path.join(FONT_DIR, "Literata", "Literata-Regular.ttf"))
    pdf.add_font("Literata", "I", os.path.join(FONT_DIR, "Literata", "Literata-Italic.ttf"))

    # multi_cell/cell leave the X cursor wherever the text ended, not reset to the
    # margin -- pass new_x/new_y explicitly on every call rather than relying on
    # version-dependent defaults, or the next call inherits almost no width.
    full_width = dict(new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Fraunces", "", 20)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 11, _pdf_safe(req.agency_name) or "The Great Automatic Grammatizator", **full_width)

    pdf.set_font("Literata", "I", 10.5)
    pdf.set_text_color(*SLATE)
    byline = f"Manufactured for {_pdf_safe(req.user_name)}" if req.user_name else "Manufactured automatically"
    pdf.multi_cell(0, 6, f"{byline} - {_today_iso()} - {req.word_count} words", **full_width)

    pdf.set_draw_color(*BRASS)
    pdf.set_line_width(0.7)
    y = pdf.get_y() + 3
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_y(y + 8)

    pdf.set_font("Literata", "", 11.5)
    pdf.set_text_color(*INK)
    story = _pdf_safe(req.story)
    paragraphs = [p.strip() for p in story.split("\n\n") if p.strip()] or [story.strip()]
    for paragraph in paragraphs:
        pdf.multi_cell(0, 6.5, paragraph, **full_width)
        pdf.ln(3.5)

    # Disable auto page-break before the footer -- otherwise landing this close to the
    # bottom margin can itself trigger an unwanted trailing blank page.
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-18)
    pdf.set_font("Literata", "I", 8)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 8, "Produced by the Great Automatic Grammatizator", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    output = pdf.output()
    return bytes(output)
