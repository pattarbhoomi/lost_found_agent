"""
matcher.py  -  the agent's THINKING part (utility scoring)
==========================================================
ELI5: Suppose someone says "I lost a black wallet" and you find a black
wallet on the floor.  How sure are you it is theirs?  You do not answer
yes/no - you collect clues and give each a mark between 0 and 1:
     same kind of object?  colour same?  same brand?  nearby place?
     found AFTER it was lost?  descriptions sound alike?
Then you mix the marks using weights (config.WEIGHTS) into ONE number
called the match score (0 = no way, 1 = surely).  A utility-based agent
is exactly this: "turn every option into a number, pick the best".
"""
import math
from typing import List, Tuple

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

import config
from perception import Report

# words that appear in EVERY report and carry no information
_EXTRA_STOP = {"lost", "found", "missing", "please", "help", "left", "someone",
               "near", "around", "kindly", "forgot", "picked", "got", "had", "ha",
               "pls", "contact", "yesterday", "today", "morning", "evening"}
STOP_WORDS = list(ENGLISH_STOP_WORDS | _EXTRA_STOP)


# ---------------------------------------------------------------------
# Individual clue scorers  (each returns a number 0..1)
# ---------------------------------------------------------------------
def _same_or_unknown(a, b) -> float:
    """1 if both known and equal, 0 if both known and different,
    0.5 ('no idea') if either side is missing."""
    if a is None or b is None:
        return config.UNKNOWN_SCORE
    return 1.0 if a == b else 0.0


def location_score(a, b) -> float:
    if a is None or b is None:
        return config.UNKNOWN_SCORE
    (x1, y1) = config.LOCATIONS[a]["xy"]
    (x2, y2) = config.LOCATIONS[b]["xy"]
    dist = math.hypot(x1 - x2, y1 - y2)
    return max(0.0, 1.0 - dist / config.LOCATION_RANGE_M)


def time_score(lost: Report, found: Report) -> float:
    hours = (found.when - lost.when).total_seconds() / 3600.0
    if hours < -config.FOUND_BEFORE_LOST_TOLERANCE_H:   # found BEFORE it was lost?!
        return 0.0
    return math.exp(-abs(hours) / config.TIME_HALF_LIFE_H)


# ---------------------------------------------------------------------
# One pair of reports -> one final score
# ---------------------------------------------------------------------
def score_pair(lost: Report, found: Report, text_sim: float) -> Tuple[float, dict]:
    parts = {
        "text":     float(text_sim),
        "category": _same_or_unknown(lost.category, found.category),
        "color":    _same_or_unknown(lost.color, found.color),
        "brand":    _same_or_unknown(lost.brand, found.brand),
        "location": location_score(lost.location, found.location),
        "time":     time_score(lost, found),
    }
    score = sum(config.WEIGHTS[k] * v for k, v in parts.items())
    # common-sense rule: two clearly different kinds of object are not a match
    if parts["category"] == 0.0:
        score *= config.CATEGORY_MISMATCH_PENALTY
    return score, parts


# ---------------------------------------------------------------------
# One query report versus a whole pool of candidates
# ---------------------------------------------------------------------
def text_similarities(query_text: str, pool_texts: List[str]) -> List[float]:
    """TF-IDF + cosine similarity.
    ELI5: TF-IDF gives every word a 'rarity weight' (the word 'sticker' is
    more telling than 'the').  Each description becomes a list of weights;
    cosine similarity measures how much two lists point the same way."""
    if not pool_texts:
        return []
    try:
        vec = TfidfVectorizer(stop_words=STOP_WORDS, sublinear_tf=True)
        X = vec.fit_transform([query_text] + pool_texts)
        sims = (X[1:] @ X[0].T).toarray().ravel()
        return [float(s) for s in sims]
    except ValueError:               # empty vocabulary (e.g. only stop-words)
        return [0.0] * len(pool_texts)


def rank_candidates(query: Report, pool: List[Report]):
    """Score `query` against every report in `pool`.
    Returns [(candidate, score, breakdown)] sorted best-first."""
    sims = text_similarities(query.clean_text, [c.clean_text for c in pool])
    ranked = []
    for cand, sim in zip(pool, sims):
        lost, found = (query, cand) if query.kind == "lost" else (cand, query)
        score, parts = score_pair(lost, found, sim)
        ranked.append((cand, score, parts))
    ranked.sort(key=lambda t: t[1], reverse=True)
    return ranked
