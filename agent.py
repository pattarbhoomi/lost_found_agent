"""
agent.py  -  the Lost & Found AGENT (the loop that ties everything together)
===========================================================================
ELI5: This is the "helpful clerk".  Every time a new report arrives the
clerk does four things, always in the same order:

    1. PERCEIVE  read the report and fill the tidy form      (perception.py)
    2. THINK     compare it with everything waiting          (matcher.py)
    3. DECIDE    pick ONE action from the best score         (decide() below)
    4. ACT       notify / ask a question / keep waiting      (_act_* below)

Agent type  : goal-based + utility-based  (goal = reunite owner and item,
              utility = the 0..1 match score)
Autonomy    : SEMI-autonomous.  The agent suggests and notifies by itself,
              but a human at the security desk confirms the final hand-over.
"""
from dataclasses import dataclass, field
from typing import List, Optional

import config
import matcher
import perception
from database import Database
from perception import Report

NOTIFY, ASK, WAIT = "NOTIFY", "ASK", "WAIT"


@dataclass
class AgentResponse:
    action: str                                   # NOTIFY / ASK / WAIT
    item_id: int
    message: str
    matches: list = field(default_factory=list)   # top candidates: (Report, score, breakdown)
    question: Optional[str] = None
    attribute: Optional[str] = None               # which clue the question is about
    match_id: Optional[int] = None


# ---------------------------------------------------------------------
# The decision policy lives in ONE tiny function so it is easy to explain
# ---------------------------------------------------------------------
def decide(best_score: Optional[float], second_score: Optional[float] = None) -> str:
    """Policy:  strong AND clearly better than the runner-up -> NOTIFY
                medium (or too close to call)                -> ASK
                weak                                         -> WAIT"""
    if best_score is None:
        return WAIT
    margin = best_score - (second_score if second_score is not None else 0.0)
    if best_score >= config.NOTIFY_THRESHOLD and margin >= config.NOTIFY_MARGIN:
        return NOTIFY
    if best_score >= config.NOTIFY_THRESHOLD:          # strong but ambiguous
        return ASK
    if best_score >= config.ASK_THRESHOLD:
        return ASK
    return WAIT


def choose_question(report: Report, cand: Report, parts: dict, asked: set):
    """Ask about the clue that would help most, and never repeat a question.
    (We never reveal the other person's description - that stops people
    from simply 'guessing' their way to someone else's property.)"""
    verb = "lose" if report.kind == "lost" else "find"
    if "color" not in asked and report.color is None and cand.color is not None:
        return "color", "What colour was the item?"
    if "brand" not in asked and report.brand is None and cand.brand is not None:
        return "brand", "Do you remember the brand / make of the item?"
    if "location" not in asked and (report.location is None or parts["location"] < 0.4):
        return "location", f"Where exactly did you {verb} it? (e.g. library, canteen, main gate)"
    if "feature" not in asked:
        return "feature", "Any unique mark - sticker, scratch, name, or something inside it?"
    return None, None


