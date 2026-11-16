# Campus Lost & Found Agent
A semi-autonomous, goal-based + utility-based AI agent that matches lost items with found items.
Mini project: *Implementation of an AI Agent*.

**Tech:** Python 3.9+, scikit-learn (TF-IDF), SQLite (built into Python). No GPU, no internet, no API keys.

## Quick start
```bash
pip install -r requirements.txt
python demo.py              # 1-minute scripted tour of every behaviour  (use this in the viva)
python main.py              # interactive agent (type reports, answer its questions)
python -m unittest -v       # 13 automatic self-checks
python evaluate.py          # accuracy on 5 unseen synthetic test sets -> results/evaluation_results.txt
```

## What makes it an AGENT (not just a search box)?
| Agent property | Where it happens |
|---|---|
| **Perceives** its environment | `perception.py` reads messy text, place and time and builds a tidy "Report" |
| **Remembers** | `database.py` keeps every report, suggestion, question, rejection |
| **Decides** on its own | `agent.py -> decide()` picks NOTIFY / ASK / WAIT from the match score |
| **Acts** on the world | notifies both people, asks follow-up questions, re-checks when new reports arrive |
| **Has a goal + a utility** | goal = reunite owner and item; utility = the 0..1 match score |
| **Semi-autonomous** | a human (security desk) confirms / rejects the final hand-over |

## The loop (Perceive -> Think -> Decide -> Act)
```
 new report
     |
 1 PERCEIVE   perception.parse_report()   text -> category, colour, brand, place, time
     |
 2 THINK      matcher.rank_candidates()   score vs every open report of the opposite kind
     |
 3 DECIDE     agent.decide()              score >= 0.75 and clearly ahead of #2 -> NOTIFY
     |                                    score >= 0.45 (or too close to call)   -> ASK
     |                                    otherwise                              -> WAIT
 4 ACT        notify both / ask one question / save and keep watching
```

## File-by-file (ELI5)
| File | Analogy | What it does |
|---|---|---|
| `config.py` | the clerk's notebook | synonyms ("earphones = earbuds"), campus map, clue weights, thresholds |
| `perception.py` | the clerk's eyes and ears | turns a sentence into a tidy form (Report) |
| `matcher.py` | the clerk's judgement | compares two reports clue by clue and returns one score 0-1 |
| `database.py` | the clerk's memory | SQLite tables: items, matches, questions, notifications |
| `agent.py` | the clerk | the Perceive->Think->Decide->Act loop + confirm / reject |
| `main.py` | the front desk | command-line menu |
| `demo.py` | a rehearsed performance | scripted scenario showing every behaviour |
| `generate_data.py` | exam-paper writer | synthetic reports WITH an answer key |
| `evaluate.py` | the examiner | measures accuracy, compares with baselines |
| `test_agent.py` | safety net | 13 automatic checks |

## How the score is computed (worked example from `demo.py`)
Asha lost *"black Boat earbuds case, has a sticker"* (library, 2 PM). Ravi found *"black earphone box with a sticker"* (reading hall, 3:30 PM).

| Clue | Mark (0-1) | Weight | Contribution |
|---|---|---|---|
| Description similarity (TF-IDF) | 0.51 | 0.25 | 0.128 |
| Same category (earbuds = earbuds) | 1.00 | 0.15 | 0.150 |
| Same colour (black) | 1.00 | 0.20 | 0.200 |
| Brand (found report doesn't say) | 0.50 *unknown* | 0.05 | 0.025 |
| Location (reading hall = library) | 1.00 | 0.15 | 0.150 |
| Time (1.5 h apart) | 0.97 | 0.20 | 0.194 |
| **Total** | | | **0.85 -> above 0.75 -> NOTIFY** |

*Unknown* clues score 0.5 ("no idea") instead of 0, so a missing detail does not kill a good match.
Two common-sense rules: **(1)** different categories multiply the score by 0.4; **(2)** an item cannot be found more than 3 hours *before* it was lost (time mark = 0).

## Dry run of the ASK loop (Karan's vague wallet)
1. Found: *"brown leather wallet"* at the canteen is waiting.
2. Karan reports *"Lost my wallet"*, canteen. Colour is unknown -> score **0.73** (< 0.75) -> **ASK**: *"What colour was the item?"*
3. Karan answers *"it was brown"*. `apply_answer()` fills the empty colour box and extends the description.
4. The agent re-thinks: colour now matches, text similarity rises -> score **0.90** -> **NOTIFY**.
5. The agent never reveals the finder's description in its question (prevents people guessing their way to someone else's property).

## Results (held-out synthetic test sets, 5 x [60 true pairs + 50 unmatched reports])
| Method | Top-1 | Top-3 | MRR |
|---|---|---|---|
| Baseline A: plain TF-IDF | 0.25 | 0.40 | 0.37 |
| Baseline B: TF-IDF + synonyms | 0.37 | 0.59 | 0.51 |
| **Full agent (multi-clue score)** | **0.71** | **0.89** | **0.80** |

Policy results: NOTIFY precision **0.91**; false-alarm rate on unmatched reports **3%**.
With the clarifying-question loop (simulated owner): **38%** of true pairs are resolved automatically (**22%** without questions), only **2%** go to the wrong item, and the rest go to the security desk with a ranked shortlist (right item in the top-3 for 89% of cases).
Full numbers: `results/evaluation_results.txt`.

## Honest limitations
* Test data is **synthetic** (generated by `generate_data.py`), so real-world numbers will differ. ~15% of object names and ~12% of places are deliberately unknown to the agent to make the test fairer.
* The agent is deliberately **cautious**: it prefers asking or escalating to a human over a wrong hand-over.
* Text only. No photo matching; notifications are written to a log table instead of real e-mail/SMS.
* Thresholds and weights were tuned on one dev set (seed 1) and reported on five *other* sets (seeds 2-6).

## Possible extensions
Photo matching with a pre-trained image model, sentence embeddings (`sentence-transformers`) instead of TF-IDF, a Streamlit/web UI, real e-mail/SMS, a learned (logistic-regression) scorer trained on confirmed matches.
