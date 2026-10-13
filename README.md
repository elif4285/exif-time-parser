# Exif Time Parser

Parses and normalises EXIF date-time strings (the `DateTime`, `DateTimeOriginal`, and `DateTimeDigitized` tags) from image metadata. Standard library only, no third-party dependencies.

```python
from exif_time_parser import parse_exif_datetime, normalize_exif_datetime

dt = parse_exif_datetime("2023:04:01 12:30:45.500")
# -> datetime(2023, 4, 1, 12, 30, 45, 500000)

canonical = normalize_exif_datetime("2023:04:01 12:30:45+05:30")
# -> "2023:04:01 12:30:45"
```

## Why this exists

EXIF stores timestamps as `YYYY:MM:DD HH:MM:SS` — colons in the date, a space before the time, no separator before subseconds. Real files also carry subsecond suffixes (`.5`, ` 500`, or a bare trailing digit run) and, less often, a `Z` or `±HH:MM` offset glued onto the end. Most general-purpose date parsers refuse the colon-separated date, and most EXIF readers hand you the raw string and leave you to fend for yourself.

This library accepts the three shapes that actually occur in EXIF and returns a plain `datetime`. It deliberately returns `None` for unparseable input rather than raising, because in batch image pipelines a bad timestamp on one file should not abort the whole run.

## The awkward edge

Timezone offsets in EXIF are interpreted and then **dropped**: the returned `datetime` is always naive. EXIF timestamps are overwhelmingly meant as local camera time, and silently attaching an offset has historically caused more downstream bugs than it solved. If you genuinely need offset-aware datetimes, convert after parsing — but first read the EXIF spec's non-commitment on the matter.

Subsecond precision is quantised to whole microseconds (the resolution of Python's `datetime`). A 7-digit fraction is truncated, not rounded; `.5` is padded to `.500000`. The normalised output round-trips through `parse_exif_datetime`.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

