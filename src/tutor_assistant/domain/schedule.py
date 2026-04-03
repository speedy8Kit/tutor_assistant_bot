import datetime
import re


_DAY_MAP: dict[str, int] = {
    "ПН": 0,
    "ВТ": 1,
    "СР": 2,
    "ЧТ": 3,
    "ПТ": 4,
    "СБ": 5,
    "ВС": 6,
}
_DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_SLOT_RE = re.compile(r"^(ПН|ВТ|СР|ЧТ|ПТ|СБ|ВС)\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)


def _parse_slot(text: str) -> tuple[int, datetime.time] | None:
    m = _SLOT_RE.match(text.strip().upper())
    if not m:
        return None
    day = _DAY_MAP[m.group(1)]
    hour, minute = int(m.group(2)), int(m.group(3))
    if hour > 23 or minute > 59:
        return None
    return day, datetime.time(hour, minute)


def _format_slots(slots: list[tuple[int, datetime.time]]) -> str:
    return "\n".join(f"  {_DAY_NAMES[d]} {t:%H:%M}" for d, t in slots)