"""
perception.py  -  the agent's SENSORS  (the "S" in PEAS)
========================================================
ELI5: A person types a messy sentence like
        "lost my navy BOAT earphone box near reading hall around 2pm"
A computer can't "feel" that sentence, so the sensor turns it into a tidy
form with boxes to fill:
        category = earbuds | colour = blue | brand = boat
        place = library    | time   = today 14:00
That tidy form is called a Report.  Everything later in the project
(matching, deciding, acting) works on Reports, never on raw sentences.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import config


# ---------------------------------------------------------------------
# The tidy form (one Report = one lost or found item)
# ---------------------------------------------------------------------
@dataclass
class Report:
    kind: str                       # "lost" or "found"
    description: str                # what the person typed
    clean_text: str                 # normalised text used for TF-IDF
    category: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    location: Optional[str] = None  # canonical campus place, or None
    location_text: str = ""         # raw text typed by the user
    when: datetime = field(default_factory=datetime.now)
    contact: str = ""
    status: str = "open"            # open / pending / closed
    id: Optional[int] = None


# ---------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------
def _normalize(text: str) -> str:
    """lowercase, drop punctuation, squeeze spaces."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _spans(text: str, vocab: dict):
    """Find every vocabulary word in `text`.
    Returns a list of (start, end, canonical_name)."""
    found = []
    for canon, words in vocab.items():
        for w in words:
            for m in re.finditer(rf"\b{re.escape(w)}\b", text):
                found.append((m.start(), m.end(), canon))
    return found


def _first_mention(text: str, vocab: dict) -> Optional[str]:
    """Which vocabulary entry is mentioned FIRST?  Longer phrases win ties
    (so 'laptop bag' is read as a bag, not a laptop)."""
    spans = _spans(text, vocab)
    spans.sort(key=lambda s: -(s[1] - s[0]))          # longest first
    accepted = []
    for s in spans:                                    # drop spans inside longer ones
        if all(s[1] <= a[0] or s[0] >= a[1] for a in accepted):
            accepted.append(s)
    if not accepted:
        return None
    return min(accepted, key=lambda s: s[0])[2]        # earliest mention


def _stem(token: str) -> str:
    """Very light stemming: 'stickers' -> 'sticker'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _canonical_text(text: str) -> str:
    """Rewrite synonyms to ONE word so TF-IDF can see they are the same thing.
    'earphone box' and 'airpods case' both contain 'earbuds' afterwards."""
    replacements = []
    for vocab in (config.CATEGORIES, config.COLORS):
        for canon, words in vocab.items():
            for w in words:
                replacements.append((w, canon.replace("_", "")))
    replacements.sort(key=lambda r: -len(r[0]))        # longest phrase first
    # one pass with a combined regex avoids replacing inside replacements
    pattern = r"\b(" + "|".join(re.escape(w) for w, _ in replacements) + r")\b"
    lookup = dict(replacements)
    text = re.sub(pattern, lambda m: lookup[m.group(1)], text)
    return " ".join(_stem(t) for t in text.split())


# ---------------------------------------------------------------------
# Place and time
# ---------------------------------------------------------------------
_LOC_VOCAB = {k: v["aliases"] for k, v in config.LOCATIONS.items()}


def resolve_location(text: str) -> Optional[str]:
    return _first_mention(_normalize(text), _LOC_VOCAB) if text else None


def parse_time(text: str, now: Optional[datetime] = None) -> datetime:
    """Understands '2026-11-16 14:30', '2026-11-16', '2pm', '14:30', '' (=now)."""
    now = now or datetime.now()
    text = (text or "").strip().lower()
    if not text or text == "now":
        return now
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if m:
        hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        if hour < 24 and minute < 60:
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return now


# ---------------------------------------------------------------------
# The main sensor function
# ---------------------------------------------------------------------
def extract_attributes(text: str) -> dict:
    """Pull category / colour / brand out of free text."""
    norm = _normalize(text)
    brand = _first_mention(norm, {b: [b] for b in config.BRANDS})
    return {
        "category": _first_mention(norm, config.CATEGORIES),
        "color": _first_mention(norm, config.COLORS),
        "brand": brand,
    }


def parse_report(kind: str, description: str, location_text: str = "",
                 time_text: str = "", contact: str = "",
                 now: Optional[datetime] = None) -> Report:
    """Turn what the person typed into a tidy Report."""
    norm = _normalize(description)
    attrs = extract_attributes(description)
    location = resolve_location(location_text) or resolve_location(description)
    return Report(
        kind=kind,
        description=description.strip(),
        clean_text=_canonical_text(norm),
        category=attrs["category"],
        color=attrs["color"],
        brand=attrs["brand"],
        location=location,
        location_text=location_text.strip(),
        when=parse_time(time_text, now),
        contact=contact.strip(),
    )


def apply_answer(report: Report, answer: str) -> Report:
    """The user answered a clarifying question: fill any EMPTY boxes in the
    tidy form and add the answer to the description.  (Used by the agent AND
    by the evaluation's simulated user, so both behave identically.)"""
    extra = extract_attributes(answer)
    for attr in ("category", "color", "brand"):
        if getattr(report, attr) is None and extra[attr]:
            setattr(report, attr, extra[attr])
    loc = resolve_location(answer)
    if report.location is None and loc:
        report.location, report.location_text = loc, answer
    report.description += f" ({answer})"
    report.clean_text = _canonical_text(_normalize(report.description))
    return report
