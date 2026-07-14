"""Validation and normalization of Nigerian phone numbers."""

import re

# Valid Nigerian mobile network prefixes (3 digits, without the leading 0 or
# country code), covering MTN, Glo, Airtel, and 9mobile ranges.
VALID_PREFIXES = {
    "701", "702", "703", "704", "705", "706", "707", "708", "709",
    "802", "803", "804", "805", "806", "807", "808", "809",
    "810", "811", "812", "813", "814", "815", "816", "817", "818", "819",
    "901", "902", "903", "904", "905", "906", "907", "908", "909",
    "910", "911", "912", "913", "914", "915", "916", "917", "918", "919",
}

COUNTRY_CODE = "234"


def validate_nigerian_phone_number(phone_number: str) -> str:
    """Validate a Nigerian phone number and return its standardized form.

    Accepts local format (e.g. "08012345678") or international format
    (e.g. "+2348012345678", "2348012345678", with optional spaces/hyphens),
    and normalizes either into "+234XXXXXXXXXX".

    Args:
        phone_number: The phone number to validate.

    Returns:
        str: The phone number standardized as "+234XXXXXXXXXX".

    Raises:
        TypeError: If ``phone_number`` is not a string.
        ValueError: If the number is empty, contains non-digit characters
            (after stripping spaces/hyphens/parentheses), has an unsupported
            country code, has an invalid Nigerian mobile prefix, or does not
            match the expected length for its format.
    """
    if not isinstance(phone_number, str):
        raise TypeError(
            f"phone_number must be a string, got {type(phone_number).__name__}"
        )

    cleaned = re.sub(r"[\s\-()]", "", phone_number)

    if not cleaned:
        raise ValueError("phone_number must not be empty")

    if cleaned.startswith("+"):
        digits = cleaned[1:]
        if not digits.isdigit():
            raise ValueError(f"Malformed phone number: {phone_number!r}")
        if not digits.startswith(COUNTRY_CODE):
            raise ValueError(
                f"Unsupported country code in {phone_number!r}; only +234 is supported"
            )
        subscriber_number = digits[len(COUNTRY_CODE):]
    elif cleaned.startswith(COUNTRY_CODE):
        if not cleaned.isdigit():
            raise ValueError(f"Malformed phone number: {phone_number!r}")
        subscriber_number = cleaned[len(COUNTRY_CODE):]
    elif cleaned.startswith("0"):
        if not cleaned.isdigit():
            raise ValueError(f"Malformed phone number: {phone_number!r}")
        if len(cleaned) != 11:
            raise ValueError(
                f"Local phone number must have 11 digits, got {len(cleaned)}: {phone_number!r}"
            )
        subscriber_number = cleaned[1:]
    else:
        raise ValueError(
            f"Unsupported phone number format: {phone_number!r}"
        )

    if len(subscriber_number) != 10:
        raise ValueError(
            f"Phone number must have 10 digits after the country code/leading 0, "
            f"got {len(subscriber_number)}: {phone_number!r}"
        )

    prefix = subscriber_number[:3]
    if prefix not in VALID_PREFIXES:
        raise ValueError(f"Invalid Nigerian network prefix: {prefix!r}")

    return f"+{COUNTRY_CODE}{subscriber_number}"
