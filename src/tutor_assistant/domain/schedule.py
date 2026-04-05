import datetime
import re
import unicodedata


_DAY_MAP: dict[str, int] = {
    "ПН": 0,
    "ВТ": 1,
    "СР": 2,
    "ЧТ": 3,
    "ПТ": 4,
    "СБ": 5,
    "ВС": 6,
}
DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_SLOT_RE = re.compile(r"^(ПН|ВТ|СР|ЧТ|ПТ|СБ|ВС)\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)


def _clean(text: str) -> str:
    """Remove invisible Unicode characters (control/format) and normalize whitespace.

    Also inserts a space between Cyrillic letters and digits so that an invisible
    character that was the only separator (e.g. zero-width space) doesn't collapse
    'ПН10:00' into an unrecognized token.
    """
    visible = "".join(ch for ch in text if not unicodedata.category(ch).startswith("C"))
    normalized = " ".join(visible.split()).upper()
    # If invisible char replaced the space: 'ПН10:00' → 'ПН 10:00'
    return re.sub(r"([А-ЯЁ]+)(\d)", r"\1 \2", normalized)


def parse_slot(text: str) -> tuple[int, datetime.time] | None:
    m = _SLOT_RE.match(_clean(text))
    if not m:
        return None
    day = _DAY_MAP[m.group(1)]
    hour, minute = int(m.group(2)), int(m.group(3))
    if hour > 23 or minute > 59:
        return None
    return day, datetime.time(hour, minute)


def format_slots(slots: list[tuple[int, datetime.time]]) -> str:
    return "\n".join(f"  {DAY_NAMES[d]} {t:%H:%M}" for d, t in slots)
