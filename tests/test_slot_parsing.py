"""Unit tests for slot-parsing logic in the add_student handler."""

import datetime

from tutor_assistant.application.handlers.add_student import _format_slots, _parse_slot


class TestParseSlot:
    def test_valid_monday(self):
        assert _parse_slot("ПН 09:00") == (0, datetime.time(9, 0))

    def test_valid_sunday(self):
        assert _parse_slot("ВС 23:59") == (6, datetime.time(23, 59))

    def test_valid_mixed_case(self):
        assert _parse_slot("пн 14:30") == (0, datetime.time(14, 30))

    def test_valid_single_digit_hour(self):
        assert _parse_slot("СР 9:05") == (2, datetime.time(9, 5))

    def test_valid_with_extra_spaces(self):
        assert _parse_slot("  ПТ 18:00  ") == (4, datetime.time(18, 0))

    def test_all_days(self):
        days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, day in enumerate(days):
            result = _parse_slot(f"{day} 10:00")
            assert result is not None
            assert result[0] == i

    def test_invalid_no_time(self):
        assert _parse_slot("ПН") is None

    def test_invalid_wrong_day(self):
        assert _parse_slot("MON 10:00") is None

    def test_invalid_hour_too_large(self):
        assert _parse_slot("ПН 25:00") is None

    def test_invalid_minute_too_large(self):
        assert _parse_slot("ПН 10:60") is None

    def test_invalid_empty_string(self):
        assert _parse_slot("") is None

    def test_invalid_random_text(self):
        assert _parse_slot("завтра в три") is None

    def test_invalid_reversed_format(self):
        assert _parse_slot("14:30 ПН") is None


class TestFormatSlots:
    def test_single_slot(self):
        result = _format_slots([(0, datetime.time(14, 30))])
        assert "Пн" in result
        assert "14:30" in result

    def test_multiple_slots(self):
        result = _format_slots([(0, datetime.time(9, 0)), (4, datetime.time(18, 0))])
        assert "Пн" in result
        assert "09:00" in result
        assert "Пт" in result
        assert "18:00" in result
        assert result.count("\n") == 1  # two lines → one separator

    def test_empty_slots(self):
        assert _format_slots([]) == ""
