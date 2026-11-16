"""
config.py  -  the agent's "knowledge book" and tuning knobs
===========================================================
ELI5: Imagine a new helper joining the campus security desk.  Before
they can help, you hand them a small notebook that says:
   * "earphones", "airpods" and "earbuds" all mean the same thing
   * "reading hall" is just another name for the library
   * the library is close to the canteen but far from the main gate
   * how much each clue (colour, place, time ...) matters
This file IS that notebook.  Nothing here is "code logic" - it is
only data, so you can tune the agent without touching its brain.
"""

# ---------------------------------------------------------------------
# 1. Categories.  The agent picks the category whose word appears FIRST in the
#    sentence; longer phrases such as "laptop bag" beat shorter ones ("laptop"),
#    so a laptop bag becomes `bag` and not `laptop`.
# ---------------------------------------------------------------------
CATEGORIES = {
    "charger":    ["charger", "phone charger", "laptop charger", "mobile charger", "adapter",
                   "adaptor", "charging cable", "usb cable", "type c cable"],
    "powerbank":  ["power bank", "powerbank"],
    "earbuds":    ["earbuds", "earbud", "earphones", "earphone", "airpods", "airpod",
                   "headphones", "headphone", "neckband", "earpiece", "buds"],
    "id_card":    ["id card", "idcard", "identity card", "college card",
                   "student card", "icard", "id"],
    "wallet":     ["wallet", "purse", "billfold", "card holder", "cardholder"],
    "keys":       ["keys", "key", "key bunch", "bunch of keys"],
    "bag":        ["bag", "backpack", "rucksack", "sling bag", "satchel", "laptop bag",
                   "college bag", "school bag", "gym bag"],
    "laptop":     ["laptop", "notebook computer", "macbook"],
    "phone":      ["phone", "mobile", "smartphone", "cellphone", "iphone", "handset"],
    "bottle":     ["bottle", "flask", "water bottle", "sipper", "tumbler"],
    "umbrella":   ["umbrella", "brolly"],
    "calculator": ["calculator", "calci"],
    "watch":      ["watch", "wristwatch", "smartwatch"],
    "spectacles": ["spectacles", "glasses", "specs", "eyeglasses", "sunglasses"],
    "notebook":   ["notebook", "copy", "diary", "register", "textbook", "book"],
}

# ---------------------------------------------------------------------
# 2. Colours (canonical name -> words people use)
# ---------------------------------------------------------------------
COLORS = {
    "black":  ["black", "jet black", "charcoal"],
    "white":  ["white", "cream", "off white"],
    "blue":   ["blue", "navy", "navy blue", "dark blue", "sky blue", "light blue"],
    "red":    ["red", "maroon", "crimson"],
    "green":  ["green", "olive", "dark green"],
    "yellow": ["yellow", "mustard"],
    "grey":   ["grey", "gray", "ash"],
    "brown":  ["brown", "tan", "coffee"],
    "pink":   ["pink", "rose"],
    "orange": ["orange"],
    "purple": ["purple", "violet"],
    "silver": ["silver", "metallic"],
    "gold":   ["gold", "golden"],
}

# ---------------------------------------------------------------------
# 3. Brands the agent recognises
# ---------------------------------------------------------------------
BRANDS = ["boat", "sony", "jbl", "noise", "realme", "apple", "oneplus", "samsung",
          "redmi", "xiaomi", "vivo", "oppo", "dell", "hp", "lenovo", "asus", "casio",
          "titan", "fastrack", "milton", "cello", "nike", "adidas", "puma", "skybags",
          "wildcraft", "safari", "hidesign", "parker", "classmate"]

# ---------------------------------------------------------------------
# 4. A tiny map of the campus.  (x, y) in metres on an imaginary grid.
#    Closer places -> higher location score.
# ---------------------------------------------------------------------
LOCATIONS = {
    "library":      {"xy": (200, 300), "aliases": ["library", "lib", "reading hall", "reading room"]},
    "canteen":      {"xy": (260, 220), "aliases": ["canteen", "cafeteria", "mess", "food court"]},
    "main_gate":    {"xy": (20, 20),   "aliases": ["main gate", "gate", "entrance", "security gate"]},
    "cs_block":     {"xy": (330, 330), "aliases": ["cs block", "computer block", "it block", "cs department", "lab block"]},
    "mech_block":   {"xy": (420, 150), "aliases": ["mech block", "mechanical block", "workshop"]},
    "ground":       {"xy": (150, 120), "aliases": ["ground", "playground", "sports ground", "cricket ground", "football ground"]},
    "hostel":       {"xy": (500, 420), "aliases": ["hostel", "boys hostel", "girls hostel", "hostel gate"]},
    "auditorium":   {"xy": (300, 400), "aliases": ["auditorium", "seminar hall", "main hall"]},
    "parking":      {"xy": (60, 80),   "aliases": ["parking", "parking lot", "bike stand", "cycle stand"]},
    "admin_office": {"xy": (120, 220), "aliases": ["admin office", "administration", "office", "principal office"]},
    "bus_stop":     {"xy": (10, 60),   "aliases": ["bus stop", "bus stand", "bus bay"]},
}
LOCATION_RANGE_M = 500   # places this far apart (or more) score 0

# ---------------------------------------------------------------------
# 5. How much each clue matters (must add up to 1.0)
# ---------------------------------------------------------------------
WEIGHTS = {
    "text":     0.25,   # how similar the two descriptions sound
    "category": 0.15,   # same kind of object?
    "color":    0.20,
    "brand":    0.05,   # brand is often unknown, so it counts for little
    "location": 0.15,
    "time":     0.20,   # lost things are usually found within hours/days
}
UNKNOWN_SCORE = 0.5            # clue missing on one side -> "no idea", not "no match"
CATEGORY_MISMATCH_PENALTY = 0.4  # wallet vs bottle?  multiply the final score by this
TIME_HALF_LIFE_H = 48          # time clue fades with this scale
FOUND_BEFORE_LOST_TOLERANCE_H = 3  # an item can't be found before it was lost

# ---------------------------------------------------------------------
# 6. The decision thresholds - the heart of the agent's policy
# ---------------------------------------------------------------------
NOTIFY_THRESHOLD = 0.75   # >= : strong match -> tell both people
ASK_THRESHOLD    = 0.45   # >= : maybe -> ask a clarifying question
                          # <  : not similar -> store and keep waiting
NOTIFY_MARGIN    = 0.15   # best must beat the runner-up by this much to be trusted
                          # (two near-identical candidates = ambiguous -> ask instead)
