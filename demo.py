"""
demo.py  -  a scripted walk-through for the viva / presentation
================================================================
Run:  python demo.py
It shows ALL behaviours of the agent in about 20 lines of output:
   WAIT    -> a found item arrives, nobody is looking for it yet
   NOTIFY  -> the owner reports it later; strong match, both are told
   ASK     -> a vague report; the agent asks a question, then notifies
   REJECT  -> a human says "not the same"; the agent never suggests that pair again
   RE-LINK -> a later report matches a waiting one; the agent connects them
   CONFIRM -> the hand-over is confirmed and the case closes
"""
from datetime import datetime

from agent import LostFoundAgent

NOW = datetime(2026, 11, 16, 18, 0)


def show(title, r):
    print(f"\n>>> {title}")
    print(f"    ACTION : {r.action}")
    print(f"    AGENT  : {r.message}")
    if r.question:
        print(f"    ASKS   : {r.question}")
    for cand, score, parts in r.matches[:2]:
        why = ", ".join(f"{k}={v:.2f}" for k, v in parts.items())
        print(f"    top    : #{cand.id} '{cand.description}' -> {score:.2f}  [{why}]")


def main():
    agent = LostFoundAgent()          # in-memory database: fresh start every run
    print("=" * 70, "\n LOST & FOUND AGENT - DEMO\n", "=" * 70, sep="")

    r = agent.handle_report("found", "Found a black earphone box with a sticker",
                            "reading hall", "2026-11-16 15:30", "finder_ravi@college.edu", NOW)
    show("1. Ravi FOUND an earphone box (nobody has lost anything yet)", r)

    r = agent.handle_report("lost", "Lost my black Boat earbuds case, has a sticker on it",
                            "library", "2026-11-16 14:00", "asha@college.edu", NOW)
    show("2. Asha reports her earbuds LOST", r)
    first_match = r.match_id

    r = agent.handle_report("found", "Found a brown leather wallet", "canteen",
                            "2026-11-16 16:00", "finder_meena@college.edu", NOW)
    show("3. Meena FOUND a wallet", r)

    r = agent.handle_report("lost", "Lost my wallet", "canteen", "2026-11-16 15:00",
                            "karan@college.edu", NOW)
    show("4. Karan reports a wallet LOST - very vague description", r)
    r = agent.answer_question(r.item_id, "it was brown")
    show("5. Karan answers: 'it was brown'", r)
    wallet_match = r.match_id

    r = agent.handle_report("lost", "Lost blue umbrella", "parking", "2026-11-16 09:00",
                            "dev@college.edu", NOW)
    show("6. Dev reports a blue umbrella LOST (nothing similar exists)", r)

    print("\n>>> 7. Security desk REJECTS the wallet match (it was a different wallet)")
    r = agent.reject_match(wallet_match)
    show("   Agent re-thinks after the rejection", r)

    r = agent.handle_report("found", "Found a brown wallet with a card holder", "canteen",
                            "2026-11-16 17:00", "finder_ishaan@college.edu", NOW)
    show("8. Ishaan FOUND another brown wallet -> agent links it to Karan's waiting report", r)

    print("\n>>> 9. Security desk CONFIRMS the earbuds hand-over")
    print("   ", agent.confirm_match(first_match))

    print("\n--- Notification log (what the agent sent) ---")
    for n in agent.db.notifications():
        print(f"  to {n['to_contact']:<28} {n['message']}")
    print("\n--- Still open ---")
    for rep in agent.open_reports():
        print(f"  #{rep.id} [{rep.kind}] {rep.description}")


if __name__ == "__main__":
    main()
