import re

import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_international_phone_number(value: str) -> str:
    """
    Validates a phone number using Google's libphonenumber (via the
    `phonenumbers` package) and normalizes it to E.164 format.
    """
    try:
        parsed = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException as exc:
        raise ValidationError(
            _("Enter a valid phone number in international format, e.g. +14155552671."),
            code="invalid_phone",
        ) from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError(_("This phone number is not valid."), code="invalid_phone")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class ComplexityPasswordValidator:
    """Requires at least one uppercase, one lowercase, one digit and one symbol."""

    UPPER_RE = re.compile(r"[A-Z]")
    LOWER_RE = re.compile(r"[a-z]")
    DIGIT_RE = re.compile(r"\d")
    SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")

    def validate(self, password, user=None):
        errors = []
        if not self.UPPER_RE.search(password):
            errors.append(_("Password must contain at least one uppercase letter."))
        if not self.LOWER_RE.search(password):
            errors.append(_("Password must contain at least one lowercase letter."))
        if not self.DIGIT_RE.search(password):
            errors.append(_("Password must contain at least one digit."))
        if not self.SYMBOL_RE.search(password):
            errors.append(_("Password must contain at least one special character."))
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Your password must contain at least one uppercase letter, one lowercase "
            "letter, one digit, and one special character."
        )
