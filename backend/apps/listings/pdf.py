"""
Generates a small printable price tag PDF for a single game listing, sized
to 2in x 3in (a common hang-tag/price-tag size).
"""
import io

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .models import CONDITION_DESCRIPTIONS

POINTS_PER_INCH = 72
PAGE_WIDTH = 2 * POINTS_PER_INCH
PAGE_HEIGHT = 3 * POINTS_PER_INCH
MARGIN = 8
USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN


def _clamp_to_width(word, font_name, font_size, max_width):
    """
    Hard-truncates a single word that is, by itself, wider than max_width -
    e.g. a data-entry mistake with no spaces, or a pathologically long
    token. Without this, such a word would be placed alone on its own line
    and overflow the fixed-size page, which is worse than losing characters
    from an already-unrealistic input.
    """
    if stringWidth(word, font_name, font_size) <= max_width:
        return word
    while word and stringWidth(word, font_name, font_size) > max_width:
        word = word[:-1]
    return word


def _wrap_text(text, font_name, font_size, max_width):
    """Greedy word-wrap for a single canvas font; returns a list of lines.
    No returned line ever exceeds max_width, even for a single overlong word."""
    words = [_clamp_to_width(w, font_name, font_size, max_width) for w in text.split()]
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_font_size(text, font_name, start_size, min_size, max_width, max_lines):
    """Shrinks font size until the wrapped text fits within max_lines."""
    size = start_size
    while size > min_size:
        if len(_wrap_text(text, font_name, size, max_width)) <= max_lines:
            break
        size -= 1
    return size


def _wrap_with_ellipsis(text, font_name, font_size, max_width, max_lines):
    """
    Like _wrap_text, but if the text doesn't fit in max_lines even after
    wrapping, the last visible line is truncated with a trailing ellipsis
    so it's clear the name was cut off rather than silently dropping words.
    """
    lines = _wrap_text(text, font_name, font_size, max_width)
    if len(lines) <= max_lines:
        return lines

    visible = lines[:max_lines]
    last = visible[-1]
    ellipsis = "…"
    while last and stringWidth(last + ellipsis, font_name, font_size) > max_width:
        last = last[:-1].rstrip()
    visible[-1] = last + ellipsis
    return visible


MAX_PRINT_ALL = 500


def _draw_tag(c, listing, convention_name: str) -> None:
    """Draws one price tag onto the current page of an open canvas. Caller
    is responsible for the page break (c.showPage()) before/after."""
    # Decorative border for the tag.
    c.setLineWidth(1)
    c.roundRect(3, 3, PAGE_WIDTH - 6, PAGE_HEIGHT - 6, 6, stroke=1, fill=0)

    y = PAGE_HEIGHT - MARGIN

    # Header: convention name + game ID, top right corner.
    header_text = f"{convention_name} #{listing.id}"
    header_size = 7.0
    while stringWidth(header_text, "Helvetica-Bold", header_size) > USABLE_WIDTH and header_size > 5:
        header_size -= 0.5
    y -= header_size
    c.setFont("Helvetica-Bold", header_size)
    c.drawRightString(PAGE_WIDTH - MARGIN, y, header_text)
    y -= 6

    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_WIDTH - MARGIN, y)
    y -= 13

    # Game name - centered, bold, shrinks to fit up to 2 lines.
    name_size = _fit_font_size(listing.game_name, "Helvetica-Bold", 13, 8, USABLE_WIDTH, 2)
    c.setFont("Helvetica-Bold", name_size)
    for line in _wrap_with_ellipsis(listing.game_name, "Helvetica-Bold", name_size, USABLE_WIDTH, 2):
        y -= name_size
        c.drawCentredString(PAGE_WIDTH / 2, y, line)
    y -= 10

    # Price - the main event on a price tag.
    c.setFont("Helvetica-Bold", 22)
    y -= 18
    c.drawCentredString(PAGE_WIDTH / 2, y, f"${listing.price:.2f}")
    y -= 12

    # Condition, with its description in small italics underneath.
    c.setFont("Helvetica-Bold", 9)
    y -= 9
    c.drawCentredString(PAGE_WIDTH / 2, y, listing.get_condition_display())

    condition_desc = str(CONDITION_DESCRIPTIONS.get(listing.condition, ""))
    if condition_desc:
        c.setFont("Helvetica-Oblique", 6)
        for line in _wrap_text(condition_desc, "Helvetica-Oblique", 6, USABLE_WIDTH)[:2]:
            y -= 7
            c.drawCentredString(PAGE_WIDTH / 2, y, line)
    y -= 10

    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_WIDTH - MARGIN, y)
    y -= 12

    # Details - left-aligned bullet list of everything the seller noted.
    bullet_lines = []
    if listing.has_missing_pieces:
        text = "Missing pieces"
        if listing.missing_pieces_description:
            text += f": {listing.missing_pieces_description}"
        bullet_lines.append(text)
    if listing.smoking_household:
        bullet_lines.append("Smoking household")
    if listing.musty_smell:
        bullet_lines.append("Musty smell")
    if listing.pet_exposure:
        bullet_lines.append(f"Pet exposure: {listing.get_pet_exposure_display()}")

    c.setFont("Helvetica", 7)
    for line in bullet_lines:
        if y < MARGIN + 9:
            break
        wrapped = _wrap_text(line, "Helvetica", 7, USABLE_WIDTH - 8)
        for i, sub in enumerate(wrapped):
            if y < MARGIN + 9:
                break
            prefix = "• " if i == 0 else "   "
            c.drawString(MARGIN, y, prefix + sub)
            y -= 9

    # Comments, if there's room left.
    if listing.comments and y > MARGIN + 14:
        y -= 3
        quoted = f"“{listing.comments}”"
        c.setFont("Helvetica-Oblique", 6.5)
        for line in _wrap_with_ellipsis(quoted, "Helvetica-Oblique", 6.5, USABLE_WIDTH, 3):
            if y < MARGIN + 6:
                break
            c.drawCentredString(PAGE_WIDTH / 2, y, line)
            y -= 8


def generate_price_tag_pdf(listing, convention_name: str) -> bytes:
    """Single listing, single-page PDF."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    _draw_tag(c, listing, convention_name)
    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_price_tags_pdf(listings, convention_name: str) -> bytes:
    """Multiple listings, one page per listing, in a single PDF - used by
    the admin "print all filtered" action."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    for listing in listings:
        _draw_tag(c, listing, convention_name)
        c.showPage()
    c.save()
    return buffer.getvalue()
