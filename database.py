"""
database.py  -  the agent's MEMORY
==================================
ELI5: A security guard who forgets everything every night is useless.
This file is the guard's notebook (a tiny SQLite database - it is built
into Python, nothing to install).  It has four pages:
   items           every lost/found report and its status
   matches         "I think lost #3 = found #7" suggestions + their fate
   questions       what the agent asked and what the user answered
   notifications   messages the agent sent out (a log instead of real SMS)
"""
import sqlite3
from datetime import datetime
from typing import List, Optional

from perception import Report

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT, description TEXT, clean_text TEXT,
    category TEXT, color TEXT, brand TEXT,
    location TEXT, location_text TEXT, when_ts TEXT,
    contact TEXT, status TEXT DEFAULT 'open', created_at TEXT
);
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_id INTEGER, found_id INTEGER, score REAL,
    state TEXT DEFAULT 'suggested',          -- suggested / confirmed / rejected
    created_at TEXT, UNIQUE(lost_id, found_id)
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER, attribute TEXT, question TEXT, answer TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_contact TEXT, message TEXT, created_at TEXT
);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ---------------- items ----------------
    @staticmethod
    def _row_to_report(r) -> Report:
        return Report(kind=r["kind"], description=r["description"], clean_text=r["clean_text"],
                      category=r["category"], color=r["color"], brand=r["brand"],
                      location=r["location"], location_text=r["location_text"] or "",
                      when=datetime.fromisoformat(r["when_ts"]), contact=r["contact"] or "",
                      status=r["status"], id=r["id"])

    def add_item(self, rep: Report) -> int:
        cur = self.conn.execute(
            "INSERT INTO items (kind,description,clean_text,category,color,brand,location,"
            "location_text,when_ts,contact,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (rep.kind, rep.description, rep.clean_text, rep.category, rep.color, rep.brand,
             rep.location, rep.location_text, rep.when.isoformat(timespec="seconds"),
             rep.contact, rep.status, _now()))
        self.conn.commit()
        return cur.lastrowid

    def update_item(self, rep: Report):
        self.conn.execute(
            "UPDATE items SET description=?, clean_text=?, category=?, color=?, brand=?, "
            "location=?, location_text=? WHERE id=?",
            (rep.description, rep.clean_text, rep.category, rep.color, rep.brand,
             rep.location, rep.location_text, rep.id))
        self.conn.commit()

    def get_item(self, item_id: int) -> Optional[Report]:
        r = self.conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return self._row_to_report(r) if r else None

    def items_by(self, kind: str, status: str = "open") -> List[Report]:
        rows = self.conn.execute("SELECT * FROM items WHERE kind=? AND status=? ORDER BY id",
                                 (kind, status)).fetchall()
        return [self._row_to_report(r) for r in rows]

    def set_status(self, item_id: int, status: str):
        self.conn.execute("UPDATE items SET status=? WHERE id=?", (status, item_id))
        self.conn.commit()

    # ---------------- matches ----------------
    def add_match(self, lost_id: int, found_id: int, score: float) -> int:
        self.conn.execute("INSERT OR IGNORE INTO matches (lost_id,found_id,score,created_at) "
                          "VALUES (?,?,?,?)", (lost_id, found_id, score, _now()))
        self.conn.commit()
        r = self.conn.execute("SELECT id FROM matches WHERE lost_id=? AND found_id=?",
                              (lost_id, found_id)).fetchone()
        return r["id"]

    def get_match(self, match_id: int):
        return self.conn.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()

    def set_match_state(self, match_id: int, state: str):
        self.conn.execute("UPDATE matches SET state=? WHERE id=?", (state, match_id))
        self.conn.commit()

    def matches_in_state(self, state: str):
        return self.conn.execute("SELECT * FROM matches WHERE state=? ORDER BY id", (state,)).fetchall()

    def is_rejected(self, lost_id: int, found_id: int) -> bool:
        r = self.conn.execute("SELECT 1 FROM matches WHERE lost_id=? AND found_id=? AND state='rejected'",
                              (lost_id, found_id)).fetchone()
        return r is not None

    # ---------------- questions ----------------
    def add_question(self, item_id: int, attribute: str, question: str):
        self.conn.execute("INSERT INTO questions (item_id,attribute,question,created_at) VALUES (?,?,?,?)",
                          (item_id, attribute, question, _now()))
        self.conn.commit()

    def asked_attributes(self, item_id: int) -> set:
        rows = self.conn.execute("SELECT attribute FROM questions WHERE item_id=?", (item_id,)).fetchall()
        return {r["attribute"] for r in rows}

    def record_answer(self, item_id: int, attribute: str, answer: str):
        self.conn.execute("UPDATE questions SET answer=? WHERE item_id=? AND attribute=?",
                          (answer, item_id, attribute))
        self.conn.commit()

    def last_open_question(self, item_id: int):
        return self.conn.execute("SELECT * FROM questions WHERE item_id=? AND answer IS NULL "
                                 "ORDER BY id DESC LIMIT 1", (item_id,)).fetchone()

    # ---------------- notifications ----------------
    def add_notification(self, to_contact: str, message: str):
        self.conn.execute("INSERT INTO notifications (to_contact,message,created_at) VALUES (?,?,?)",
                          (to_contact, message, _now()))
        self.conn.commit()

    def notifications(self):
        return self.conn.execute("SELECT * FROM notifications ORDER BY id").fetchall()
