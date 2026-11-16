"""
app.py  -  Streamlit web interface for the Lost & Found Agent  (pastel theme)
=============================================================================
Run:   python -m streamlit run app.py
ELI5: same clerk (agent.py) as before, now with a friendlier front desk:
cards, colour-coded decisions and little bars that show WHY the agent
thinks two reports match.  All the thinking is still in agent.py.
"""
import html
import re

import streamlit as st

import config
from agent import ASK, LostFoundAgent

st.set_page_config(page_title="Campus Lost & Found Agent", page_icon="🧡", layout="wide")

# ----------------------------------------------------------------------------
# Pastel theme  (orange #FFB88C · purple #B8A1E3 · white)
# ----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
:root{
  --orange:#FFB88C; --orange-soft:#FFE3D0; --peach:#FFF4EC;
  --purple:#B8A1E3; --purple-soft:#EDE6FB; --lilac:#F7F3FF;
  --ink:#3F3556; --muted:#7C7294; --white:#FFFFFF;
}
html, body, [class*="css"], .stApp { font-family:'Nunito', sans-serif; color:var(--ink); }
.stApp { background: linear-gradient(180deg, #FFFFFF 0%, var(--peach) 55%, var(--lilac) 100%); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1180px; }

/* hero */
.hero{ background: linear-gradient(120deg, var(--orange) 0%, #E9B8D9 52%, var(--purple) 100%);
  border-radius: 26px; padding: 30px 36px; color:#fff; margin-bottom: 18px;
  box-shadow: 0 10px 30px rgba(184,161,227,.35); }
.hero h1{ margin:0; font-size:2.1rem; font-weight:800; color:#fff; letter-spacing:.2px; }
.hero p{ margin:6px 0 0 0; font-size:1.02rem; opacity:.96; color:#fff; }
.loop{ display:flex; gap:10px; flex-wrap:wrap; margin-top:16px; }
.loop span{ background:rgba(255,255,255,.28); border:1px solid rgba(255,255,255,.55);
  padding:5px 14px; border-radius:999px; font-weight:700; font-size:.85rem; color:#fff; }

/* stat cards */
.stats{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:10px; }
.stat{ background:#fff; border-radius:20px; padding:16px 18px; border:1px solid var(--purple-soft);
  box-shadow:0 4px 14px rgba(63,53,86,.06); }
.stat .n{ font-size:1.9rem; font-weight:800; line-height:1; }
.stat .l{ color:var(--muted); font-weight:600; font-size:.85rem; margin-top:4px; }
.stat.o .n{ color:#F09A62; } .stat.p .n{ color:#9C82D6; }

/* tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
    border-bottom: none;
}

.stTabs [data-baseweb="tab"] {
    background: #fff;
    border-radius: 999px;
    padding: 8px 18px;
    height: auto;
    border: 1px solid var(--purple-soft);
    font-weight: 800;
    color: #D62828 !important;
}

/* Keep every tab red, even when not selected */
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] div,
.stTabs [data-baseweb="tab"] span {
    color: #D62828 !important;
}

/* Selected tab */
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, var(--orange-soft), var(--purple-soft));
    color: #D62828 !important;
    border: 1px solid var(--purple);
}

.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] div,
.stTabs [aria-selected="true"] span {
    color: #D62828 !important;
}

.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* forms & inputs */
[data-testid="stForm"]{ background:#fff; border:1px solid var(--purple-soft); border-radius:24px;
  padding:22px 24px; box-shadow:0 6px 20px rgba(184,161,227,.18); }
.stTextInput input{ border-radius:14px !important; border:1.5px solid var(--purple-soft) !important;
  background:var(--lilac) !important; color:var(--ink) !important; }
.stTextInput input:focus{ border-color:var(--orange) !important; box-shadow:0 0 0 3px var(--orange-soft) !important; }
label, .stRadio label p{ font-weight:700 !important; color:var(--ink) !important; }

/* buttons */
.stButton>button, [data-testid="stFormSubmitButton"]>button{
  background:linear-gradient(90deg,var(--orange),#E8A9C8 60%,var(--purple)); color:#fff; border:none;
  border-radius:999px; padding:.55rem 1.5rem; font-weight:800; box-shadow:0 6px 16px rgba(184,161,227,.4);
  transition:transform .12s ease; }
.stButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover{ transform:translateY(-2px); color:#fff; }
.stButton>button:focus{ color:#fff; }

/* decision card */
.decision{ border-radius:22px; padding:18px 22px; margin:14px 0; border:1px solid transparent; }
.decision .badge{ display:inline-block; font-weight:800; padding:4px 14px; border-radius:999px; font-size:.82rem; letter-spacing:.6px; }
.decision .msg{ margin-top:8px; font-size:1.02rem; font-weight:600; }
.decision.notify{ background:var(--purple-soft); border-color:var(--purple); }
.decision.notify .badge{ background:var(--purple); color:#fff; }
.decision.ask{ background:var(--orange-soft); border-color:var(--orange); }
.decision.ask .badge{ background:var(--orange); color:#fff; }
.decision.wait{ background:#fff; border-color:var(--purple-soft); }
.decision.wait .badge{ background:var(--purple-soft); color:var(--ink); }

/* generic card */
.card{ background:#fff; border-radius:20px; padding:16px 18px; margin:10px 0; border:1px solid var(--purple-soft);
  box-shadow:0 4px 14px rgba(63,53,86,.06); }
.card.lost{ border-left:7px solid var(--orange); } .card.found{ border-left:7px solid var(--purple); }
.card .top{ display:flex; justify-content:space-between; align-items:center; gap:10px; }
.card .title{ font-weight:800; font-size:1.02rem; }
.pill{ display:inline-block; padding:3px 11px; border-radius:999px; font-size:.78rem; font-weight:700; margin:6px 6px 0 0; }
.pill.o{ background:var(--orange-soft); color:#B4622B; } .pill.p{ background:var(--purple-soft); color:#6B52A8; }
.score{ font-weight:800; font-size:1.15rem; color:#8F73CF; }

/* clue bars */
.bars{ margin-top:10px; display:grid; grid-template-columns:repeat(3,1fr); gap:6px 16px; }
.bar .lab{ display:flex; justify-content:space-between; font-size:.76rem; font-weight:700; color:var(--muted); }
.bar .track{ height:7px; background:var(--lilac); border-radius:99px; overflow:hidden; margin-top:3px; }
.bar .fill{ height:100%; border-radius:99px; background:linear-gradient(90deg,var(--orange),var(--purple)); }

/* sidebar */
[data-testid="stSidebar"]{ background:linear-gradient(180deg,var(--lilac),var(--peach)); border-right:1px solid var(--purple-soft); }
.side h3{ margin:.2rem 0 .6rem 0; }
.step{ background:#fff; border-radius:16px; padding:10px 14px; margin:8px 0; border:1px solid var(--purple-soft); font-size:.9rem; }
.step b{ color:#E58B52; }
.empty{ text-align:center; color:var(--muted); padding:26px; background:#fff; border:2px dashed var(--purple-soft); border-radius:20px; font-weight:600; }
.sect{ font-weight:800; font-size:1.15rem; margin:8px 0 2px 0; }
@media (max-width:800px){ .stats{grid-template-columns:repeat(2,1fr);} .bars{grid-template-columns:repeat(2,1fr);} }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_agent():
    return LostFoundAgent("lostfound.db")      # saved on disk, survives restarts


agent = get_agent()
e = html.escape

CLUE_LABELS = {"text": "Description", "category": "Category", "color": "Colour",
               "brand": "Brand", "location": "Place", "time": "Time"}


# ----------------------------------------------------------------------------
# Small HTML helpers
# ----------------------------------------------------------------------------
def bars_html(parts):
    out = []
    for k, label in CLUE_LABELS.items():
        v = parts[k]
        out.append(f'<div class="bar"><div class="lab"><span>{label}</span><span>{v:.0%}</span></div>'
                   f'<div class="track"><div class="fill" style="width:{max(2, v * 100):.0f}%"></div></div></div>')
    return f'<div class="bars">{"".join(out)}</div>'


def report_card(r, extra=""):
    kind_cls = "lost" if r.kind == "lost" else "found"
    pills = f'<span class="pill o">📍 {e(r.location or r.location_text or "unknown place")}</span>'
    pills += f'<span class="pill p">🕒 {r.when:%d %b, %H:%M}</span>'
    for val in (r.category, r.color, r.brand):
        if val:
            pills += f'<span class="pill p">{e(str(val).replace("_", " "))}</span>'
    return (f'<div class="card {kind_cls}"><div class="top"><div class="title">#{r.id} · {e(r.description)}</div>'
            f'<span class="pill {"o" if r.kind == "lost" else "p"}">{r.kind.upper()}</span></div>{pills}{extra}</div>')


def show_response(resp):
    meta = {"NOTIFY": ("notify", "✅ MATCH FOUND"), "ASK": ("ask", "❓ NEED ONE MORE DETAIL"),
            "WAIT": ("wait", "⏳ WAITING")}[resp.action]
    st.markdown(f'<div class="decision {meta[0]}"><span class="badge">{meta[1]}</span>'
                f'<div class="msg">{e(resp.message)}</div></div>', unsafe_allow_html=True)
    if resp.matches:
        st.markdown('<div class="sect">Why the agent thinks so</div>', unsafe_allow_html=True)
        for cand, score, parts in resp.matches:
            extra = (f'<div class="top" style="margin-top:8px"><span style="color:var(--muted);font-weight:700">'
                     f'Match score</span><span class="score">{score:.0%}</span></div>{bars_html(parts)}')
            st.markdown(report_card(cand, extra), unsafe_allow_html=True)


def empty(msg):
    st.markdown(f'<div class="empty">{msg}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""<div class="side"><h3>🧡 How the agent works</h3>
      <div class="step"><b>1 · Perceive</b><br>Reads your sentence and fills a tidy form: item, colour, brand, place, time.</div>
      <div class="step"><b>2 · Think</b><br>Scores it against every waiting report using six clues.</div>
      <div class="step"><b>3 · Decide</b><br>Picks one action from the score.</div>
      <div class="step"><b>4 · Act</b><br>Notifies, asks a question, or keeps watching.</div></div>""", unsafe_allow_html=True)
    st.markdown("#### Decision rules")
    st.markdown(f'<span class="pill p">≥ {config.NOTIFY_THRESHOLD:.0%} & clear lead → NOTIFY</span>'
                f'<span class="pill o">≥ {config.ASK_THRESHOLD:.0%} → ASK</span>'
                f'<span class="pill p">below → WAIT</span>', unsafe_allow_html=True)
    st.caption("A human at the security desk confirms every hand-over (semi-autonomous agent).")

# ----------------------------------------------------------------------------
# Hero + live stats
# ----------------------------------------------------------------------------
st.markdown("""<div class="hero"><h1>🧡 Campus Lost & Found Agent</h1>
  <p>Tell me what you lost or found. I'll compare it with everything on file and connect the right people.</p>
  <div class="loop"><span>👀 Perceive</span><span>🧠 Think</span><span>⚖️ Decide</span><span>🚀 Act</span></div></div>""",
            unsafe_allow_html=True)

open_lost, open_found = agent.db.items_by("lost"), agent.db.items_by("found")
pending = agent.pending_matches()
closed = len(agent.db.items_by("lost", "closed"))
st.markdown(f"""<div class="stats">
  <div class="stat o"><div class="n">{len(open_lost)}</div><div class="l">Lost items waiting</div></div>
  <div class="stat p"><div class="n">{len(open_found)}</div><div class="l">Found items waiting</div></div>
  <div class="stat o"><div class="n">{len(pending)}</div><div class="l">Matches awaiting desk</div></div>
  <div class="stat p"><div class="n">{closed}</div><div class="l">Items returned</div></div></div>""",
            unsafe_allow_html=True)

tab_report, tab_open, tab_match, tab_notes, tab_eval = st.tabs(
    ["📝 Report an item", "📋 Open reports", "🤝 Security desk", "🔔 Notifications", "📊 Evaluation"])

# ---------------------------------------------------------------- report
with tab_report:
    with st.form("report_form", clear_on_submit=True):
        kind = st.radio("What happened?", ["lost", "found"], horizontal=True,
                        format_func=lambda k: "😢 I LOST something" if k == "lost" else "😊 I FOUND something")
        desc = st.text_input("Describe the item", placeholder="black Boat earbuds case with a sticker on it")
        c1, c2, c3 = st.columns(3)
        place = c1.text_input("Where?", placeholder="library, canteen, main gate ...")
        when = c2.text_input("When?", placeholder="2pm · 14:30 · 2026-11-16 14:30 (blank = now)")
        contact = c3.text_input("Your contact", placeholder="email or phone")
        if st.form_submit_button("Submit report ✨") and desc.strip():
            st.session_state["resp"] = agent.handle_report(kind, desc, place, when, contact or "anonymous")

    resp = st.session_state.get("resp")
    if resp:
        show_response(resp)
        if resp.action == ASK:
            with st.form("answer_form", clear_on_submit=True):
                answer = st.text_input(f"❓ {resp.question}")
                if st.form_submit_button("Send answer 💬") and answer.strip():
                    st.session_state["resp"] = agent.answer_question(resp.item_id, answer)
                    st.rerun()

# ---------------------------------------------------------------- open reports
with tab_open:
    colL, colF = st.columns(2)
    with colL:
        st.markdown('<div class="sect">😢 Lost</div>', unsafe_allow_html=True)
        if open_lost:
            st.markdown("".join(report_card(r) for r in open_lost), unsafe_allow_html=True)
        else:
            empty("No lost items waiting")
    with colF:
        st.markdown('<div class="sect">😊 Found</div>', unsafe_allow_html=True)
        if open_found:
            st.markdown("".join(report_card(r) for r in open_found), unsafe_allow_html=True)
        else:
            empty("No found items waiting")

# ---------------------------------------------------------------- security desk
with tab_match:
    st.markdown('<div class="sect">Suggested matches awaiting a human decision</div>', unsafe_allow_html=True)
    if not pending:
        empty("No suggested matches right now ✨")
    for m in pending:
        L, F = agent.db.get_item(m["lost_id"]), agent.db.get_item(m["found_id"])
        st.markdown(f'<div class="top" style="margin-top:14px"><span class="title">Match #{m["id"]}</span>'
                    f'<span class="score">{m["score"]:.0%} confident</span></div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        a.markdown(report_card(L), unsafe_allow_html=True)
        b.markdown(report_card(F), unsafe_allow_html=True)
        b1, b2, _ = st.columns([1.3, 1.3, 4])
        if b1.button("✅ Confirm hand-over", key=f"c{m['id']}"):
            agent.confirm_match(m["id"])
            st.rerun()
        if b2.button("❌ Not the same", key=f"r{m['id']}"):
            st.session_state["resp"] = agent.reject_match(m["id"])
            st.rerun()

# ---------------------------------------------------------------- notifications
with tab_notes:
    notes = agent.db.notifications()
    if not notes:
        empty("Nothing sent yet")
    for n in reversed(notes):
        st.markdown(f'<div class="card"><div class="top"><span class="title">To: {e(n["to_contact"])}</span>'
                    f'<span class="pill p">{e(n["created_at"].replace("T", " "))}</span></div>'
                    f'<div style="margin-top:6px">{e(n["message"])}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- evaluation
with tab_eval:
    st.markdown('<div class="sect">How well does the agent perform?</div>', unsafe_allow_html=True)
    try:
        text = open("results/evaluation_results.txt").read()
        m = re.search(r"Full agent \(multi-clue score\)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", text)
        base = re.search(r"Baseline A: plain TF-IDF\s+([\d.]+)", text)
        prec = re.search(r"NOTIFY precision.*?:\s*([\d.]+)", text)
        if m:
            st.markdown(f"""<div class="stats">
              <div class="stat o"><div class="n">{float(m.group(1)):.0%}</div><div class="l">Right item ranked 1st</div></div>
              <div class="stat p"><div class="n">{float(m.group(2)):.0%}</div><div class="l">Right item in top 3</div></div>
              <div class="stat o"><div class="n">{float(prec.group(1)):.0%}</div><div class="l">Notify precision</div></div>
              <div class="stat p"><div class="n">{float(base.group(1)):.0%}</div><div class="l">Plain keyword search (1st)</div></div></div>""",
                        unsafe_allow_html=True)
        with st.expander("Full evaluation output"):
            st.code(text)
    except FileNotFoundError:
        empty("Run <code>python evaluate.py &gt; results\\evaluation_results.txt</code> to fill this tab")