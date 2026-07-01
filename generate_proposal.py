"""
West End on the Thames — Proposal PDF Generator
=================================================

Generates a one-page event proposal PDF matching the brand template
(cream background, photo panel with orange accent strip, two info
boxes overlaid on the photo, logo bottom-left).

USAGE (standalone test):
    python3 generate_proposal.py

USAGE (as a template, e.g. called from a Make.com webhook / scenario
that POSTs JSON to a small wrapper, or imported directly):
    from generate_proposal import generate_proposal_pdf, ProposalData

    data = ProposalData(
        proposal_ref="WE.9055",
        prepared_by="Katherine Bulaon",
        prepared_by_title="Client Relationship Manager",
        date_prepared="27 January 2026",
        quote_valid_days=28,
        client_name="Sarah Prentice",
        organisation="Blue Apple Contract Catering",
        telephone="020 3452 2222",
        email="sarah@blue-apple.co.uk",
        event_type="Summer Event",
        event_date_requested="Saturday 2nd June 2024 (Date TBC)",
        event_timings="13:00hrs - 17:00hrs (TBC)",
        duration_note="Duration of hire can be amended upon request",
        guest_range="40 - 60",
        guest_quote_note="Quote based on a group of up to 40 guests",
        location="London: River Thames",
    )
    generate_proposal_pdf(data, "proposal_output.pdf")

This script is deliberately split into:
  1. A `ProposalData` dataclass — this is exactly the set of fields
     a Make.com "Quote Builder" tab would hand over (one row -> one PDF).
  2. A `generate_proposal_pdf()` function — pure function, no I/O side
     effects beyond writing the one output file, easy to call from a
     webhook handler, CLI, or batch script.
"""

from dataclasses import dataclass
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
import textwrap

# ---------------------------------------------------------------------------
# Brand constants — tweak these once, every proposal stays on-brand
# ---------------------------------------------------------------------------

PAGE_SIZE = landscape((297 * mm, 174 * mm))  # widescreen slide-style page
CREAM = HexColor("#FAF4E6")
ORANGE = HexColor("#E8995E")
DARK = HexColor("#2B2B2B")
GREY = HexColor("#5A5A5A")
BOX_BG = HexColor("#FFFFFF")
BOX_BORDER = HexColor("#CFE3E8")

PHOTO_PATH = "assets/thames_photo.jpg"  # swap per-event if you like
LOGO_TEXT_TOP = "WEST END"
LOGO_TEXT_BOTTOM = "ON THE THAMES"

FONT_BOLD = "Helvetica-Bold"
FONT_REG = "Helvetica"


