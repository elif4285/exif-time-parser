from __future__ import annotations

from datetime import datetime
from typing import Optional

# Common EXIF DateTime/DateTimeOriginal/DateTimeDigitized canonical form,
# as written by most cameras: "YYYY:MM:DD HH:MM:SS".
# Some software (notably older Apple tools) writes the same but with a
# space before a subsecond field, and some write a trailing "+00:00" or
# "Z". We deliberately scope this to the three shapes that occur in real
# EXIF strings in the wild: the bare 19-char form, the same with a
# fractional-second suffix, and the same with an explicit timezone offset.
# We do NOT attempt to parse XMP/ IPTC-style "2023-04-01T12:00:00" here;
# that is a different metadata dialect and mixing the two has historically
# caused more bugs than it solved.

_BARE_FORMAT = "%Y:%m:%d %H:%M:%S"


def parse_exif_datetime(value: str) -> Optional[datetime]:
    """Parse an EXIF date-time string into a naive ``datetime``.

    Returns ``None`` when the string is empty or not in a form this
    library recognises. We return ``None`` rather than raising because
    EXIF values are routinely missing or malformed in real image files,
    and callers almost always want to skip the photo rather than abort
    the batch.

    Recognised shapes (all use ``:`` as the date separator, per the EXIF
    spec — NOT ``-``):

    * ``YYYY:MM:DD HH:MM:SS``
    * ``YYYY:MM:DD HH:MM:SS.fraction`` — fraction may be 1–6 digits,
      optionally preceded by a space or a ``.``. A bare trailing digit
      run is treated as microseconds.
    * ``YYYY:MM:DD HH:MM:SS+HH:MM`` or ``...Z`` — the offset is parsed
      but the returned ``datetime`` is naive; the offset is dropped on
      purpose, because EXIF timestamps are overwhelmingly local time
      and pretending otherwise has burned too many import pipelines.
      If you need offset-aware datetimes, convert after parsing.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None

    # Separate the timezone tail, if any. We only accept the two forms
    # that actually appear in EXIF: ``Z`` or ``±HH:MM``.
    tz_index = -1
    if s.endswith("Z"):
        tz_index = len(s) - 1
    elif "+" in s[19:]:
        tz_index = s.find("+", 19)
    elif "-" in s[19:]:
        tz_index = s.find("-", 19)

    tz_part = ""
    if tz_index >= 19:
        tz_part = s[tz_index:]
        s = s[:tz_index].strip()

    if tz_part and tz_part != "Z":
        # Validate offset shape strictly so we don't silently accept
        # nonsense like ``+1`` and then return a half-parsed datetime.
        if len(tz_part) < 6:
            return None
        sign = tz_part[0]
        if sign not in ("+", "-"):
            return None
        rest = tz_part[1:]
        if rest[2] != ":":
            return None
        if not (rest[:2].isdigit() and rest[3:].isdigit()):
            return None

    # Now split a subsecond suffix. EXIF spec doesn't define one, but
    # in practice subseconds live in a separate tag (SubSecTime) AND
    # occasionally get concatenated by some tools. We handle the
    # concatenated form defensively.
    subsec = ""
    # Look for a run of digits after the 19-char base. A leading "." is
    # the most common separator; a leading space shows up in Apple files.
    if len(s) > 19:
        tail = s[19:]
        if tail.startswith("."):
            subsec = tail[1:]
            s = s[:19]
        elif tail.startswith(" "):
            stripped = tail.strip()
            if stripped.isdigit():
                subsec = stripped
                s = s[:19]
        elif tail.isdigit():
            subsec = tail
            s = s[:19]

    if len(s) != 19:
        return None

    try:
        dt = datetime.strptime(s, _BARE_FORMAT)
    except ValueError:
        return None

    if subsec:
        # Microseconds must be exactly 6 digits for ``datetime``.
        # Left-pad OR right-truncate to 6. Right-truncation is correct
        # for a 7+ digit precision (we keep the most-significant digits);
        # left-padding is correct for ``.5`` meaning 500000us.
        if len(subsec) >= 6:
            micros = int(subsec[:6])
        else:
            micros = int(subsec.ljust(6, "0"))
        if micros < 0 or micros > 999999:
            return None
        dt = dt.replace(microsecond=micros)

    return dt


def normalize_exif_datetime(value: str) -> str:
    """Return the canonical EXIF form of a parsed date-time string.

    The output is always ``YYYY:MM:DD HH:MM:SS`` (19 chars) or, when
    the input carried subsecond precision,
    ``YYYY:MM:DD HH:MM:SS.ffffff`` (26 chars, dot-separated, 6 digits).
    Returns ``""`` for unparseable input.

    Normalisation is deliberately lossy on two axes: the timezone offset
    is dropped (see :func:`parse_exif_datetime` for the reasoning) and
    subsecond precision is quantised to whole microseconds. Both choices
    keep the output round-trippable through :func:`parse_exif_datetime`.
    """
    dt = parse_exif_datetime(value)
    if dt is None:
        return ""
    base = dt.strftime(_BARE_FORMAT)
    if dt.microsecond:
        return f"{base}.{dt.microsecond:06d}"
    return base
