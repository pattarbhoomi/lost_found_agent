"""
evaluate.py  -  the agent's EXAM (Performance measure, the "P" in PEAS)
======================================================================
ELI5: We hand the agent a pile of lost reports and a pile of found reports
that we already know the answers to, and mark it like a teacher:
   Top-1 accuracy : was the right item its very first suggestion?
   Top-3 accuracy : was the right item among its first three?
   MRR            : average of 1/rank (1.0 = always first)
   Decisions      : did it NOTIFY when it should, and stay quiet when
                    there was no true partner? (precision / false alarms)
We also run two simpler "baseline" matchers so you can show the examiner
that the full agent really is better than plain keyword search.

Usage:  python evaluate.py                      (seeds 2-6, default thresholds)
        python evaluate.py --seeds 1 --notify 0.7 --ask 0.45
"""
import argparse
import copy
import csv
import os
import random
import statistics

import config
import generate_data
import matcher
import perception
from agent import ASK, NOTIFY, WAIT, choose_question, decide


def load(csv_path):
    reports, truth, rows = [], {}, {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            rows[int(row["id"])] = row
            rep = perception.parse_report(row["kind"], row["description"], row["location"],
                                          row["time"], row["contact"])
            rep.id = int(row["id"])
            reports.append(rep)
            truth[rep.id] = row["pair_id"]
    return reports, truth, rows


def simulate_answer(row, attribute, rng):
    """A pretend owner who answers the agent's question from the answer key
    (sometimes forgetting, like a real person)."""
    if attribute == "color":
        return f"it was {rng.choice(generate_data.COLORS[row['true_color']])}" if rng.random() < 0.9 else "not sure"
    if attribute == "brand":
        return row["true_brand"] if row["true_brand"] and rng.random() < 0.7 else "don't remember"
    if attribute == "location":
        return f"near the {generate_data._alias(rng, row['true_place'])}" if rng.random() < 0.9 else "not sure"
    return f"it has {row['true_mark']}" if row["true_mark"] and rng.random() < 0.8 else "nothing special"


def run_dialogue(report, row, founds, rng):
    """Let the agent talk to the simulated owner until it notifies or runs out of questions."""
    rep, asked, rounds = copy.deepcopy(report), set(), 0
    while True:
        ranked = matcher.rank_candidates(rep, founds)
        best = ranked[0]
        action = decide(best[1], ranked[1][1] if len(ranked) > 1 else None)
        if action == NOTIFY:
            return NOTIFY, best[0].id, rounds
        if action == WAIT:
            return WAIT, None, rounds
        attr, question = choose_question(rep, best[0], best[2], asked)
        if question is None:                      # nothing left to ask -> human review
            return "REVIEW", None, rounds
        asked.add(attr)
        perception.apply_answer(rep, simulate_answer(row, attr, rng))
        rounds += 1


def evaluate(csv_path, notify_t=None, ask_t=None, margin=None):
    if margin is not None:
        config.NOTIFY_MARGIN = margin
    if notify_t is not None:
        config.NOTIFY_THRESHOLD = notify_t
    if ask_t is not None:
        config.ASK_THRESHOLD = ask_t
    reports, truth, rows = load(csv_path)
    rng = random.Random(7)
    inter = {"correct": 0, "wrong": 0, "unresolved": 0, "false_alarm": 0, "dist_ok": 0, "questions": 0}
    losts = [r for r in reports if r.kind == "lost"]
    founds = [r for r in reports if r.kind == "found"]
    found_by_pair = {truth[f.id]: f for f in founds if truth[f.id]}

    ranks = {"agent": [], "tfidf_raw": [], "tfidf_clean": []}
    dec = {"correct_notify": 0, "wrong_notify": 0, "pair_ask": 0, "pair_wait": 0,
           "distractor_notify": 0, "distractor_ask": 0, "distractor_wait": 0}
    n_pairs = n_dist = 0

    for L in losts:
        pid = truth[L.id]
        # --- full agent ranking
        ranked = matcher.rank_candidates(L, founds)
        best_cand, best_score, _ = ranked[0]
        # --- baselines (text similarity only)
        raw = matcher.text_similarities(perception._normalize(L.description),
                                        [perception._normalize(f.description) for f in founds])
        clean = matcher.text_similarities(L.clean_text, [f.clean_text for f in founds])
        if pid:
            n_pairs += 1
            target = found_by_pair[pid]
            ranks["agent"].append([c.id for c, _, _ in ranked].index(target.id) + 1)
            for name, sims in (("tfidf_raw", raw), ("tfidf_clean", clean)):
                order = sorted(range(len(founds)), key=lambda i: sims[i], reverse=True)
                ranks[name].append([founds[i].id for i in order].index(target.id) + 1)
        # --- interactive run: the agent may ask questions
        outcome, chosen, rounds = run_dialogue(L, rows[L.id], founds, rng)
        inter["questions"] += rounds
        if pid:
            if outcome == NOTIFY:
                inter["correct" if chosen == found_by_pair[pid].id else "wrong"] += 1
            else:
                inter["unresolved"] += 1
        else:
            inter["false_alarm" if outcome == NOTIFY else "dist_ok"] += 1

        action = decide(best_score, ranked[1][1] if len(ranked) > 1 else None)
        if pid:
            if action == NOTIFY:
                dec["correct_notify" if best_cand.id == found_by_pair[pid].id else "wrong_notify"] += 1
            else:
                dec["pair_ask" if action == ASK else "pair_wait"] += 1
        else:
            n_dist += 1
            dec[{NOTIFY: "distractor_notify", ASK: "distractor_ask", WAIT: "distractor_wait"}[action]] += 1

    def summarize(rs):
        return {"top1": sum(r == 1 for r in rs) / len(rs), "top3": sum(r <= 3 for r in rs) / len(rs),
                "mrr": sum(1 / r for r in rs) / len(rs)}

    notified = dec["correct_notify"] + dec["wrong_notify"] + dec["distractor_notify"]
    out = {name: summarize(rs) for name, rs in ranks.items()}
    out["decisions"] = dec
    out["n_pairs"], out["n_distractors"] = n_pairs, n_dist
    out["notify_precision"] = dec["correct_notify"] / notified if notified else float("nan")
    out["auto_resolved"] = dec["correct_notify"] / n_pairs
    out["false_alarm_rate"] = dec["distractor_notify"] / n_dist
    inter["n_pairs"], inter["n_dist"] = n_pairs, n_dist
    inter["avg_questions"] = inter["questions"] / (n_pairs + n_dist)
    out["interactive"] = inter
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="2,3,4,5,6")
    ap.add_argument("--pairs", type=int, default=60)
    ap.add_argument("--distractors", type=int, default=25)
    ap.add_argument("--notify", type=float, default=None)
    ap.add_argument("--ask", type=float, default=None)
    ap.add_argument("--margin", type=float, default=None)
    a = ap.parse_args()
    if a.margin is not None:
        config.NOTIFY_MARGIN = a.margin

    os.makedirs("data", exist_ok=True)
    results = []
    print(f"Thresholds: NOTIFY >= {a.notify or config.NOTIFY_THRESHOLD} (margin >= {config.NOTIFY_MARGIN}), ASK >= {a.ask or config.ASK_THRESHOLD}")
    print(f"Each test set: {a.pairs} true pairs + {a.distractors * 2} unmatched reports\n")
    for s in [int(x) for x in a.seeds.split(",")]:
        path = f"data/test_set_seed{s}.csv"
        if not os.path.exists(path):
            generate_data.generate(s, a.pairs, a.distractors, path)
        res = evaluate(path, a.notify, a.ask, a.margin)
        results.append(res)
        print(f"seed {s}: agent top1={res['agent']['top1']:.2f} top3={res['agent']['top3']:.2f} "
              f"| notify precision={res['notify_precision']:.2f} "
              f"auto-resolved={res['auto_resolved']:.2f} false-alarms={res['false_alarm_rate']:.2f}")

    def avg(getter):
        vals = [getter(r) for r in results]
        return statistics.mean(vals), (statistics.pstdev(vals) if len(vals) > 1 else 0.0)

    print("\n" + "=" * 66)
    print(f"AVERAGE OVER {len(results)} TEST SETS (mean +- std)")
    print("=" * 66)
    print(f"{'Method':<34}{'Top-1':>10}{'Top-3':>10}{'MRR':>10}")
    for key, label in (("tfidf_raw", "Baseline A: plain TF-IDF"),
                       ("tfidf_clean", "Baseline B: TF-IDF + synonyms"),
                       ("agent", "Full agent (multi-clue score)")):
        t1, t3, mr = (avg(lambda r, k=key, m=m: r[k][m])[0] for m in ("top1", "top3", "mrr"))
        print(f"{label:<34}{t1:>10.2f}{t3:>10.2f}{mr:>10.2f}")
    print("\nAgent DECISIONS (total counts over all test sets)")
    keys = ["correct_notify", "wrong_notify", "pair_ask", "pair_wait",
            "distractor_notify", "distractor_ask", "distractor_wait"]
    labels = {"correct_notify": "True pair -> NOTIFY, right item", "wrong_notify": "True pair -> NOTIFY, WRONG item",
              "pair_ask": "True pair -> ASK a question", "pair_wait": "True pair -> WAIT (missed)",
              "distractor_notify": "No partner exists -> NOTIFY (false alarm)",
              "distractor_ask": "No partner exists -> ASK", "distractor_wait": "No partner exists -> WAIT (correct)"}
    for k in keys:
        print(f"  {labels[k]:<44}{sum(r['decisions'][k] for r in results):>5}")
    m, s = avg(lambda r: r["notify_precision"])
    print(f"\nNOTIFY precision (right item when it notifies): {m:.2f} +- {s:.2f}")
    m, s = avg(lambda r: r["auto_resolved"])
    print(f"Auto-resolved (true pairs notified correctly)   : {m:.2f} +- {s:.2f}")
    m, s = avg(lambda r: r["false_alarm_rate"])
    print(f"False-alarm rate (unmatched reports notified)   : {m:.2f} +- {s:.2f}")

    print("\n" + "=" * 66)
    print("INTERACTIVE TEST: agent may ask up to 4 questions, simulated owner answers")
    print("=" * 66)
    tot = {k: sum(r["interactive"][k] for r in results) for k in ("correct", "wrong", "unresolved", "false_alarm", "dist_ok", "questions")}
    P = sum(r["interactive"]["n_pairs"] for r in results)
    D = sum(r["interactive"]["n_dist"] for r in results)
    print(f"True pairs ({P}):")
    print(f"  returned to the RIGHT owner (auto)   : {tot['correct']:>4}  ({tot['correct'] / P:.0%})")
    print(f"  notified the WRONG item              : {tot['wrong']:>4}  ({tot['wrong'] / P:.0%})")
    print(f"  still unresolved -> human review     : {tot['unresolved']:>4}  ({tot['unresolved'] / P:.0%})")
    print(f"Unmatched reports ({D}):")
    print(f"  false alarms (wrongly notified)      : {tot['false_alarm']:>4}  ({tot['false_alarm'] / D:.0%})")
    print(f"  correctly left waiting / for review  : {tot['dist_ok']:>4}  ({tot['dist_ok'] / D:.0%})")
    print(f"Average questions asked per report     : {tot['questions'] / (P + D):.1f}")
    print(f"Precision of NOTIFY after questions    : {tot['correct'] / max(1, tot['correct'] + tot['wrong'] + tot['false_alarm']):.2f}")


if __name__ == "__main__":
    main()
