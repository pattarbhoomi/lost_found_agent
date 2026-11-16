"""
generate_data.py  -  makes a synthetic test set WITH the right answers
=====================================================================
ELI5: To check the agent we need exam papers where WE know the answer key.
For every "true item" we write TWO reports in different words:
    * the owner's LOST report   ("Lost my navy Boat earphones, sticker on it")
    * the finder's FOUND report ("Found blue earbuds case near reading hall")
The pair_id is the answer key.  We also add extra reports with no partner
(distractors) - in real life most lost items are never reported found,
and the agent must NOT invent matches for them.

Realism tricks (so the test is not too easy):
  * the owner and finder use different words and drop details at random
  * ~15% of object names are words the agent does NOT know (e.g. 'earpods')
  * ~12% of places are unknown ('near the big tree')
  * 20% of reports give a nearby place instead of the exact one
Usage:  python generate_data.py --seed 2 --pairs 60 --distractors 25
"""
import argparse
import csv
import random
from datetime import datetime, timedelta

import config

# in-vocabulary names (agent knows them) and OUT-of-vocabulary names (it does not)
NAMES = {
    "earbuds":    (["earbuds case", "earphones", "airpods", "earbuds", "earphone box", "headphones", "neckband"], ["earpods", "tws set", "buds pouch"]),
    "wallet":     (["wallet", "purse", "card holder", "leather wallet"], ["money pouch"]),
    "phone":      (["phone", "mobile", "smartphone", "cellphone"], ["handy device"]),
    "id_card":    (["id card", "college card", "student card", "identity card"], ["campus pass"]),
    "keys":       (["keys", "bunch of keys", "key bunch"], ["lock openers"]),
    "bottle":     (["bottle", "water bottle", "flask", "sipper"], ["steel jug"]),
    "umbrella":   (["umbrella"], ["rain shield"]),
    "bag":        (["bag", "backpack", "sling bag", "laptop bag", "college bag"], ["haversack"]),
    "laptop":     (["laptop", "macbook"], ["portable computer"]),
    "charger":    (["charger", "phone charger", "laptop charger", "adapter", "usb cable"], ["power brick"]),
    "calculator": (["calculator", "calci"], ["scientific device"]),
    "watch":      (["watch", "wristwatch", "smartwatch"], ["timepiece"]),
    "spectacles": (["spectacles", "glasses", "specs", "sunglasses"], ["eye frames"]),
    "notebook":   (["notebook", "diary", "register", "textbook"], ["writing pad"]),
}
BRANDS = {
    "earbuds": ["boat", "sony", "jbl", "noise", "realme", "apple", "oneplus"],
    "wallet": ["fastrack", "titan", "wildcraft", "puma", "hidesign"],
    "phone": ["samsung", "apple", "redmi", "realme", "oneplus", "vivo", "oppo"],
    "bottle": ["milton", "cello", "nike"],
    "bag": ["skybags", "wildcraft", "safari", "nike", "adidas"],
    "laptop": ["dell", "hp", "lenovo", "asus"],
    "charger": ["apple", "samsung", "realme", "boat", "xiaomi"],
    "calculator": ["casio"],
    "watch": ["casio", "titan", "fastrack", "noise"],
    "notebook": ["classmate"],
}
COLORS = {"black": ["black", "jet black"], "white": ["white", "cream"], "blue": ["blue", "navy", "dark blue"],
          "red": ["red", "maroon"], "green": ["green", "olive"], "grey": ["grey", "gray"],
          "brown": ["brown", "tan"], "pink": ["pink"], "silver": ["silver"], "yellow": ["yellow"]}
MARKS = ["a small scratch", "a sticker on it", "a keychain attached", "a crack on one side",
         "a name written on it", "initials RK on it", "a rubber band around it",
         "a torn corner", "a dent", "a faded logo"]
# per mark, how each side tends to phrase it (shared keyword so TF-IDF can overlap, as in real life)
PLACES = list(config.LOCATIONS)
UNKNOWN_PLACES = ["near the big tree", "somewhere behind the stairs", "near the water cooler"]