@dataclass
class ProposalData:
    # --- Quotation meta (left info box) ---
    proposal_ref: str
    prepared_by: str
    prepared_by_title: str
    date_prepared: str
    quote_valid_days: int
    client_name: str
    organisation: str
    telephone: str
    email: str

    # --- Event details (right info box) ---
    event_type: str
    event_date_requested: str
    event_timings: str
    duration_note: str
    guest_range: str
    guest_quote_note: str
    location: str

    # --- Optional overrides ---
    photo_path: str = PHOTO_PATH
    not_held_note: str = (
        "Due to high demand, we do not hold dates at the proposal stage. "
        "All dates are booked on a first-come, first-served basis. Dates "
        "can only be held once a booking form contract has been sent to "
        "you, after which you get a 3-day hold."
    )
    footer_note: str = (
        "The unauthorised use, disclosure, copying or alteration of this "
        "document is strictly forbidden. West End on the Thames is a "
        "subsidiary of Alterniq Events Ltd. Copyright \u00a9 2026."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_wrapped(c, text, x, y, font, size, max_width, leading, color=DARK):
    """Draw left-aligned text wrapped to max_width, returns new y (bottom)."""
    c.setFont(font, size)
    c.setFillColor(color)
    words = text.split()
    line = ""
    for word in words:
        trial = (line + " " + word).strip()
        if stringWidth(trial, font, size) <= max_width:
            line = trial
        else:
            c.drawString(x, y, line)
            y -= leading
            line = word
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def _label_value(c, x, y, label, value, label_font_size=8.5, value_font_size=8.5,
                  max_width=210, leading=11.5):
    """Draw 'Label | value' the way the brand sheet does, wrapping value if needed."""
    c.setFont(FONT_BOLD, label_font_size)
    c.setFillColor(DARK)
    label_str = f"{label} | "
    c.drawString(x, y, label_str)
    label_w = stringWidth(label_str, FONT_BOLD, label_font_size)

    c.setFont(FONT_REG, value_font_size)
    remaining_width = max_width - label_w

    words = value.split()
    line = ""
    first_line = True
    cursor_y = y
    for word in words:
        trial = (line + " " + word).strip()
        avail = remaining_width if first_line else max_width
        if stringWidth(trial, FONT_REG, value_font_size) <= avail:
            line = trial
        else:
            draw_x = x + label_w if first_line else x
            c.drawString(draw_x, cursor_y, line)
            cursor_y -= leading
            line = word
            first_line = False
    if line:
        draw_x = x + label_w if first_line else x
        c.drawString(draw_x, cursor_y, line)
        cursor_y -= leading
    return cursor_y - 3  # small gap before next field


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_proposal_pdf(data: ProposalData, output_path: str):
    page_w, page_h = PAGE_SIZE
    c = canvas.Canvas(output_path, pagesize=PAGE_SIZE)

    # ---- Background ----
    c.setFillColor(CREAM)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # ---- Orange accent strip, far right edge ----
    strip_w = 14 * mm
    c.setFillColor(ORANGE)
    c.rect(page_w - strip_w, 0, strip_w, page_h, fill=1, stroke=0)

    # ---- Photo panel ----
    photo_margin_right = 24 * mm
    photo_w = page_w * 0.535
    photo_h = page_h - 16 * mm
    photo_x = page_w - photo_margin_right - photo_w
    photo_y = (page_h - photo_h) / 2

    try:
        img = ImageReader(data.photo_path)
        c.drawImage(img, photo_x, photo_y, width=photo_w, height=photo_h,
                    preserveAspectRatio=True, anchor='c', mask='auto')
    except Exception:
        c.setFillColor(HexColor("#DDEAEF"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)

    # ---- Title block (left side) ----
    left_x = 20 * mm
    c.setFillColor(DARK)
    c.setFont(FONT_BOLD, 30)
    c.drawString(left_x, page_h - 38 * mm, "OUR")
    c.drawString(left_x, page_h - 50 * mm, "PROPOSAL")

    c.setFillColor(GREY)
    c.setFont(FONT_REG, 13)
    c.drawString(left_x, page_h - 60 * mm, "For Your Event")

    # ---- Logo (bottom left) ----
    logo_x = left_x
    logo_y = 16 * mm
    logo_w = 46 * mm
    logo_h = 13 * mm
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1)
    c.rect(logo_x, logo_y, logo_w, logo_h, fill=0, stroke=1)
    c.setFillColor(ORANGE)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(logo_x + logo_w / 2, logo_y + 7.2 * mm,
                         " ".join(list(LOGO_TEXT_TOP)))
    c.setFont(FONT_REG, 5.5)
    c.drawCentredString(logo_x + logo_w / 2, logo_y + 3.2 * mm,
                         " ".join(list(LOGO_TEXT_BOTTOM)))

    # ---- Info boxes overlaid on top of the photo ----
    box_top = photo_y + photo_h - 6 * mm
    box_h = 58 * mm
    box_gap = 4 * mm
    box_w = (photo_w - 2 * 6 * mm - box_gap) / 2
    box1_x = photo_x + 6 * mm
    box2_x = box1_x + box_w + box_gap
    box_y = box_top - box_h

    for bx in (box1_x, box2_x):
        c.setFillColor(BOX_BG)
        c.setStrokeColor(BOX_BORDER)
        c.setLineWidth(0.75)
        c.roundRect(bx, box_y, box_w, box_h, 2, fill=1, stroke=1)

    pad = 4 * mm
    text_w = box_w - 2 * pad

    # --- Box 1: Quotation meta ---
    y = box_y + box_h - pad - 6
    y = _label_value(c, box1_x + pad, y, "Proposal/Quotation Ref", data.proposal_ref, max_width=text_w)
    y = _label_value(c, box1_x + pad, y, "Prepared by",
                      f"{data.prepared_by} | {data.prepared_by_title}", max_width=text_w)
    y = _label_value(c, box1_x + pad, y, data.date_prepared,
                      f"Quotation valid for {data.quote_valid_days} days", max_width=text_w)
    y -= 5
    y = _label_value(c, box1_x + pad, y, "Client Name", data.client_name, max_width=text_w)
    y = _label_value(c, box1_x + pad, y, "Organisation", data.organisation, max_width=text_w)
    y = _label_value(c, box1_x + pad, y, "Telephone", data.telephone, max_width=text_w)
    y = _label_value(c, box1_x + pad, y, "Email", data.email, max_width=text_w)

    y -= 4
    c.setFont(FONT_REG, 5.8)
    c.setFillColor(GREY)
    wrapped = textwrap.wrap(data.footer_note, width=72)
    for line in wrapped:
        if y < box_y + pad:
            break
        c.drawString(box1_x + pad, y, line)
        y -= 7.5

    # --- Box 2: Event details ---
    y = box_y + box_h - pad - 6
    y = _label_value(c, box2_x + pad, y, "Event type", data.event_type, max_width=text_w)
    y = _label_value(c, box2_x + pad, y, "Event date requested", data.event_date_requested, max_width=text_w)
    y -= 2
    c.setFont(FONT_BOLD, 8.5)
    c.setFillColor(DARK)
    y = _draw_wrapped(c, "Date not held - " + data.not_held_note, box2_x + pad, y,
                       FONT_REG, 7.3, text_w, 9.2, color=GREY)
    y -= 3
    y = _label_value(c, box2_x + pad, y, "Event timings", data.event_timings, max_width=text_w)
    c.setFont(FONT_REG, 7.3)
    c.setFillColor(GREY)
    c.drawString(box2_x + pad, y, data.duration_note)
    y -= 12

    y = _label_value(c, box2_x + pad, y, "No. of guests", data.guest_range, max_width=text_w)
    c.setFont(FONT_REG, 7.3)
    c.setFillColor(GREY)
    c.drawString(box2_x + pad, y, data.guest_quote_note)
    y -= 12

    y = _label_value(c, box2_x + pad, y, "Location", data.location, max_width=text_w)

    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# CLI / quick test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample = ProposalData(
        proposal_ref="WE.9055",
        prepared_by="Katherine Bulaon",
        prepared_by_title="Client Relationship Manager",
        date_prepared="27 January 2026",
        quote_valid_days=28,
        client_name="Sarah Prentice",
        organisation="Blue Apple Contract Catering",
        telephone="020 3452 2222",
        email="sarah@blue-apple.co.uk",
        event_type="Summer Event",
        event_date_requested="Saturday 2nd June 2024 (Date TBC)",
        event_timings="13:00hrs - 17:00hrs (TBC)",
        duration_note="Duration of hire can be amended upon request",
        guest_range="40 - 60",
        guest_quote_note="Quote based on a group of up to 40 guests",
        location="London: River Thames",
    )
    generate_proposal_pdf(sample, "/mnt/user-data/outputs/proposal_sample.pdf")
    print("Done.")
