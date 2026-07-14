"""Validation of student registration records."""

import re

from phone_validator import validate_nigerian_phone_number

REQUIRED_FIELDS = ("name", "email", "phone", "course")

NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z'\-. ]*$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
COURSE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &\-/.]*$")


def validate_student_registration(registration: dict) -> dict:
    """Validate a student registration record.

    Validates the ``name``, ``email``, ``phone``, and ``course`` fields of a
    registration record, standardizing ``phone`` via
    :func:`phone_validator.validate_nigerian_phone_number`.

    Args:
        registration: A dict with the keys "name", "email", "phone", and
            "course", all string values.

    Returns:
        dict: A new dict with the same keys, with ``name``/``email``/
        ``course`` stripped of surrounding whitespace and ``phone``
        standardized to "+234XXXXXXXXXX".

    Raises:
        TypeError: If ``registration`` is not a dict, or if any field value
            is not a string.
        ValueError: If a required field is missing, empty, malformed (e.g.
            an invalid email format or a name containing digits/symbols), or
            if the phone number fails validation (invalid format, invalid
            Nigerian prefix, unsupported country code, or incorrect length).
    """
    if not isinstance(registration, dict):
        raise TypeError(
            f"registration must be a dict, got {type(registration).__name__}"
        )

    missing_fields = [field for field in REQUIRED_FIELDS if field not in registration]
    if missing_fields:
        raise ValueError(f"Missing required field(s): {', '.join(missing_fields)}")

    name = registration["name"]
    if not isinstance(name, str):
        raise TypeError(f"name must be a string, got {type(name).__name__}")
    name = name.strip()
    if not name:
        raise ValueError("name must not be empty")
    if not NAME_PATTERN.match(name):
        raise ValueError(f"Invalid name: {name!r}")

    email = registration["email"]
    if not isinstance(email, str):
        raise TypeError(f"email must be a string, got {type(email).__name__}")
    email = email.strip()
    if not email:
        raise ValueError("email must not be empty")
    if not EMAIL_PATTERN.match(email):
        raise ValueError(f"Invalid email format: {email!r}")

    phone = validate_nigerian_phone_number(registration["phone"])

    course = registration["course"]
    if not isinstance(course, str):
        raise TypeError(f"course must be a string, got {type(course).__name__}")
    course = course.strip()
    if not course:
        raise ValueError("course must not be empty")
    if not COURSE_PATTERN.match(course):
        raise ValueError(f"Invalid course: {course!r}")

    return {"name": name, "email": email, "phone": phone, "course": course}


def main() -> None:
    """Prompt for registration details on the console and print the result."""
    registration = {
        "name": input("Name: "),
        "email": input("Email: "),
        "phone": input("Phone (e.g. 08031234567 or +2348031234567): "),
        "course": input("Course: "),
    }

    try:
        validated = validate_student_registration(registration)
    except (TypeError, ValueError) as error:
        print(f"Registration invalid: {error}")
        return

    print("Registration valid:")
    for field, value in validated.items():
        print(f"  {field}: {value}")


if __name__ == "__main__":
    main()
