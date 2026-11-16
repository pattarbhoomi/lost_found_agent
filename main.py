"""
main.py  -  the interactive Lost & Found Agent (command-line app)
=================================================================
Run:   python main.py              (data is saved in lostfound.db)
       python main.py --db other.db
ELI5: this file is only the "front desk" - it asks you questions, passes
your answers to the agent (agent.py) and prints what the agent decides.
"""
import argparse

from agent import ASK, NOTIFY, LostFoundAgent

MENU = """
==============  CAMPUS LOST & FOUND AGENT  ==============
 1. Report a LOST item
 2. Report a FOUND item
 3. Show open reports
 4. Show suggested matches (waiting for the security desk)
 5. Security desk: CONFIRM a match (item handed over)
 6. Security desk: REJECT a match (not the same item)
 7. Show notifications sent by the agent
 0. Exit
"""


def print_response(r):
    print(f"\n  AGENT DECISION: {r.action}")
    print(f"  {r.message}")
    for cand, score, parts in r.matches[:3]:
        why = ", ".join(f"{k} {v:.2f}" for k, v in parts.items())
        print(f"   - candidate #{cand.id}: '{cand.description}' @ {cand.location or '?'}  -> {score:.0%}")
        print(f"       why: {why}")


def report_flow(agent, kind):
    print(f"\n-- New {kind.upper()} report --")
    description = input("Describe the item (type, colour, brand, marks): ").strip()
    if not description:
        print("A description is required.")
        return
    place = input("Where (e.g. library, canteen, main gate): ").strip()
    when = input("When? (e.g. 2pm, 14:30, 2026-11-16 14:30, blank = now): ").strip()
    contact = input("Your contact (email/phone): ").strip() or "anonymous"
    resp = agent.handle_report(kind, description, place, when, contact)
    print_response(resp)
    # the agent may ask follow-up questions; keep the conversation going
    while resp.action == ASK:
        answer = input(f"\n  AGENT ASKS: {resp.question}\n  (your answer, blank to skip): ").strip()
        if not answer:
            print("  Skipped. Your report stays open; I will keep watching for matches.")
            break
        resp = agent.answer_question(resp.item_id, answer)
        print_response(resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="lostfound.db")
    agent = LostFoundAgent(ap.parse_args().db)
    while True:
        print(MENU)
        choice = input("Choose: ").strip()
        if choice == "1":
            report_flow(agent, "lost")
        elif choice == "2":
            report_flow(agent, "found")
        elif choice == "3":
            reps = agent.open_reports()
            print("\nOpen reports:" if reps else "\nNo open reports.")
            for r in reps:
                print(f"  #{r.id} [{r.kind.upper()}] {r.description} | {r.location or r.location_text or '?'} | {r.when:%Y-%m-%d %H:%M}")
        elif choice == "4":
            ms = agent.pending_matches()
            print("\nSuggested matches:" if ms else "\nNo suggested matches.")
            for m in ms:
                L, F = agent.db.get_item(m["lost_id"]), agent.db.get_item(m["found_id"])
                print(f"  match #{m['id']} ({m['score']:.0%})\n     LOST : #{L.id} {L.description}\n     FOUND: #{F.id} {F.description}")
        elif choice in ("5", "6"):
            try:
                mid = int(input("Match number: "))
                if agent.db.get_match(mid) is None:
                    print("No such match.")
                elif choice == "5":
                    print("  " + agent.confirm_match(mid))
                else:
                    print_response(agent.reject_match(mid))
            except ValueError:
                print("Please type a number.")
        elif choice == "7":
            for n in agent.db.notifications():
                print(f"  [{n['created_at']}] to {n['to_contact']}: {n['message']}")
        elif choice == "0":
            print("Bye!")
            break
        else:
            print("Please choose 0-7.")


if __name__ == "__main__":
    main()