LOST_T = ["Lost my {color} {brand} {name}.{mark}", "I lost a {name} ({color}).{mark} {brand}",
          "{name} missing, {color} {brand}.{mark}", "Lost {name}.{mark}", "Misplaced my {brand} {name}, {color}.{mark}"]
FOUND_T = ["Found a {color} {name} {brand}.{mark}", "{name} found, looks {color}.{mark} {brand}",
           "Found {name}.{mark}", "Picked up a {color} {brand} {name}.{mark}", "Someone left a {name}, {color}.{mark}"]


def _pick_name(rng, cat):
    ok, oov = NAMES[cat]
    return rng.choice(oov) if rng.random() < 0.15 else rng.choice(ok)


def _place(rng, true_place):
    r = rng.random()
    if r < 0.12:
        return rng.choice(UNKNOWN_PLACES)
    if r < 0.32:                                   # a different (maybe nearby) place
        return rng.choice([p for p in PLACES if p != true_place])
    return true_place


def _alias(rng, place):
    return rng.choice(config.LOCATIONS[place]["aliases"]) if place in config.LOCATIONS else place


def _write_report(rng, templates, cat, color, brand, mark, name_pref=None):
    c = rng.choice(COLORS[color]) if (color and rng.random() < 0.75) else ""
    b = brand if (brand and rng.random() < 0.55) else ""
    m = f" It has {mark}." if (mark and rng.random() < 0.5) else ""
    text = rng.choice(templates).format(color=c, brand=b, name=_pick_name(rng, cat), mark=m)
    return " ".join(text.split())


def generate(seed, pairs, distractors, outfile):
    rng = random.Random(seed)
    base = datetime(2026, 11, 1, 9, 0)
    rows = []
    n = 0

    def new_item():
        cat = rng.choice(list(NAMES))
        color = rng.choice(list(COLORS))
        brand = rng.choice(BRANDS[cat]) if cat in BRANDS and rng.random() < 0.8 else None
        mark = rng.choice(MARKS) if rng.random() < 0.7 else None
        place = rng.choice(PLACES)
        when = base + timedelta(hours=rng.uniform(0, 14 * 24))
        return cat, color, brand, mark, place, when

    for pid in range(1, pairs + 1):
        cat, color, brand, mark, place, when = new_item()
        lost_when = when - timedelta(hours=rng.uniform(0, 4))
        found_when = when + timedelta(hours=rng.uniform(0, 30 if rng.random() < 0.8 else 72))
        for kind, templates, t in (("lost", LOST_T, lost_when), ("found", FOUND_T, found_when)):
            n += 1
            rows.append({"id": n, "kind": kind, "pair_id": pid,
                         "true_color": color, "true_brand": brand or "", "true_place": place, "true_mark": mark or "",
                         "description": _write_report(rng, templates, cat, color, brand, mark),
                         "location": _alias(rng, _place(rng, place)),
                         "time": t.strftime("%Y-%m-%d %H:%M"), "contact": f"user{n}@college.edu"})
    for d in range(distractors * 2):               # unmatched reports (half lost, half found)
        cat, color, brand, mark, place, when = new_item()
        kind, templates = ("lost", LOST_T) if d % 2 == 0 else ("found", FOUND_T)
        n += 1
        rows.append({"id": n, "kind": kind, "pair_id": "",
                     "true_color": color, "true_brand": brand or "", "true_place": place, "true_mark": mark or "",
                     "description": _write_report(rng, templates, cat, color, brand, mark),
                     "location": _alias(rng, _place(rng, place)),
                     "time": when.strftime("%Y-%m-%d %H:%M"), "contact": f"user{n}@college.edu"})
    rng.shuffle(rows)
    with open(outfile, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "kind", "pair_id", "true_color", "true_brand", "true_place", "true_mark", "description", "location", "time", "contact"])
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--pairs", type=int, default=60)
    ap.add_argument("--distractors", type=int, default=25)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or f"data/test_set_seed{a.seed}.csv"
    rows = generate(a.seed, a.pairs, a.distractors, out)
    print(f"wrote {len(rows)} reports to {out}")
    for r in rows[:6]:
        print("  ", r["kind"], "|", r["description"], "|", r["location"], "|", r["time"])
