"""
CSV import support for bulk-creating game listings, plus the downloadable
example/template file shown to users so they know exactly how to format
their own CSV.
"""
import csv

from .models import GameCondition, PetExposure

MAX_ROWS = 500

TRUE_VALUES = {"true", "1", "yes", "y"}


def parse_bool(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in TRUE_VALUES


def _normalize_choice(value, choices_enum) -> str:
    """
    Accepts either the exact stored code (e.g. "very_good") or the plain
    English label (e.g. "Very Good"), case/spacing-insensitive. Anything
    else is returned unchanged so the serializer's own validation produces
    a clear "not a valid choice" error naming the bad value.
    """
    if not value:
        return ""
    v = value.strip()
    if not v:
        return ""
    key = v.lower().replace(" ", "_").replace("-", "_")
    valid_keys = {choice.value for choice in choices_enum}
    if key in valid_keys:
        return key
    for choice in choices_enum:
        if str(choice.label).strip().lower() == v.lower():
            return choice.value
    return v


def _normalize_header(name: str) -> str:
    return name.strip().lower().rstrip("?:").replace(" ", "_").replace("-", "_")


def normalize_row(raw_row: dict) -> dict:
    return {
        "game_name": (raw_row.get("game_name") or "").strip(),
        "price": (raw_row.get("price") or "").strip(),
        "condition": _normalize_choice(raw_row.get("condition"), GameCondition),
        "has_missing_pieces": parse_bool(raw_row.get("has_missing_pieces")),
        "missing_pieces_description": (raw_row.get("missing_pieces_description") or "").strip(),
        "smoking_household": parse_bool(raw_row.get("smoking_household")),
        "musty_smell": parse_bool(raw_row.get("musty_smell")),
        "pet_exposure": _normalize_choice(raw_row.get("pet_exposure"), PetExposure),
        "comments": (raw_row.get("comments") or "").strip(),
    }


def parse_csv_file(file_obj) -> list[dict]:
    """
    Reads an uploaded CSV, skipping blank lines and "#"-prefixed comment
    lines (used by the template to document each column inline), and
    returns a list of raw row dicts keyed by normalized header name.
    """
    raw = file_obj.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")  # utf-8-sig strips a BOM from Excel exports
    lines = [line for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines)
    reader.fieldnames = [_normalize_header(name) for name in (reader.fieldnames or [])]
    return list(reader)


TEMPLATE_CSV = """# BaseWeb Game Listing Import Template
#
# HOW THIS WORKS
# Each row below (other than comments and the header) becomes one game
# listing under your account once uploaded. Lines starting with "#" -
# like every line in this block - are comments and are ignored by the
# importer, so it is safe to upload this exact file as a test: it will
# create the 10 example listings below it. When you're ready, delete
# these comment lines and the example rows, keep the header row, and
# add your own rows underneath it.
#
# COLUMN REFERENCE
#   game_name            Text. Required. The name of the game.
#   price                Number. Required. Dollar amount with no
#                         currency symbol, e.g. 25.99
#   condition            Required. One of the following codes (plain
#                         English labels like "Very Good" also work and
#                         are converted automatically):
#                           new_in_shrink  New in Shrink
#                                          (original shrink wrap, never opened)
#                           like_new       Like New
#                                          (pieces unpunched, cards wrapped, never played)
#                           very_good      Very Good
#                                          (pieces punched, sorted, rarely/never
#                                           played, no discernible wear)
#                           good           Good
#                                          (played but well maintained, pieces
#                                           unsorted, box shows signs of use)
#                           fair           Fair
#                                          (discernible wear, box/book show minor
#                                           damage, slightly marked)
#                           poor           Poor
#                                          (worn but playable, box/book show
#                                           damage and/or significantly marked)
#   has_missing_pieces   TRUE or FALSE. Optional, defaults to FALSE.
#   missing_pieces_description
#                        Text, max 64 characters. Optional. Only
#                        meaningful when has_missing_pieces is TRUE, e.g.
#                        "Missing 2 red meeples, 1 die". Ignored (cleared)
#                        if has_missing_pieces is FALSE.
#   smoking_household    TRUE or FALSE. Optional, defaults to FALSE.
#   musty_smell          TRUE or FALSE. Optional, defaults to FALSE.
#   pet_exposure         One of: cat, dog, multiple. Leave blank if the
#                         game was never exposed to any pets.
#   comments             Text, max 64 characters. Optional. Any other
#                         notes about this listing.
#
# A FEW CSV BASICS
#   - The first row must be the header (the column names) - don't delete
#     it, only replace the example data rows beneath it.
#   - If a value itself contains a comma, wrap the whole value in double
#     quotes, e.g. "Missing 1 die, 2 tokens".
#   - Leaving a value blank between two commas (like the pet_exposure
#     column in most rows below) means "no value" for that column.
#
# LIMITS
#   Up to 500 rows per upload. Rows with errors are skipped and reported
#   individually - valid rows in the same file are still imported.
#
game_name,price,condition,has_missing_pieces,missing_pieces_description,smoking_household,musty_smell,pet_exposure,comments
Catan,25.00,very_good,FALSE,,FALSE,FALSE,cat,Great starter game - highly recommend
Ticket to Ride,18.50,good,FALSE,,FALSE,FALSE,,Kids love this one
Pandemic,12.00,fair,TRUE,Missing 2 blue infection cubes,FALSE,FALSE,dog,Ask about bundle discount
Monopoly (Vintage 1970s Edition),8.00,poor,TRUE,"Missing dog token, 3 houses",TRUE,TRUE,multiple,Vintage edition - collectors item
Azul,30.00,like_new,FALSE,,FALSE,FALSE,,Barely played once
Wingspan,45.00,new_in_shrink,FALSE,,FALSE,FALSE,,Still sealed - perfect gift
Carcassonne,20.00,good,FALSE,,FALSE,FALSE,dog,Comes with one expansion
Gloomhaven,60.00,very_good,FALSE,,TRUE,FALSE,,Heavy box - large and heavy
Codenames,10.00,fair,FALSE,,FALSE,TRUE,cat,Great for game night
Risk,5.00,poor,TRUE,Missing 1 red army piece,FALSE,FALSE,,Classic but well loved
"""
