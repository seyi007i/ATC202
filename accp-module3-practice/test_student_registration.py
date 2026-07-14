"""Tests for student_registration.validate_student_registration."""

import pytest

from student_registration import validate_student_registration


def make_registration(**overrides):
    registration = {
        "name": "Ada Okafor",
        "email": "ada.okafor@example.com",
        "phone": "0803-123-4567",
        "course": "Computer Science",
    }
    registration.update(overrides)
    return registration


class TestValidRegistration:
    def test_valid_registration_is_standardized(self):
        result = validate_student_registration(make_registration())
        assert result == {
            "name": "Ada Okafor",
            "email": "ada.okafor@example.com",
            "phone": "+2348031234567",
            "course": "Computer Science",
        }

    def test_strips_surrounding_whitespace(self):
        result = validate_student_registration(
            make_registration(name="  Ada Okafor  ", email=" ada.okafor@example.com ", course=" Computer Science ")
        )
        assert result["name"] == "Ada Okafor"
        assert result["email"] == "ada.okafor@example.com"
        assert result["course"] == "Computer Science"

    def test_international_phone_is_standardized(self):
        result = validate_student_registration(make_registration(phone="+2348031234567"))
        assert result["phone"] == "+2348031234567"

    def test_hyphenated_name_allowed(self):
        result = validate_student_registration(make_registration(name="Chioma Eze-Nwosu"))
        assert result["name"] == "Chioma Eze-Nwosu"


class TestInvalidInputTypes:
    @pytest.mark.parametrize("value", [None, "not a dict", 123, ["name", "email"]])
    def test_non_dict_raises_type_error(self, value):
        with pytest.raises(TypeError):
            validate_student_registration(value)

    @pytest.mark.parametrize("field", ["name", "email", "course"])
    def test_non_string_field_raises_type_error(self, field):
        with pytest.raises(TypeError):
            validate_student_registration(make_registration(**{field: 12345}))

    def test_non_string_phone_raises_type_error(self):
        with pytest.raises(TypeError):
            validate_student_registration(make_registration(phone=12345))


class TestMissingFields:
    @pytest.mark.parametrize("field", ["name", "email", "phone", "course"])
    def test_missing_field_raises_value_error(self, field):
        registration = make_registration()
        del registration[field]
        with pytest.raises(ValueError):
            validate_student_registration(registration)


class TestEmptyFields:
    @pytest.mark.parametrize("field", ["name", "email", "course"])
    def test_empty_field_raises_value_error(self, field):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(**{field: "   "}))

    def test_empty_phone_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(phone=""))


class TestMalformedFields:
    @pytest.mark.parametrize(
        "name", ["Ada123", "!!!", "1234"]
    )
    def test_invalid_name_raises_value_error(self, name):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(name=name))

    @pytest.mark.parametrize(
        "email", ["not-an-email", "ada@", "@example.com", "ada.example.com"]
    )
    def test_invalid_email_raises_value_error(self, email):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(email=email))

    @pytest.mark.parametrize("course", ["!!!", "   *&^%"])
    def test_invalid_course_raises_value_error(self, course):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(course=course))


class TestPhoneValidationPropagation:
    def test_invalid_prefix_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(phone="07001234567"))

    def test_unsupported_country_code_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(phone="+18031234567"))

    def test_incorrect_length_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_student_registration(make_registration(phone="080312345"))