class LostFoundAgent:
    def __init__(self, db_path: str = ":memory:"):
        self.db = Database(db_path)           # the agent's memory

    # =================================================================
    # PUBLIC ACTIONS (what the outside world can ask the agent to do)
    # =================================================================
    def handle_report(self, kind: str, description: str, location_text: str = "",
                      time_text: str = "", contact: str = "", now=None) -> AgentResponse:
        """A person submits a new LOST or FOUND report."""
        report = perception.parse_report(kind, description, location_text, time_text, contact, now)   # 1. PERCEIVE
        report.id = self.db.add_item(report)
        return self._think_and_act(report)

    def answer_question(self, item_id: int, answer: str) -> AgentResponse:
        """The user answers the agent's clarifying question; agent re-thinks."""
        report = self.db.get_item(item_id)
        q = self.db.last_open_question(item_id)
        if q:
            self.db.record_answer(item_id, q["attribute"], answer)
        perception.apply_answer(report, answer)   # learn: fill empty boxes, extend description
        self.db.update_item(report)
        return self._think_and_act(report)

    def confirm_match(self, match_id: int) -> str:
        """Human at the security desk confirms the hand-over -> close both reports."""
        m = self.db.get_match(match_id)
        self.db.set_match_state(match_id, "confirmed")
        lost, found = self.db.get_item(m["lost_id"]), self.db.get_item(m["found_id"])
        self.db.set_status(lost.id, "closed")
        self.db.set_status(found.id, "closed")
        for who in (lost, found):
            self.db.add_notification(who.contact, f"Case closed: item returned (match #{match_id}). Thank you!")
        return f"Match #{match_id} confirmed. Reports #{lost.id} and #{found.id} are now closed."

    def reject_match(self, match_id: int) -> AgentResponse:
        """Human says 'not the same item' -> agent remembers and tries the next-best."""
        m = self.db.get_match(match_id)
        self.db.set_match_state(match_id, "rejected")
        self.db.set_status(m["lost_id"], "open")
        self.db.set_status(m["found_id"], "open")
        return self._think_and_act(self.db.get_item(m["lost_id"]))

    # =================================================================
    # THE AGENT LOOP
    # =================================================================
    def _think_and_act(self, report: Report) -> AgentResponse:
        # ---- 2. THINK: score the report against every OPEN report of the opposite kind
        opposite = "found" if report.kind == "lost" else "lost"
        pool = [c for c in self.db.items_by(opposite, "open") if not self._pair_rejected(report, c)]
        ranked = matcher.rank_candidates(report, pool)[:3]
        best = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None

        # ---- 3. DECIDE
        action = decide(best[1] if best else None, second[1] if second else None)

        # ---- 4. ACT
        if action == NOTIFY:
            return self._act_notify(report, ranked)
        if action == ASK:
            resp = self._act_ask(report, ranked)
            if resp:
                return resp
        return self._act_wait(report, ranked)

    def _pair_rejected(self, a: Report, b: Report) -> bool:
        lost, found = (a, b) if a.kind == "lost" else (b, a)
        return self.db.is_rejected(lost.id, found.id)

    # ----------------------- ACTUATORS -------------------------------
    def _act_notify(self, report: Report, ranked) -> AgentResponse:
        cand, score, parts = ranked[0]
        lost, found = (report, cand) if report.kind == "lost" else (cand, report)
        match_id = self.db.add_match(lost.id, found.id, score)
        self.db.set_status(lost.id, "pending")      # reserve both so they are not matched twice
        self.db.set_status(found.id, "pending")
        self.db.add_notification(lost.contact,
            f"Good news! A possible match for your lost item was found "
            f"(match #{match_id}, {score:.0%} confident). Visit the security desk with proof of ownership.")
        self.db.add_notification(found.contact,
            f"Thank you! Someone may be the owner of the item you found "
            f"(match #{match_id}). Please keep it safe / hand it to the security desk.")
        msg = (f"Strong match ({score:.0%}). Both people have been notified; "
               f"a human must confirm the hand-over (match #{match_id}).")
        return AgentResponse(NOTIFY, report.id, msg, ranked, match_id=match_id)

    def _act_ask(self, report: Report, ranked) -> Optional[AgentResponse]:
        cand, score, parts = ranked[0]
        attr, question = self._choose_question(report, cand, parts)
        if question is None:
            return None                              # nothing useful left to ask
        self.db.add_question(report.id, attr, question)
        msg = f"Possible match ({score:.0%}) but I am not sure yet. I need one more detail."
        return AgentResponse(ASK, report.id, msg, ranked, question=question, attribute=attr)

    def _act_wait(self, report: Report, ranked) -> AgentResponse:
        if ranked:
            msg = (f"Best candidate scores only {ranked[0][1]:.0%}. Report saved; "
                   f"I will compare it with every new report that arrives.")
        else:
            msg = "No candidates yet. Report saved; I will compare it with every new report that arrives."
        return AgentResponse(WAIT, report.id, msg, ranked)

    # ------------- choosing the most useful clarifying question -------------
    def _choose_question(self, report: Report, cand: Report, parts: dict):
        return choose_question(report, cand, parts, self.db.asked_attributes(report.id))

    # ---------------------- read-only helpers for the UI ----------------------
    def open_reports(self) -> List[Report]:
        return self.db.items_by("lost") + self.db.items_by("found")

    def pending_matches(self):
        return self.db.matches_in_state("suggested")
