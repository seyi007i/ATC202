"""Tests for phone_validator.validate_nigerian_phone_number."""

import pytest

from phone_validator import validate_nigerian_phone_number


class TestValidFormats:
    def test_local_format(self):
        assert validate_nigerian_phone_number("08031234567") == "+2348031234567"

    def test_international_with_plus(self):
        assert validate_nigerian_phone_number("+2348031234567") == "+2348031234567"

    def test_international_without_plus(self):
        assert validate_nigerian_phone_number("2348031234567") == "+2348031234567"

    def test_strips_spaces(self):
        assert validate_nigerian_phone_number("+234 803 123 4567") == "+2348031234567"

    def test_strips_hyphens(self):
        assert validate_nigerian_phone_number("0803-123-4567") == "+2348031234567"

    def test_strips_parentheses(self):
        assert validate_nigerian_phone_number("(0803) 123-4567") == "+2348031234567"

    @pytest.mark.parametrize(
        "prefix", ["701", "802", "813", "909", "916"]
    )
    def test_various_valid_prefixes(self, prefix):
        local = f"0{prefix}1234567"
        assert validate_nigerian_phone_number(local) == f"+234{prefix}1234567"


class TestInvalidInputTypes:
    @pytest.mark.parametrize("value", [None, 8012345678, 12.3, ["0801234567"], {}])
    def test_non_string_raises_type_error(self, value):
        with pytest.raises(TypeError):
            validate_nigerian_phone_number(value)


class TestEmptyInput:
    @pytest.mark.parametrize("value", ["", "   ", "()"])
    def test_empty_raises_value_error(self, value):
        with pytest.raises(ValueError):
            validate_nigerian_phone_number(value)


class TestMalformedNumbers:
    @pytest.mark.parametrize(
        "value",
        ["0803abcd567", "+234abcd12345", "phone number", "080-ABC-1234"],
    )
    def test_non_digit_characters_raise_value_error(self, value):
        with pytest.raises(ValueError):
            validate_nigerian_phone_number(value)


class TestInvalidPrefixes:
    @pytest.mark.parametrize("value", ["07001234567", "+2346001234567", "06012345678"])
    def test_invalid_prefix_raises_value_error(self, value):
        with pytest.raises(ValueError):
            validate_nigerian_phone_number(value)


class TestUnsupportedCountryCodes:
    @pytest.mark.parametrize(
        "value", ["+18012345678", "+447911123456", "+254701234567"]
    )
    def test_unsupported_country_code_raises_value_error(self, value):
        with pytest.raises(ValueError):
            validate_nigerian_phone_number(value)


class TestIncorrectLengths:
    @pytest.mark.parametrize(
        "value",
        [
            "080123456",  # too short local
            "080123456789",  # too long local
            "+23480123456",  # too short international
            "+2348012345678901",  # too long international
        ],
    )
    def test_incorrect_length_raises_value_error(self, value):
        with pytest.raises(ValueError):
            validate_nigerian_phone_number(value)
