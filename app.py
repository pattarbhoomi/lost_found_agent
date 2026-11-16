import pandas as pd
import streamlit as st

from agent import ASK, NOTIFY, LostFoundAgent

st.set_page_config(page_title="Campus Lost & Found Agent", page_icon="🔎", layout="wide")

st.markdown("""
<style>

/* Main page */
.stApp {
    background-color: #FFFFFF;
    color: #222222;
}

/* Main headings */
h1, h2, h3, h4 {
    color: #C65D21 !important;
}

/* Normal text */
p, span, label, div {
    color: #222222;
}

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #333333 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: #FFFFFF;
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background-color: #FFF3E8;
    border: 1px solid #F2C49F;
    border-radius: 8px 8px 0 0;
    color: #C65D21 !important;
    font-weight: 700;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #C65D21 !important;
}

/* Selected tab */
.stTabs [aria-selected="true"] {
    background-color: #F4B183 !important;
    color: #222222 !important;
    border-color: #E9A16D !important;
}

.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span {
    color: #222222 !important;
}

/* Buttons */
.stButton button,
.stFormSubmitButton button,
[data-testid="stFormSubmitButton"] button {
    background-color: #F4B183 !important;
    color: #222222 !important;
    border: 1px solid #E9A16D !important;
    border-radius: 10px;
    font-weight: 700;
}

/* Button hover */
.stButton button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background-color: #FFE2CC !important;
    color: #C65D21 !important;
    border-color: #C65D21 !important;
}

/* Input fields */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background-color: #FFFFFF !important;
    color: #222222 !important;
    border: 1px solid #E9B58F !important;
    border-radius: 8px;
}

/* Input focus */
.stTextInput input:focus,
.stTextArea textarea:focus {
    border: 2px solid #F4B183 !important;
    box-shadow: none !important;
}

/* Forms */
[data-testid="stForm"] {
    background-color: #FFFAF6;
    border: 1px solid #F2D2B8;
    border-radius: 14px;
    padding: 20px;
}

/* Containers */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFAF6;
    border-color: #F2D2B8 !important;
    border-radius: 12px;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #F2D2B8;
    border-radius: 10px;
}

/* Radio buttons */
.stRadio label {
    color: #222222 !important;
}

/* Success, warning and info messages */
[data-testid="stAlert"] {
    background-color: #FFF3E8 !important;
    border: 1px solid #F4B183 !important;
    color: #222222 !important;
}

/* Expander */
[data-testid="stExpander"] {
    background-color: #FFFAF6;
    border: 1px solid #F2D2B8;
    border-radius: 10px;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #222222 !important;
}

/* Remove gradients and shadows */
* {
    box-shadow: none;
}

</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_agent():
    return LostFoundAgent("lostfound.db")


agent = get_agent()
st.title("🔎 Campus Lost & Found Agent")
st.caption("Goal-based + utility-based agent · Perceive → Think → Decide → Act · "
           "a human at the security desk confirms every hand-over")


def show_response(resp):
    icon = {"NOTIFY": "✅", "ASK": "❓", "WAIT": "⏳"}[resp.action]
    box = {"NOTIFY": st.success, "ASK": st.warning, "WAIT": st.info}[resp.action]
    box(f"{icon} **Agent decision: {resp.action}**  \n{resp.message}")
    if resp.matches:
        rows = []
        for cand, score, parts in resp.matches:
            rows.append({"Report #": cand.id, "Description": cand.description,
                         "Place": cand.location or "?", "Score": f"{score:.0%}",
                         **{k: round(v, 2) for k, v in parts.items()}})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


tab_report, tab_open, tab_match, tab_notes, tab_eval = st.tabs(
    ["📝 Report an item", "📋 Open reports", "🤝 Matches (security desk)", "🔔 Notifications", "📊 Evaluation"])

with tab_report:
    with st.form("report_form", clear_on_submit=True):
        kind = st.radio("What happened?", ["lost", "found"], horizontal=True,
                        format_func=lambda k: "I LOST something" if k == "lost" else "I FOUND something")
        desc = st.text_input("Describe the item (type, colour, brand, marks)",
                             placeholder="black Boat earbuds case with a sticker")
        c1, c2, c3 = st.columns(3)
        place = c1.text_input("Where?", placeholder="library, canteen, main gate ...")
        when = c2.text_input("When?", placeholder="2pm, 14:30, 2026-11-16 14:30 (blank = now)")
        contact = c3.text_input("Your contact", placeholder="email / phone")
        if st.form_submit_button("Submit report") and desc.strip():
            st.session_state["resp"] = agent.handle_report(kind, desc, place, when, contact or "anonymous")

    resp = st.session_state.get("resp")
    if resp:
        show_response(resp)
        if resp.action == ASK:
            with st.form("answer_form", clear_on_submit=True):
                answer = st.text_input(f"❓ {resp.question}")
                if st.form_submit_button("Answer") and answer.strip():
                    st.session_state["resp"] = agent.answer_question(resp.item_id, answer)
                    st.rerun()

with tab_open:
    reps = agent.open_reports()
    pend = agent.db.items_by("lost", "pending") + agent.db.items_by("found", "pending")
    st.subheader("Open reports (waiting)")
    if reps:
        st.dataframe(pd.DataFrame([{"#": r.id, "Type": r.kind.upper(), "Description": r.description,
                                    "Place": r.location or r.location_text or "?",
                                    "When": f"{r.when:%Y-%m-%d %H:%M}", "Category": r.category,
                                    "Colour": r.color, "Brand": r.brand} for r in reps]),
                     width="stretch", hide_index=True)
    else:
        st.write("No open reports.")
    if pend:
        st.subheader("Reserved by a suggested match")
        st.dataframe(pd.DataFrame([{"#": r.id, "Type": r.kind.upper(), "Description": r.description} for r in pend]),
                     width="stretch", hide_index=True)

with tab_match:
    st.subheader("Suggested matches awaiting a human decision")
    ms = agent.pending_matches()
    if not ms:
        st.write("No suggested matches.")
    for m in ms:
        L, F = agent.db.get_item(m["lost_id"]), agent.db.get_item(m["found_id"])
        with st.container(border=True):
            st.markdown(f"**Match #{m['id']}** · confidence {m['score']:.0%}")
            st.markdown(f"🔴 LOST #{L.id}: {L.description}  \n🟢 FOUND #{F.id}: {F.description}")
            b1, b2, _ = st.columns([1, 1, 4])
            if b1.button("✅ Confirm hand-over", key=f"c{m['id']}"):
                st.success(agent.confirm_match(m["id"]))
                st.rerun()
            if b2.button("❌ Not the same", key=f"r{m['id']}"):
                st.session_state["resp"] = agent.reject_match(m["id"])
                st.rerun()

with tab_notes:
    notes = agent.db.notifications()
    if notes:
        st.dataframe(pd.DataFrame([dict(n) for n in notes])[["created_at", "to_contact", "message"]],
                     width="stretch", hide_index=True)
    else:
        st.write("Nothing sent yet.")

with tab_eval:
    st.subheader("Agent evaluation on held-out synthetic test sets")
    try:
        with open("results/evaluation_results.txt") as f:
            st.code(f.read())
    except FileNotFoundError:
        st.write("Run `python evaluate.py > results/evaluation_results.txt` first.")
